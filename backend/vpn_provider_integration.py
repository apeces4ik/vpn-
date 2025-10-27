"""
VPN Provider Integration Module
Supports DigitalOcean and Vultr for automated VPN server deployment
"""

import os
import logging
import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timezone
import base64

logger = logging.getLogger(__name__)


class VPNProviderBase:
    """Base class for VPN provider integrations"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def create_server(self, region: str, plan: str, name: str) -> Dict:
        raise NotImplementedError
    
    async def delete_server(self, server_id: str) -> bool:
        raise NotImplementedError
    
    async def get_server_info(self, server_id: str) -> Dict:
        raise NotImplementedError
    
    async def list_servers(self) -> List[Dict]:
        raise NotImplementedError
    
    async def reboot_server(self, server_id: str) -> bool:
        raise NotImplementedError


class DigitalOceanProvider(VPNProviderBase):
    """DigitalOcean API integration for VPN server management"""
    
    BASE_URL = "https://api.digitalocean.com/v2"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_wireguard_setup_script(self, server_hostname: str) -> str:
        """Generate WireGuard installation and setup script"""
        return f"""#!/bin/bash
set -e

echo "🚀 Setting up WireGuard VPN Server: {server_hostname}"

# Update system
apt-get update -qq
apt-get upgrade -y -qq

# Install WireGuard
apt-get install -y wireguard wireguard-tools qrencode iptables

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf
sysctl -p

# Generate server keys
cd /etc/wireguard
umask 077
wg genkey | tee server_private.key | wg pubkey > server_public.key

SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_PUBLIC_KEY=$(cat server_public.key)

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)

# Create WireGuard configuration
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $SERVER_PRIVATE_KEY
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

# Set permissions
chmod 600 /etc/wireguard/wg0.conf
chmod 600 /etc/wireguard/server_private.key

# Enable and start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Configure firewall
ufw allow 51820/udp
ufw allow 22/tcp
echo "y" | ufw enable

# Install OpenVPN
apt-get install -y openvpn easy-rsa

