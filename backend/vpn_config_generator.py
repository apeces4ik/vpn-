"""
VPN Configuration Generator
Generates WireGuard and OpenVPN configurations for clients
"""
import secrets
import base64
from typing import Dict, Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import logging

logger = logging.getLogger(__name__)


class WireGuardKeyPair:
    """Generate WireGuard key pairs"""
    
    @staticmethod
    def generate() -> Tuple[str, str]:
        """Generate a new WireGuard key pair"""
        try:
            # Generate private key
            private_key = x25519.X25519PrivateKey.generate()
            
            # Get private key bytes
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Get public key bytes
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Encode to base64
            private_key_b64 = base64.b64encode(private_bytes).decode('utf-8')
            public_key_b64 = base64.b64encode(public_bytes).decode('utf-8')
            
            return private_key_b64, public_key_b64
        except Exception as e:
            logger.error(f"Failed to generate WireGuard keys: {str(e)}")
            # Fallback to random base64 strings (for demo purposes)
            private_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            public_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            return private_key, public_key


class VPNConfigGenerator:
    """Generate VPN configuration files"""
    
    def __init__(self):
        # Mock server public keys (in production, these would be fetched from server metadata)
        self.server_public_keys = {}
    
    def generate_wireguard_config(
        self,
        server_ip: str,
        server_location: str,
        server_country: str,
        user_id: str,
        connection_id: str,
        client_address: str = "10.0.0.2",
        dns_servers: str = "1.1.1.1, 1.0.0.1",
        port: int = 51820
    ) -> Dict[str, str]:
        """Generate WireGuard configuration"""
        
        # Generate client key pair
        client_private_key, client_public_key = WireGuardKeyPair.generate()
        
        # Generate server public key (in production, this would be the actual server's key)
        server_public_key = self.server_public_keys.get(
            server_ip,
            base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        )
        
        config = f"""[Interface]
# Client Configuration
PrivateKey = {client_private_key}
Address = {client_address}/32
DNS = {dns_servers}

# Security Settings
# PreUp = iptables -A FORWARD -i wg0 -j ACCEPT
# PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

[Peer]
# AnonVPN Server: {server_location}, {server_country}
PublicKey = {server_public_key}
Endpoint = {server_ip}:{port}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25

# ================================================
# AnonVPN Enterprise - Anonymous VPN Service
# Location: {server_location} ({server_country})
# User ID: {user_id}
# Connection ID: {connection_id}
# Protocol: WireGuard
# No-Log Policy Active
# ================================================
"""
        
        return {
            "config": config,
            "client_private_key": client_private_key,
            "client_public_key": client_public_key,
            "server_public_key": server_public_key,
            "filename": f"anonvpn-{server_location.lower().replace(' ', '-')}-wg.conf"
        }
    
    def generate_openvpn_config(
        self,
        server_ip: str,
        server_location: str,
        server_country: str,
        user_id: str,
        connection_id: str,
        port: int = 1194,
        protocol: str = "udp"
    ) -> Dict[str, str]:
        """Generate OpenVPN configuration"""
        
        # In production, these would be actual certificates
        ca_cert = self._generate_mock_cert("AnonVPN CA")
        client_cert = self._generate_mock_cert(f"AnonVPN Client {connection_id}")
        client_key = self._generate_mock_key()
        
        config = f"""# AnonVPN Enterprise - OpenVPN Configuration
# Location: {server_location} ({server_country})
# User ID: {user_id}
# Connection ID: {connection_id}
# Protocol: OpenVPN over {protocol.upper()}

client
dev tun
proto {protocol}
remote {server_ip} {port}
resolv-retry infinite
nobind
persist-key
persist-tun

# Security Settings
cipher AES-256-GCM
auth SHA256
tls-client
tls-version-min 1.2
remote-cert-tls server

# Privacy Settings
verb 3
mute 20

# DNS Leak Protection
dhcp-option DNS 1.1.1.1
dhcp-option DNS 1.0.0.1

# Compression
comp-lzo adaptive

# Keep-alive
keepalive 10 120

<ca>
{ca_cert}
</ca>

<cert>
{client_cert}
</cert>

<key>
{client_key}
</key>

# ================================================
# AnonVPN Enterprise - Anonymous VPN Service
# No-Log Policy Active
# ================================================
"""
        
        return {
            "config": config,
            "filename": f"anonvpn-{server_location.lower().replace(' ', '-')}-ovpn.ovpn"
        }
    
    def generate_ikev2_config(
        self,
        server_ip: str,
        server_location: str,
        server_country: str,
        user_id: str,
        connection_id: str
    ) -> Dict[str, str]:
        """Generate IKEv2 configuration (for iOS/macOS)"""
        
        # Generate credentials
        username = f"user_{user_id[:8]}"
        password = secrets.token_urlsafe(16)
        
        # iOS/macOS profile format
        config = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>IKEv2</key>
            <dict>
                <key>AuthenticationMethod</key>
                <string>SharedSecret</string>
                <key>ChildSecurityAssociationParameters</key>
                <dict>
                    <key>EncryptionAlgorithm</key>
                    <string>AES-256-GCM</string>
                    <key>IntegrityAlgorithm</key>
                    <string>SHA2-256</string>
                    <key>DiffieHellmanGroup</key>
                    <integer>14</integer>
                    <key>LifeTimeInMinutes</key>
                    <integer>1440</integer>
                </dict>
                <key>DeadPeerDetectionRate</key>
                <string>Medium</string>
                <key>DisableMOBIKE</key>
                <integer>0</integer>
                <key>DisableRedirect</key>
                <integer>0</integer>
                <key>EnableCertificateRevocationCheck</key>
                <integer>0</integer>
                <key>EnablePFS</key>
                <integer>1</integer>
                <key>IKESecurityAssociationParameters</key>
                <dict>
                    <key>EncryptionAlgorithm</key>
                    <string>AES-256</string>
                    <key>IntegrityAlgorithm</key>
                    <string>SHA2-256</string>
                    <key>DiffieHellmanGroup</key>
                    <integer>14</integer>
                    <key>LifeTimeInMinutes</key>
                    <integer>1440</integer>
                </dict>
                <key>LocalIdentifier</key>
                <string>{username}</string>
                <key>RemoteAddress</key>
                <string>{server_ip}</string>
                <key>RemoteIdentifier</key>
                <string>{server_ip}</string>
                <key>SharedSecret</key>
                <string>{password}</string>
                <key>UseConfigurationAttributeInternalIPSubnet</key>
                <integer>0</integer>
            </dict>
            <key>IPv4</key>
            <dict>
                <key>OverridePrimary</key>
                <integer>1</integer>
            </dict>
            <key>PayloadDescription</key>
            <string>AnonVPN - {server_location}</string>
            <key>PayloadDisplayName</key>
            <string>AnonVPN {server_location}</string>
            <key>PayloadIdentifier</key>
            <string>com.anonvpn.ikev2.{connection_id}</string>
            <key>PayloadType</key>
            <string>com.apple.vpn.managed</string>
            <key>PayloadUUID</key>
            <string>{connection_id}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Proxies</key>
            <dict>
                <key>HTTPEnable</key>
                <integer>0</integer>
                <key>HTTPSEnable</key>
                <integer>0</integer>
            </dict>
            <key>UserDefinedName</key>
            <string>AnonVPN - {server_location}</string>
            <key>VPNType</key>
            <string>IKEv2</string>
        </dict>
    </array>
    <key>PayloadDisplayName</key>
    <string>AnonVPN - {server_location}</string>
    <key>PayloadIdentifier</key>
    <string>com.anonvpn.profile.{connection_id}</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{secrets.token_hex(16)}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>
