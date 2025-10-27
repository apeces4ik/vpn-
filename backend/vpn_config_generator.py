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


# Singleton instance
vpn_config_generator = VPNConfigGenerator()
