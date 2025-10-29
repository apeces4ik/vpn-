"""
Proxy Manager for Web-VPN
Manages SOCKS5/HTTP proxy connections through VPNGate servers
"""

import asyncio
import logging
import httpx
from typing import Dict, Optional, List
from datetime import datetime
import subprocess
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyConnection:
    """Represents an active proxy connection"""
    
    def __init__(self, server_ip: str, server_config: str, connection_id: str):
        self.server_ip = server_ip
        self.server_config = server_config
        self.connection_id = connection_id
        self.process = None
        self.status = "disconnected"
        self.connected_at = None
        self.proxy_port = 1080  # SOCKS5 proxy port
        self.http_proxy_port = 8080  # HTTP proxy port
        
    async def connect(self) -> Dict:
        """
        Connect to VPNGate server using OpenVPN config
        Returns proxy connection details
        """
        try:
            logger.info(f"🔌 Attempting to connect to VPN server {self.server_ip}")
            
            # For now, return simulated proxy details
            # In production, this would establish actual OpenVPN connection
            self.status = "connected"
            self.connected_at = datetime.now()
            
            return {
                "status": "connected",
                "proxy_type": "socks5",
                "proxy_host": "localhost",
                "proxy_port": self.proxy_port,
                "http_proxy_port": self.http_proxy_port,
                "server_ip": self.server_ip,
                "connected_at": self.connected_at.isoformat(),
                "pac_url": f"/api/proxy/pac/{self.connection_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
            self.status = "error"
            raise
    
    async def disconnect(self):
        """Disconnect from VPN"""
        try:
            if self.process:
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            
            self.status = "disconnected"
            self.connected_at = None
            logger.info(f"✅ Disconnected from {self.server_ip}")
            
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
    
    def get_status(self) -> Dict:
        """Get current connection status"""
        return {
            "connection_id": self.connection_id,
            "status": self.status,
            "server_ip": self.server_ip,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "proxy_host": "localhost" if self.status == "connected" else None,
            "proxy_port": self.proxy_port if self.status == "connected" else None
        }


class ProxyManager:
    """Manages proxy connections for web-based VPN"""
    
    def __init__(self):
        self.active_connections: Dict[str, ProxyConnection] = {}
        self.public_proxies: List[Dict] = []
        
    async def get_available_proxies(self) -> List[Dict]:
        """
        Get list of available public proxies from VPNGate servers
        These are existing public proxies we can use directly
        """
        try:
            # Fetch list of public SOCKS/HTTP proxies
            # Many VPNGate servers have open proxies
            proxies = [
                {
                    "id": "proxy-001",
                    "type": "socks5",
                    "host": "vpn-gate-proxy-1.example.com",
                    "port": 1080,
                    "country": "Japan",
                    "country_code": "JP",
                    "speed_mbps": 5.2,
                    "available": True
                },
                {
                    "id": "proxy-002", 
                    "type": "http",
                    "host": "vpn-gate-proxy-2.example.com",
                    "port": 8080,
                    "country": "United States",
                    "country_code": "US", 
                    "speed_mbps": 8.5,
                    "available": True
                }
            ]
            
            return proxies
            
        except Exception as e:
            logger.error(f"Error fetching proxies: {str(e)}")
            return []
    
    async def create_connection(self, user_id: str, server_ip: str, 
                               server_config: str, connection_id: str) -> Dict:
        """
        Create new proxy connection for user
        """
        try:
            # Check if user already has active connection
            existing = self.active_connections.get(user_id)
            if existing and existing.status == "connected":
                await existing.disconnect()
            
            # Create new connection
            connection = ProxyConnection(server_ip, server_config, connection_id)
            result = await connection.connect()
            
            # Store connection
            self.active_connections[user_id] = connection
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            raise
    
    async def disconnect_user(self, user_id: str) -> Dict:
        """Disconnect user from VPN"""
        connection = self.active_connections.get(user_id)
        
        if not connection:
            return {"status": "not_connected", "message": "No active connection found"}
        
        await connection.disconnect()
        del self.active_connections[user_id]
        
        return {"status": "disconnected", "message": "Successfully disconnected"}
    
    def get_user_connection(self, user_id: str) -> Optional[Dict]:
        """Get user's current connection status"""
        connection = self.active_connections.get(user_id)
        return connection.get_status() if connection else None
    
    def generate_pac_file(self, proxy_host: str, proxy_port: int) -> str:
        """
        Generate PAC (Proxy Auto-Config) file for browser
        This allows automatic proxy configuration in browser
        """
        pac_content = f"""
function FindProxyForURL(url, host) {{
    // Use proxy for all connections
    return "SOCKS5 {proxy_host}:{proxy_port}; DIRECT";
}}
"""
        return pac_content
    
    def get_manual_config_instructions(self, proxy_host: str, proxy_port: int, 
                                      proxy_type: str = "socks5") -> Dict:
        """
        Get manual proxy configuration instructions for different browsers
        """
        return {
            "proxy_type": proxy_type.upper(),
            "proxy_host": proxy_host,
            "proxy_port": proxy_port,
            "instructions": {
                "chrome": {
                    "windows": [
                        "1. Open Chrome Settings",
                        "2. Search for 'proxy'",
                        "3. Click 'Open your computer's proxy settings'",
                        f"4. Enable 'Use a proxy server' and enter: {proxy_host}:{proxy_port}",
                        "5. Save and restart Chrome"
                    ],
                    "mac": [
                        "1. Open System Settings → Network",
                        "2. Select your active connection → Advanced → Proxies",
                        f"3. Enable 'SOCKS Proxy' and enter: {proxy_host}:{proxy_port}",
                        "4. Click OK and Apply"
                    ],
                    "linux": [
                        "1. Open Settings → Network → Network Proxy",
                        f"2. Set Method to 'Manual', SOCKS Host: {proxy_host}, Port: {proxy_port}",
                        "3. Click Apply"
                    ]
                },
                "firefox": {
                    "all": [
                        "1. Open Firefox Settings → General → Network Settings",
                        "2. Click 'Settings'",
                        "3. Select 'Manual proxy configuration'",
                        f"4. SOCKS Host: {proxy_host}, Port: {proxy_port}",
                        "5. Select 'SOCKS v5'",
                        "6. Enable 'Proxy DNS when using SOCKS v5'",
                        "7. Click OK"
                    ]
                },
                "system": {
                    "note": "System-wide proxy will route all applications through VPN"
                }
            }
        }


# Singleton instance
proxy_manager = ProxyManager()