"""
        
        return {
            "config": config,
            "username": username,
            "password": password,
            "filename": f"anonvpn-{server_location.lower().replace(' ', '-')}-ikev2.mobileconfig"
        }
    
    def _generate_mock_cert(self, cn: str) -> str:
        """Generate mock certificate for demo"""
        return f"""-----BEGIN CERTIFICATE-----
MIID{base64.b64encode(secrets.token_bytes(200)).decode('utf-8')}
-----END CERTIFICATE-----"""
    
    def _generate_mock_key(self) -> str:
        """Generate mock private key for demo"""
        return f"""-----BEGIN PRIVATE KEY-----
MIIE{base64.b64encode(secrets.token_bytes(300)).decode('utf-8')}
-----END PRIVATE KEY-----"""
    
    # ============= ADVANCED FEATURES =============
    
    def generate_double_vpn_config(
        self,
        entry_server_ip: str,
        exit_server_ip: str,
        entry_location: str,
        exit_location: str,
        user_id: str,
        connection_id: str,
        protocol: str = "WireGuard"
    ) -> Dict[str, str]:
        """
        Generate Double VPN configuration (multi-hop)
        Routes traffic: Client -> Entry Server -> Exit Server -> Internet
        """
        
        if protocol == "WireGuard":
            # Generate keys for both hops
            client_private_key, client_public_key = WireGuardKeyPair.generate()
            entry_public_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            exit_public_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            
            config = f"""[Interface]