# Setup OpenVPN
mkdir -p /etc/openvpn/easy-rsa
cp -r /usr/share/easy-rsa/* /etc/openvpn/easy-rsa/

# Install monitoring agent
apt-get install -y prometheus-node-exporter

# Create status endpoint
mkdir -p /var/www/html
cat > /var/www/html/health.json <<EOF
{{
  "status": "healthy",
  "hostname": "{server_hostname}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "services": {{
    "wireguard": "active",
    "openvpn": "active"
  }}
}}
EOF

# Install nginx for health endpoint
apt-get install -y nginx
systemctl enable nginx
systemctl start nginx

echo "✅ WireGuard VPN Server setup completed!"
echo "Server IP: $SERVER_IP"
echo "WireGuard Port: 51820"
echo "Server Public Key: $SERVER_PUBLIC_KEY"

# Save server info
cat > /root/vpn_server_info.json <<EOF
{{
  "server_ip": "$SERVER_IP",
  "wireguard_port": 51820,
  "server_public_key": "$SERVER_PUBLIC_KEY",
  "setup_completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}}
EOF

echo "Server info saved to /root/vpn_server_info.json"
"""
    
    async def create_server(
        self, 
        region: str, 
        plan: str = "s-1vcpu-1gb",
        name: str = None,
        tags: List[str] = None
    ) -> Dict:
        """
        Create a new DigitalOcean droplet for VPN server
        
        Args:
            region: DigitalOcean region slug (e.g., 'nyc1', 'sfo3', 'ams3')
            plan: Droplet size (default: s-1vcpu-1gb)
            name: Server name (auto-generated if not provided)
            tags: List of tags for the droplet
        
        Returns:
            Dict with server information
        """
        try:
            if not name:
                name = f"vpn-server-{region}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            if not tags:
                tags = ["vpn-server", "wireguard", "anonvpn"]
            
            # Encode setup script
            user_data = self._get_wireguard_setup_script(name)
            
            data = {
                "name": name,
                "region": region,
                "size": plan,
                "image": "ubuntu-22-04-x64",
                "ssh_keys": [],  # Add your SSH key IDs here
                "backups": False,
                "ipv6": True,
                "monitoring": True,
                "tags": tags,
                "user_data": user_data
            }
            
            response = await self.client.post(
                f"{self.BASE_URL}/droplets",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 201:
                result = response.json()
                droplet = result.get('droplet', {})
                logger.info(f"✅ Created DigitalOcean droplet: {droplet.get('id')} - {name}")
                return {
                    "provider": "digitalocean",
                    "server_id": str(droplet.get('id')),
                    "name": name,
                    "region": region,
                    "status": droplet.get('status'),
                    "created_at": droplet.get('created_at'),
                    "ip_address": None,  # Will be available after creation
                    "ipv6_address": None
                }
            else:
                logger.error(f"Failed to create droplet: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating DigitalOcean server: {e}")
            return None
    
    async def get_server_info(self, server_id: str) -> Dict:
        """Get detailed information about a droplet"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/droplets/{server_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                droplet = result.get('droplet', {})
                
                # Extract IP addresses
                networks = droplet.get('networks', {})
                ipv4_address = None
                ipv6_address = None
                
                if networks.get('v4'):
                    ipv4_address = networks['v4'][0].get('ip_address')
                if networks.get('v6'):
                    ipv6_address = networks['v6'][0].get('ip_address')
                
                return {
                    "provider": "digitalocean",
                    "server_id": str(droplet.get('id')),
                    "name": droplet.get('name'),
                    "region": droplet.get('region', {}).get('slug'),
                    "status": droplet.get('status'),
                    "ip_address": ipv4_address,
                    "ipv6_address": ipv6_address,
                    "vcpus": droplet.get('vcpus'),
                    "memory": droplet.get('memory'),
                    "disk": droplet.get('disk'),
                    "created_at": droplet.get('created_at')
                }
            else:
                logger.error(f"Failed to get droplet info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting DigitalOcean server info: {e}")
            return None
    
    async def list_servers(self, tag: str = "vpn-server") -> List[Dict]:
        """List all VPN server droplets"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/droplets",
                headers=self.headers,
                params={"tag_name": tag}
            )
            
            if response.status_code == 200:
                result = response.json()
                droplets = result.get('droplets', [])
                
                servers = []
                for droplet in droplets:
                    networks = droplet.get('networks', {})
                    ipv4_address = None
                    if networks.get('v4'):
                        ipv4_address = networks['v4'][0].get('ip_address')
                    
                    servers.append({
                        "provider": "digitalocean",
                        "server_id": str(droplet.get('id')),
                        "name": droplet.get('name'),
                        "region": droplet.get('region', {}).get('slug'),
                        "status": droplet.get('status'),
                        "ip_address": ipv4_address
                    })
                
                return servers
            else:
                logger.error(f"Failed to list droplets: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing DigitalOcean servers: {e}")
            return []
    
    async def delete_server(self, server_id: str) -> bool:
        """Delete a droplet"""
        try:
            response = await self.client.delete(
                f"{self.BASE_URL}/droplets/{server_id}",
                headers=self.headers
            )
            
            if response.status_code == 204:
                logger.info(f"✅ Deleted DigitalOcean droplet: {server_id}")
                return True
            else:
                logger.error(f"Failed to delete droplet: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting DigitalOcean server: {e}")
            return False
    
    async def reboot_server(self, server_id: str) -> bool:
        """Reboot a droplet"""
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/droplets/{server_id}/actions",
                headers=self.headers,
                json={"type": "reboot"}
            )
            
            if response.status_code == 201:
                logger.info(f"✅ Rebooted DigitalOcean droplet: {server_id}")
                return True
            else:
                logger.error(f"Failed to reboot droplet: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error rebooting DigitalOcean server: {e}")
            return False
    
    async def get_available_regions(self) -> List[Dict]:
        """Get list of available regions"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/regions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                regions = result.get('regions', [])
                
                return [
                    {
                        "slug": r.get('slug'),
                        "name": r.get('name'),
                        "available": r.get('available'),
                        "features": r.get('features', [])
                    }
                    for r in regions if r.get('available')
                ]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting regions: {e}")
            return []


class VultrProvider(VPNProviderBase):
    """Vultr API integration for VPN server management"""
    
    BASE_URL = "https://api.vultr.com/v2"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def create_server(
        self,
        region: str,
        plan: str = "vc2-1c-1gb",
        name: str = None,
        tags: List[str] = None
    ) -> Dict:
        """Create a new Vultr instance for VPN server"""
        try:
            if not name:
                name = f"vpn-server-{region}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Get Ubuntu 22.04 OS ID
            os_response = await self.client.get(
                f"{self.BASE_URL}/os",
                headers=self.headers
            )
            
            ubuntu_os_id = 1743  # Ubuntu 22.04 LTS x64
            
            data = {
                "region": region,
                "plan": plan,
                "os_id": ubuntu_os_id,
                "label": name,
                "hostname": name,
                "enable_ipv6": True,
                "backups": "disabled",
                "tags": tags or ["vpn-server", "anonvpn"]
            }
            
            response = await self.client.post(
                f"{self.BASE_URL}/instances",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 202:
                result = response.json()
                instance = result.get('instance', {})
                logger.info(f"✅ Created Vultr instance: {instance.get('id')} - {name}")
                return {
                    "provider": "vultr",
                    "server_id": instance.get('id'),
                    "name": name,
                    "region": region,
                    "status": instance.get('status'),
                    "created_at": instance.get('date_created'),
                    "ip_address": instance.get('main_ip'),
                    "ipv6_address": instance.get('v6_main_ip')
                }
            else:
                logger.error(f"Failed to create Vultr instance: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating Vultr server: {e}")
            return None
    
    async def get_server_info(self, server_id: str) -> Dict:
        """Get detailed information about a Vultr instance"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/instances/{server_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                instance = result.get('instance', {})
                
                return {
                    "provider": "vultr",
                    "server_id": instance.get('id'),
                    "name": instance.get('label'),
                    "region": instance.get('region'),
                    "status": instance.get('status'),
                    "ip_address": instance.get('main_ip'),
                    "ipv6_address": instance.get('v6_main_ip'),
                    "vcpus": instance.get('vcpu_count'),
                    "memory": instance.get('ram'),
                    "disk": instance.get('disk'),
                    "created_at": instance.get('date_created')
                }
            else:
                logger.error(f"Failed to get Vultr instance info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Vultr server info: {e}")
            return None
    
    async def list_servers(self) -> List[Dict]:
        """List all Vultr VPN server instances"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/instances",
                headers=self.headers,
                params={"tag": "vpn-server"}
            )
            
            if response.status_code == 200:
                result = response.json()
                instances = result.get('instances', [])
                
                return [
                    {
                        "provider": "vultr",
                        "server_id": i.get('id'),
                        "name": i.get('label'),
                        "region": i.get('region'),
                        "status": i.get('status'),
                        "ip_address": i.get('main_ip')
                    }
                    for i in instances
                ]
            else:
                logger.error(f"Failed to list Vultr instances: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing Vultr servers: {e}")
            return []
    
    async def delete_server(self, server_id: str) -> bool:
        """Delete a Vultr instance"""
        try:
            response = await self.client.delete(
                f"{self.BASE_URL}/instances/{server_id}",
                headers=self.headers
            )
            
            if response.status_code == 204:
                logger.info(f"✅ Deleted Vultr instance: {server_id}")
                return True
            else:
                logger.error(f"Failed to delete Vultr instance: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting Vultr server: {e}")
            return False
    
    async def reboot_server(self, server_id: str) -> bool:
        """Reboot a Vultr instance"""
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/instances/{server_id}/reboot",
                headers=self.headers
            )
            
            if response.status_code == 204:
                logger.info(f"✅ Rebooted Vultr instance: {server_id}")
                return True
            else:
                logger.error(f"Failed to reboot Vultr instance: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error rebooting Vultr server: {e}")
            return False
    
    async def get_available_regions(self) -> List[Dict]:
        """Get list of available Vultr regions"""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/regions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                regions = result.get('regions', [])
                
                return [
                    {
                        "id": r.get('id'),
                        "city": r.get('city'),
                        "country": r.get('country'),
                        "continent": r.get('continent')
                    }
                    for r in regions
                ]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting Vultr regions: {e}")
            return []


# Factory function
def get_vpn_provider(provider: str, api_key: str) -> VPNProviderBase:
    """Factory function to get VPN provider instance"""
    providers = {
        "digitalocean": DigitalOceanProvider,
        "vultr": VultrProvider
    }
    
    provider_class = providers.get(provider.lower())
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return provider_class(api_key)
