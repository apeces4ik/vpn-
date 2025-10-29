"""
VPN Gate Parser - Free VPN Servers from vpngate.net
Парсит публичные бесплатные VPN серверы для демо/тестирования
"""

import httpx
import base64
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VPNGateParser:
    """Parser for VPN Gate public servers"""
    
    API_URL = "http://www.vpngate.net/api/iphone/"
    
    async def fetch_servers(self, limit: int = 20, min_speed: int = 1000000) -> List[Dict]:
        """
        Fetch top VPN servers from VPN Gate
        
        Args:
            limit: Maximum number of servers to return
            min_speed: Minimum speed in bytes/sec (default 1 Mbps)
            
        Returns:
            List of server dictionaries with parsed data
        """
        try:
            logger.info(f"🌐 Fetching VPN Gate servers (limit: {limit}, min_speed: {min_speed/1_000_000}Mbps)")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.API_URL)
                response.raise_for_status()
                
                # Parse CSV data
                lines = response.text.strip().split('\n')
                
                # Skip header and comment lines (first 2 lines)
                servers_data = []
                for line in lines[2:]:
                    if line.startswith('*') or not line.strip():
                        continue
                    
                    try:
                        server = self._parse_server_line(line)
                        if server and server['speed'] >= min_speed:
                            servers_data.append(server)
                    except Exception as e:
                        logger.warning(f"Failed to parse server line: {e}")
                        continue
                
                # Sort by score (speed + uptime + ping)
                servers_data.sort(key=lambda x: x['score'], reverse=True)
                
                # Take top servers
                top_servers = servers_data[:limit]
                
                logger.info(f"✅ Successfully parsed {len(top_servers)} VPN Gate servers")
                return top_servers
                
        except Exception as e:
            logger.error(f"❌ Error fetching VPN Gate servers: {str(e)}")
            return []
    
    def _parse_server_line(self, line: str) -> Optional[Dict]:
        """Parse single CSV line from VPN Gate API"""
        parts = line.split(',')
        
        if len(parts) < 15:
            return None
        
        try:
            # VPN Gate CSV format:
            # 0: HostName
            # 1: IP
            # 2: Score (higher is better)
            # 3: Ping (ms)
            # 4: Speed (bytes/sec)
            # 5: CountryLong
            # 6: CountryShort (2-letter code)
            # 7: NumVpnSessions
            # 8: Uptime (ms)
            # 14: OpenVPN Config (base64)
            
            hostname = parts[0].strip()
            ip = parts[1].strip()
            score = int(parts[2].strip()) if parts[2].strip() else 0
            ping = int(parts[3].strip()) if parts[3].strip() else 999
            speed = int(parts[4].strip()) if parts[4].strip() else 0
            country_name = parts[5].strip()
            country_code = parts[6].strip()
            sessions = int(parts[7].strip()) if parts[7].strip() else 0
            uptime = int(parts[8].strip()) if parts[8].strip() else 0
            
            # Calculate uptime in days
            uptime_days = uptime / (1000 * 60 * 60 * 24) if uptime > 0 else 0
            
            # Parse OpenVPN config if available
            ovpn_config = None
            if len(parts) > 14 and parts[14].strip():
                try:
                    ovpn_config = base64.b64decode(parts[14].strip()).decode('utf-8')
                except:
                    pass
            
            return {
                'hostname': hostname or f"vpngate-{ip.replace('.', '-')}",
                'ip': ip,
                'score': score,
                'ping': ping,
                'speed': speed,
                'speed_mbps': round(speed / 1_000_000, 2),
                'country_name': country_name,
                'country_code': country_code.upper() if country_code else 'XX',
                'sessions': sessions,
                'uptime': uptime,
                'uptime_days': round(uptime_days, 1),
                'ovpn_config': ovpn_config
            }
            
        except Exception as e:
            logger.debug(f"Error parsing server line: {e}")
            return None
    
    def format_for_database(self, servers: List[Dict]) -> List[Dict]:
        """
        Format parsed servers for database insertion
        Compatible with VPNServer model
        """
        formatted = []
        
        for idx, server in enumerate(servers, 1):
            formatted.append({
                'id': f"vpngate-{idx:03d}",
                'hostname': f"{server['hostname']}.vpngate.net",
                'location': server['country_name'],
                'country_code': server['country_code'],
                'ipv4_address': server['ip'],
                'provider': 'VPNGate',
                'is_active': True,
                'current_connections': server['sessions'],
                'max_capacity': 100,
                'protocols': ['OpenVPN'],  # VPN Gate primarily supports OpenVPN
                'supports_double_vpn': False,  # Community servers don't support advanced features
                'supports_obfuscation': False,
                'supports_tor': False,
                'obfs4_port': None,
                'tor_socks_port': None,
                'created_at': datetime.now()
            })
        
        return formatted


# Singleton instance
vpn_gate_parser = VPNGateParser()