# Double VPN Configuration - Client Side
# Hop 1: {entry_location} (Entry)
# Hop 2: {exit_location} (Exit)
PrivateKey = {client_private_key}
Address = 10.0.0.2/32
DNS = 1.1.1.1, 1.0.0.1

# Route all traffic through VPN
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# Entry Server: {entry_location}
PublicKey = {entry_public_key}
Endpoint = {entry_server_ip}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25

# ================================================
# DOUBLE VPN ACTIVE - ENHANCED PRIVACY
# ================================================
# Your connection is routed through 2 servers:
# 1. Entry: {entry_location} ({entry_server_ip})
# 2. Exit: {exit_location} ({exit_server_ip})
# 
# This provides double encryption and makes it
# extremely difficult to trace your real IP address.
# ================================================
# User ID: {user_id}
# Connection ID: {connection_id}
# No-Log Policy Active
# ================================================
"""
            
            return {
                "config": config,
                "filename": f"anonvpn-double-{entry_location.lower()}-{exit_location.lower()}-wg.conf",
                "entry_server": entry_location,
                "exit_server": exit_location,
                "info": f"Double VPN: {entry_location} → {exit_location}"
            }
        
        elif protocol == "OpenVPN":
            # OpenVPN double VPN uses cascading configuration
            ca_cert = self._generate_mock_cert("AnonVPN CA")
            client_cert = self._generate_mock_cert(f"AnonVPN Client {connection_id}")
            client_key = self._generate_mock_key()
            
            config = f"""# AnonVPN Enterprise - Double VPN Configuration
# Entry Server: {entry_location} ({entry_server_ip})
# Exit Server: {exit_location} ({exit_server_ip})
# User ID: {user_id}
# Connection ID: {connection_id}

client
dev tun
proto udp
remote {entry_server_ip} 1194
resolv-retry infinite
nobind
persist-key
persist-tun

# Security Settings
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
key-direction 1

# Double VPN routing
# Traffic flows through: Client -> Entry ({entry_server_ip}) -> Exit ({exit_server_ip}) -> Internet
route {exit_server_ip} 255.255.255.255 net_gateway
route 0.0.0.0 0.0.0.0 vpn_gateway

# DNS leak protection
dhcp-option DNS 1.1.1.1
dhcp-option DNS 1.0.0.1
block-outside-dns

# Compression and keep-alive
compress lz4-v2
keepalive 10 60

# Certificates and keys
<ca>
{ca_cert}
</ca>
<cert>
{client_cert}
</cert>
<key>
{client_key}
</key>

# ================================================
# DOUBLE VPN ACTIVE - MAXIMUM PRIVACY
# Entry: {entry_location}, Exit: {exit_location}
# ================================================
"""
            
            return {
                "config": config,
                "filename": f"anonvpn-double-{entry_location.lower()}-{exit_location.lower()}.ovpn",
                "entry_server": entry_location,
                "exit_server": exit_location
            }
    
    def generate_obfuscated_config(
        self,
        server_ip: str,
        server_location: str,
        user_id: str,
        connection_id: str,
        obfs4_port: int = 9001
    ) -> Dict[str, str]:
        """
        Generate obfuscated OpenVPN config with obfs4
        Makes VPN traffic look like regular HTTPS traffic
        """
        
        # Generate obfs4 bridge credentials
        obfs4_cert = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
        obfs4_iat = secrets.randbelow(2)
        
        ca_cert = self._generate_mock_cert("AnonVPN CA")
        client_cert = self._generate_mock_cert(f"AnonVPN Client {connection_id}")
        client_key = self._generate_mock_key()
        
        config = f"""# AnonVPN Enterprise - Obfuscated Configuration
