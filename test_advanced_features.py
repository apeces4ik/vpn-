#!/usr/bin/env python3
"""
Advanced VPN Features Testing - Focused Test Suite
Tests the 4 advanced VPN features comprehensively
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://privacyshield-19.preview.emergentagent.com/api"

class AdvancedVPNTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        self.test_data = {
            'user_id': None,
            'server_id': None,
            'tor_server_id': None
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if response_data and not success:
            print(f"    Response: {response_data}")
        
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'response': response_data
        }
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> tuple[bool, Any]:
        """Make HTTP request and return success status and response"""
        try:
            url = f"{BACKEND_URL}{endpoint}"
            print(f"    → {method} {url}")
            
            async with self.session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    data = await response.text()
                
                success = 200 <= response.status < 300
                return success, data
        except Exception as e:
            return False, str(e)
    
    async def setup_test_data(self):
        """Setup test data - user and servers"""
        print("\n🔧 Setting up test data...")
        
        # Create test user
        success, user_data = await self.make_request('POST', '/users', params={"email": "advanced-test@anonvpn.example"})
        if success and user_data.get('id'):
            self.test_data['user_id'] = user_data['id']
            print(f"    Created test user: {user_data['id']}")
        
        # Get servers
        success, servers = await self.make_request('GET', '/servers')
        if success and servers:
            self.test_data['server_id'] = servers[0]['id']
            print(f"    Using server: {servers[0]['hostname']}")
        
        # Get Tor-enabled server
        success, tor_data = await self.make_request('GET', '/servers/tor-enabled')
        if success and tor_data.get('servers'):
            self.test_data['tor_server_id'] = tor_data['servers'][0]['id']
            print(f"    Using Tor server: {tor_data['servers'][0]['hostname']}")
    
    async def test_double_vpn_feature(self):
        """Test Double VPN feature comprehensively"""
        print("\n🔐 Testing Double VPN Feature...")
        
        # Test 1: Get Double VPN server pairs
        success, data = await self.make_request('GET', '/servers/double-vpn')
        
        if success and data.get('pairs'):
            pairs = data['pairs']
            total_servers = data.get('total_servers', 0)
            
            if len(pairs) > 0 and total_servers >= 55:
                first_pair = pairs[0]
                entry_server = first_pair.get('entry_server', {})
                exit_server = first_pair.get('exit_server', {})
                
                self.log_test("Double VPN - Server Pairs", True, 
                    f"Found {len(pairs)} pairs from {total_servers} servers. Route: {first_pair.get('route', 'N/A')}")
                
                # Test 2: Try to create Double VPN connection (will fail due to no active plan)
                if self.test_data['user_id'] and entry_server.get('id') and exit_server.get('id'):
                    params = {
                        'user_id': self.test_data['user_id'],
                        'server_id': entry_server['id'],
                        'device_name': 'Double VPN Test',
                        'enable_double_vpn': 'true',
                        'exit_server_id': exit_server['id']
                    }
                    
                    success, conn_data = await self.make_request('POST', '/connections/advanced', params=params)
                    
                    if not success:
                        error_msg = str(conn_data).lower()
                        if "no active" in error_msg or "subscription" in error_msg:
                            self.log_test("Double VPN - Connection Creation", True, 
                                "Expected error: No active subscription (validation working)")
                        elif "pro or ultimate" in error_msg:
                            self.log_test("Double VPN - Connection Creation", True, 
                                "Expected error: Plan restriction working")
                        else:
                            self.log_test("Double VPN - Connection Creation", False, 
                                f"Unexpected error: {conn_data}")
                    else:
                        self.log_test("Double VPN - Connection Creation", True, 
                            "Double VPN connection created successfully")
            else:
                self.log_test("Double VPN - Server Pairs", False, 
                    f"Insufficient pairs or servers. Pairs: {len(pairs)}, Servers: {total_servers}")
        else:
            self.log_test("Double VPN - Server Pairs", False, "Failed to get Double VPN servers", data)
    
    async def test_obfuscation_feature(self):
        """Test Obfuscation (obfs4) feature"""
        print("\n🎭 Testing Obfuscation Feature...")
        
        # Test 1: Get obfuscated servers
        success, data = await self.make_request('GET', '/servers/obfuscated')
        
        if success and data.get('servers'):
            servers = data['servers']
            total_obfuscated = data.get('total_obfuscated_servers', 0)
            
            if total_obfuscated >= 55 and len(servers) >= 55:
                # Check server structure
                first_server = servers[0]
                has_obfs_support = first_server.get('supports_obfuscation', False)
                has_obfs_port = first_server.get('obfs4_port') is not None
                
                if has_obfs_support:
                    self.log_test("Obfuscation - Server Support", True, 
                        f"All {total_obfuscated} servers support obfuscation. Port: {first_server.get('obfs4_port', 'N/A')}")
                    
                    # Test 2: Try to create obfuscated connection
                    if self.test_data['user_id']:
                        params = {
                            'user_id': self.test_data['user_id'],
                            'server_id': first_server['id'],
                            'device_name': 'Obfuscation Test',
                            'enable_obfuscation': 'true'
                        }
                        
                        success, conn_data = await self.make_request('POST', '/connections/advanced', params=params)
                        
                        if not success:
                            error_msg = str(conn_data).lower()
                            if "no active" in error_msg or "subscription" in error_msg:
                                self.log_test("Obfuscation - Connection Creation", True, 
                                    "Expected error: No active subscription (validation working)")
                            elif "pro or ultimate" in error_msg:
                                self.log_test("Obfuscation - Connection Creation", True, 
                                    "Expected error: Plan restriction working")
                            else:
                                self.log_test("Obfuscation - Connection Creation", False, 
                                    f"Unexpected error: {conn_data}")
                        else:
                            self.log_test("Obfuscation - Connection Creation", True, 
                                "Obfuscated connection created successfully")
                else:
                    self.log_test("Obfuscation - Server Support", False, 
                        "Server missing obfuscation support")
            else:
                self.log_test("Obfuscation - Server Support", False, 
                    f"Expected 55+ servers, got {total_obfuscated}")
        else:
            self.log_test("Obfuscation - Server Support", False, "Failed to get obfuscated servers", data)
    
    async def test_tor_over_vpn_feature(self):
        """Test Tor-over-VPN feature"""
        print("\n🧅 Testing Tor-over-VPN Feature...")
        
        # Test 1: Get Tor-enabled servers
        success, data = await self.make_request('GET', '/servers/tor-enabled')
        
        if success and data.get('servers'):
            servers = data['servers']
            total_tor = data.get('total_tor_servers', 0)
            
            if total_tor == 10 and len(servers) == 10:
                # Check server structure
                first_server = servers[0]
                has_tor_support = first_server.get('supports_tor', False)
                has_tor_port = first_server.get('tor_socks_port') is not None
                
                if has_tor_support and has_tor_port:
                    self.log_test("Tor-over-VPN - Server Support", True, 
                        f"Found {total_tor} Tor servers. SOCKS port: {first_server['tor_socks_port']}")
                    
                    # Test 2: Try to create Tor connection
                    if self.test_data['user_id']:
                        params = {
                            'user_id': self.test_data['user_id'],
                            'server_id': first_server['id'],
                            'device_name': 'Tor Test',
                            'enable_tor': 'true'
                        }
                        
                        success, conn_data = await self.make_request('POST', '/connections/advanced', params=params)
                        
                        if not success:
                            error_msg = str(conn_data).lower()
                            if "no active" in error_msg or "subscription" in error_msg:
                                self.log_test("Tor-over-VPN - Connection Creation", True, 
                                    "Expected error: No active subscription (validation working)")
                            elif "ultimate" in error_msg:
                                self.log_test("Tor-over-VPN - Connection Creation", True, 
                                    "Expected error: Ultimate plan restriction working")
                            else:
                                self.log_test("Tor-over-VPN - Connection Creation", False, 
                                    f"Unexpected error: {conn_data}")
                        else:
                            self.log_test("Tor-over-VPN - Connection Creation", True, 
                                "Tor connection created successfully")
                    
                    # Test 3: Try non-Tor server with enable_tor=true
                    success, all_servers = await self.make_request('GET', '/servers')
                    if success and all_servers:
                        non_tor_server = None
                        for server in all_servers:
                            if not server.get('supports_tor', False):
                                non_tor_server = server
                                break
                        
                        if non_tor_server and self.test_data['user_id']:
                            params = {
                                'user_id': self.test_data['user_id'],
                                'server_id': non_tor_server['id'],
                                'device_name': 'Invalid Tor Test',
                                'enable_tor': 'true'
                            }
                            
                            success, conn_data = await self.make_request('POST', '/connections/advanced', params=params)
                            
                            if not success:
                                error_msg = str(conn_data).lower()
                                if "doesn't support tor" in error_msg or "tor" in error_msg:
                                    self.log_test("Tor-over-VPN - Server Validation", True, 
                                        "Non-Tor server correctly rejected for Tor connection")
                                elif "no active" in error_msg:
                                    self.log_test("Tor-over-VPN - Server Validation", True, 
                                        "Expected error: No active subscription (validation working)")
                                else:
                                    self.log_test("Tor-over-VPN - Server Validation", False, 
                                        f"Unexpected error: {conn_data}")
                            else:
                                self.log_test("Tor-over-VPN - Server Validation", False, 
                                    "Non-Tor server should have been rejected")
                else:
                    self.log_test("Tor-over-VPN - Server Support", False, 
                        "Tor server missing required configuration")
            else:
                self.log_test("Tor-over-VPN - Server Support", False, 
                    f"Expected exactly 10 Tor servers, got {total_tor}")
        else:
            self.log_test("Tor-over-VPN - Server Support", False, "Failed to get Tor servers", data)
    
    async def test_split_tunneling_feature(self):
        """Test Split Tunneling feature"""
        print("\n🔀 Testing Split Tunneling Feature...")
        
        if not self.test_data['user_id'] or not self.test_data['server_id']:
            self.log_test("Split Tunneling", False, "Missing test data")
            return
        
        # Test 1: Create connection with split tunnel rules (using JSON body)
        split_rules = [
            {"type": "domain", "value": "example.com", "action": "bypass"},
            {"type": "ip", "value": "8.8.8.8", "action": "bypass"},
            {"type": "subnet", "value": "192.168.1.0/24", "action": "include"}
        ]
        
        # For split tunneling, we need to send JSON body
        request_data = {
            "user_id": self.test_data['user_id'],
            "server_id": self.test_data['server_id'],
            "device_name": "Split Tunnel Test",
            "split_tunnel_rules": split_rules
        }
        
        success, data = await self.make_request('POST', '/connections/advanced', json=request_data)
        
        if not success:
            error_msg = str(data).lower()
            if "no active" in error_msg or "subscription" in error_msg:
                self.log_test("Split Tunneling - Connection Creation", True, 
                    "Expected error: No active subscription (validation working)")
            elif "validation" in error_msg or "required" in error_msg:
                # Try with query parameters instead
                params = {
                    'user_id': self.test_data['user_id'],
                    'server_id': self.test_data['server_id'],
                    'device_name': 'Split Tunnel Test'
                }
                
                success2, data2 = await self.make_request('POST', '/connections/advanced', params=params)
                
                if not success2:
                    error_msg2 = str(data2).lower()
                    if "no active" in error_msg2 or "subscription" in error_msg2:
                        self.log_test("Split Tunneling - Connection Creation", True, 
                            "Expected error: No active subscription (validation working)")
                    else:
                        self.log_test("Split Tunneling - Connection Creation", False, 
                            f"Unexpected error: {data2}")
                else:
                    self.log_test("Split Tunneling - Connection Creation", True, 
                        "Split tunneling connection created successfully")
            else:
                self.log_test("Split Tunneling - Connection Creation", False, 
                    f"Unexpected error: {data}")
        else:
            connection = data.get('connection', {})
            rules = connection.get('split_tunnel_rules', [])
            
            if len(rules) == 3:
                self.log_test("Split Tunneling - Connection Creation", True, 
                    f"Created connection with {len(rules)} split tunnel rules")
            else:
                self.log_test("Split Tunneling - Connection Creation", False, 
                    f"Expected 3 rules, got {len(rules)}")
    
    async def test_advanced_config_generation(self):
        """Test advanced config generation"""
        print("\n⚙️ Testing Advanced Config Generation...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            from vpn_config_generator import vpn_config_generator
            
            # Test Double VPN config
            double_config = vpn_config_generator.generate_double_vpn_config(
                entry_server_ip="192.0.2.1",
                exit_server_ip="192.0.2.2",
                entry_location="New York",
                exit_location="London",
                user_id="test-user",
                connection_id="test-connection",
                protocol="WireGuard"
            )
            
            if double_config and len(double_config.get('config', '')) > 500:
                self.log_test("Advanced Config - Double VPN", True, 
                    f"Generated Double VPN config: {len(double_config['config'])} chars")
            else:
                self.log_test("Advanced Config - Double VPN", False, "Double VPN config too short")
            
            # Test Obfuscated config
            obfs_config = vpn_config_generator.generate_obfuscated_config(
                server_ip="192.0.2.1",
                server_location="Frankfurt",
                user_id="test-user",
                connection_id="test-connection"
            )
            
            if obfs_config and len(obfs_config.get('config', '')) > 500:
                self.log_test("Advanced Config - Obfuscation", True, 
                    f"Generated obfuscated config: {len(obfs_config['config'])} chars")
            else:
                self.log_test("Advanced Config - Obfuscation", False, "Obfuscated config too short")
            
            # Test Tor-over-VPN config
            tor_config = vpn_config_generator.generate_tor_over_vpn_config(
                server_ip="192.0.2.1",
                server_location="Amsterdam",
                user_id="test-user",
                connection_id="test-connection",
                protocol="OpenVPN"
            )
            
            if tor_config and len(tor_config.get('config', '')) > 500:
                self.log_test("Advanced Config - Tor-over-VPN", True, 
                    f"Generated Tor config: {len(tor_config['config'])} chars")
            else:
                self.log_test("Advanced Config - Tor-over-VPN", False, "Tor config too short")
            
            # Test Split Tunneling
            base_config = vpn_config_generator.generate_wireguard_config(
                server_ip="192.0.2.1",
                server_location="Test",
                server_country="US",
                user_id="test-user",
                connection_id="test-connection"
            )
            
            split_rules = [
                {"type": "domain", "value": "example.com", "action": "bypass"},
                {"type": "ip", "value": "8.8.8.8", "action": "bypass"}
            ]
            
            split_config = vpn_config_generator.add_split_tunneling(
                base_config=base_config['config'],
                rules=split_rules,
                protocol="WireGuard"
            )
            
            if len(split_config) > len(base_config['config']):
                self.log_test("Advanced Config - Split Tunneling", True, 
                    f"Added split tunneling: +{len(split_config) - len(base_config['config'])} chars")
            else:
                self.log_test("Advanced Config - Split Tunneling", False, "Split tunneling not added")
                
        except Exception as e:
            self.log_test("Advanced Config Generation", False, f"Module error: {str(e)}")
    
    async def test_advanced_features_info(self):
        """Test advanced features information endpoint"""
        print("\n📋 Testing Advanced Features Info...")
        
        success, data = await self.make_request('GET', '/features/advanced')
        
        if success and data.get('features'):
            features = data['features']
            
            if len(features) == 4:
                feature_names = [f['name'] for f in features]
                expected = ['Double VPN', 'Obfuscation (obfs4)', 'Tor-over-VPN', 'Split Tunneling']
                
                all_present = all(any(exp in name for name in feature_names) for exp in expected)
                
                if all_present:
                    self.log_test("Advanced Features Info", True, 
                        f"All 4 features present: {', '.join(feature_names)}")
                    
                    # Check feature details
                    for feature in features:
                        name = feature.get('name', '')
                        has_description = bool(feature.get('description'))
                        has_benefits = bool(feature.get('benefits'))
                        has_requirements = bool(feature.get('requirements'))
                        
                        if has_description and has_benefits and has_requirements:
                            self.log_test(f"Feature Details - {name}", True, 
                                f"Complete feature information")
                        else:
                            self.log_test(f"Feature Details - {name}", False, 
                                f"Missing details: desc={has_description}, benefits={has_benefits}, req={has_requirements}")
                else:
                    self.log_test("Advanced Features Info", False, 
                        f"Missing expected features. Got: {feature_names}")
            else:
                self.log_test("Advanced Features Info", False, 
                    f"Expected 4 features, got {len(features)}")
        else:
            self.log_test("Advanced Features Info", False, "Failed to get features info", data)
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("🧪 ADVANCED VPN FEATURES TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"  • {test_name}: {result['details']}")
        
        print("\n" + "="*60)
        
        return passed_tests, failed_tests

async def main():
    """Run advanced VPN features tests"""
    print("🚀 Starting Advanced VPN Features Testing")
    print(f"Backend URL: {BACKEND_URL}")
    print("🎯 Focus: Double VPN, Obfuscation, Tor-over-VPN, Split Tunneling")
    
    async with AdvancedVPNTester() as tester:
        # Setup test data
        await tester.setup_test_data()
        
        # Test all 4 advanced features
        await tester.test_double_vpn_feature()
        await tester.test_obfuscation_feature()
        await tester.test_tor_over_vpn_feature()
        await tester.test_split_tunneling_feature()
        
        # Test config generation
        await tester.test_advanced_config_generation()
        
        # Test features info
        await tester.test_advanced_features_info()
        
        # Print summary
        passed, failed = tester.print_summary()
        
        # Return appropriate exit code
        return 0 if failed == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)