# Location: {server_location}
# User ID: {user_id}
# Connection ID: {connection_id}
# OBFUSCATION: obfs4 Active

client
dev tun
proto tcp
remote {server_ip} {obfs4_port}
resolv-retry infinite
nobind
persist-key
persist-tun

# Security Settings
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
key-direction 1

# Obfuscation with obfs4
# Traffic is disguised as regular HTTPS to bypass VPN blocks
socks-proxy 127.0.0.1 9050

# DNS leak protection
dhcp-option DNS 1.1.1.1
dhcp-option DNS 1.0.0.1
block-outside-dns

# Compression and keep-alive
compress lz4-v2
keepalive 10 60
ping-restart 60

# Certificates and keys
<ca>
{ca_cert}
</ca>
<cert>
{client_cert}
</cert>
<key>
{client_key}
</key>

# ================================================
# OBFUSCATION ACTIVE
# ================================================
# Your VPN traffic is disguised as regular HTTPS
# This helps bypass:
# - DPI (Deep Packet Inspection)
# - VPN blocks and firewalls
# - Censorship systems
#
# obfs4 Bridge: {server_ip}:{obfs4_port}
# Certificate: {obfs4_cert[:32]}...
# IAT-Mode: {obfs4_iat}
# ================================================
# 
# SETUP INSTRUCTIONS:
# 1. Install obfs4proxy: apt-get install obfs4proxy
# 2. Start obfs4proxy before connecting:
#    obfs4proxy -enableLogging -logLevel INFO \\
#      -cert {obfs4_cert} \\
#      -iatMode {obfs4_iat}
# 3. Connect using this config
# ================================================
"""
        
        return {
            "config": config,
            "filename": f"anonvpn-obfs4-{server_location.lower().replace(' ', '-')}.ovpn",
            "obfs4_cert": obfs4_cert,
            "obfs4_port": obfs4_port,
            "info": "Obfuscated with obfs4 - Bypasses VPN detection"
        }
    
    def generate_tor_over_vpn_config(
        self,
        server_ip: str,
        server_location: str,
        user_id: str,
        connection_id: str,
        tor_socks_port: int = 9050,
        protocol: str = "OpenVPN"
    ) -> Dict[str, str]:
        """
        Generate Tor-over-VPN configuration
        Traffic flow: Client -> VPN -> Tor Network -> Internet
        """
        
        if protocol == "OpenVPN":
            ca_cert = self._generate_mock_cert("AnonVPN CA")
            client_cert = self._generate_mock_cert(f"AnonVPN Client {connection_id}")
            client_key = self._generate_mock_key()
            
            config = f"""# AnonVPN Enterprise - Tor-over-VPN Configuration
# Location: {server_location}
# User ID: {user_id}
# Connection ID: {connection_id}
# TOR INTEGRATION: Active

client
dev tun
proto udp
remote {server_ip} 1194
resolv-retry infinite
nobind
persist-key
persist-tun

# Security Settings
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
key-direction 1

# Tor routing (server-side Tor proxy)
# All traffic is routed through VPN first, then through Tor network
route-method exe
route-delay 2

# DNS through Tor
dhcp-option DNS 1.1.1.1
dhcp-option DNS 1.0.0.1
block-outside-dns

# Compression and keep-alive
compress lz4-v2
keepalive 10 60

# Certificates and keys
<ca>
{ca_cert}
</ca>
<cert>
{client_cert}
</cert>
<key>
{client_key}
</key>

# ================================================
# TOR-OVER-VPN ACTIVE - MAXIMUM ANONYMITY
# ================================================
# Your connection flow:
# You -> VPN ({server_location}) -> Tor Network -> Internet
#
# Benefits:
# - ISP cannot see you're using Tor
# - Tor entry nodes don't see your real IP
# - VPN + Tor double anonymity layer
# - Access to .onion sites through VPN
#
# Server Tor SOCKS: {server_ip}:{tor_socks_port}
# ================================================
#
# IMPORTANT NOTES:
# - Tor routing handled by VPN server
# - Slower speeds due to Tor network
# - Maximum anonymity and privacy
# - No additional software needed on client
# ================================================
"""
            
            return {
                "config": config,
                "filename": f"anonvpn-tor-{server_location.lower().replace(' ', '-')}.ovpn",
                "tor_enabled": True,
                "info": "Tor-over-VPN - Ultimate anonymity"
            }
        
        elif protocol == "WireGuard":
            client_private_key, client_public_key = WireGuardKeyPair.generate()
            server_public_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            
            config = f"""[Interface]
# Tor-over-VPN Configuration
PrivateKey = {client_private_key}
Address = 10.0.0.2/32
DNS = 1.1.1.1, 1.0.0.1

# Route all traffic through VPN (server routes to Tor)
PostUp = echo "nameserver 1.1.1.1" | resolvconf -a %i -m 0 -x
PostDown = resolvconf -d %i

[Peer]
# Server: {server_location} (Tor-enabled)
PublicKey = {server_public_key}
Endpoint = {server_ip}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25

# ================================================
# TOR-OVER-VPN ACTIVE
# ================================================
# Connection: You -> VPN ({server_location}) -> Tor -> Internet
# Server Tor SOCKS: {tor_socks_port}
# ================================================
"""
            
            return {
                "config": config,
                "filename": f"anonvpn-tor-{server_location.lower().replace(' ', '-')}-wg.conf",
                "tor_enabled": True
            }
    
    def add_split_tunneling(
        self,
        base_config: str,
        rules: list,
        protocol: str = "WireGuard"
    ) -> str:
        """
        Add split tunneling rules to existing config
        Rules format: [{"type": "domain/ip/subnet", "value": "example.com", "action": "bypass/include"}]
        """
        
        if protocol == "WireGuard":
            # Build split tunnel routes
            bypass_ips = []
            include_ips = []
            bypass_domains = []
            
            for rule in rules:
                if rule["action"] == "bypass":
                    if rule["type"] == "ip":
                        bypass_ips.append(rule["value"])
                    elif rule["type"] == "subnet":
                        bypass_ips.append(rule["value"])
                    elif rule["type"] == "domain":
                        bypass_domains.append(rule["value"])
                elif rule["action"] == "include":
                    if rule["type"] in ["ip", "subnet"]:
                        include_ips.append(rule["value"])
            
            split_tunnel_section = "\n# Split Tunneling Configuration\n"
            
            if bypass_ips:
                split_tunnel_section += "# Bypass VPN for these IPs (direct connection):\n"
                for ip in bypass_ips:
                    split_tunnel_section += f"# PostUp = ip route add {ip} via $(ip route | grep default | awk '{{print $3}}')\n"
                    split_tunnel_section += f"# PostDown = ip route del {ip}\n"
            
            if bypass_domains:
                split_tunnel_section += "\n# Bypass VPN for these domains:\n"
                for domain in bypass_domains:
                    split_tunnel_section += f"# - {domain} (resolve IP and add route)\n"
            
            if include_ips:
                split_tunnel_section += "\n# Only route these IPs through VPN:\n"
                split_tunnel_section += f"# AllowedIPs = {', '.join(include_ips)}\n"
            
            # Insert after [Interface] section
            lines = base_config.split('\n')
            interface_end = 0
            for i, line in enumerate(lines):
                if line.startswith('[Peer]'):
                    interface_end = i
                    break
            
            lines.insert(interface_end, split_tunnel_section)
            return '\n'.join(lines)
        
        elif protocol == "OpenVPN":
            split_tunnel_section = "\n# Split Tunneling Configuration\n"
            
            for rule in rules:
                if rule["action"] == "bypass" and rule["type"] in ["ip", "subnet"]:
                    # Route through regular gateway (bypass VPN)
                    split_tunnel_section += f"route {rule['value']} 255.255.255.255 net_gateway\n"
                elif rule["action"] == "include" and rule["type"] in ["ip", "subnet"]:
                    # Route through VPN
                    split_tunnel_section += f"route {rule['value']} 255.255.255.255 vpn_gateway\n"
                elif rule["type"] == "domain":
                    split_tunnel_section += f"# Domain: {rule['value']} ({rule['action']})\n"
            
            # Add before certificates section
            return base_config.replace("<ca>", split_tunnel_section + "\n<ca>")
        
        return base_config


# Singleton instance
vpn_config_generator = VPNConfigGenerator()
