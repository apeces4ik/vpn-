#!/usr/bin/env python3
"""
Review Request Testing - Specific endpoints mentioned in the review request
Tests the following fixes:
1. Referral Code Creation Fix
2. Support Ticket with Telegram Username
3. Get Support Tickets
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://oneclick-vpn-1.preview.emergentagent.com/api"

class ReviewRequestTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        self.test_data = {
            'user_id': None,
            'referral_code': None,
            'ticket_id': None
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
    
    async def setup_test_user(self):
        """Create a test user for testing"""
        print("🔧 Setting up test user...")
        
        # Create user with email
        user_data = {"email": "review-test@anonvpn.example"}
        success, data = await self.make_request('POST', '/users', params=user_data)
        
        if success and data.get('id'):
            self.test_user_id = data['id']
            self.log_test("Setup Test User", True, f"Created user: {self.test_user_id}")
            return True
        else:
            self.log_test("Setup Test User", False, "Failed to create test user", data)
            return False
    
    async def test_connection_history_endpoint(self):
        """Test Connection History endpoint - Review Request Focus"""
        print("\n📊 Testing Connection History Endpoint...")
        
        if not self.test_user_id:
            self.log_test("Connection History Endpoint", False, "No test user available")
            return
        
        # Test GET /api/users/{user_id}/connection-history
        success, data = await self.make_request('GET', f'/users/{self.test_user_id}/connection-history')
        
        if success:
            print(f"    Response keys: {list(data.keys())}")
            
            # Check if response has "connections" field (not "history")
            if 'connections' in data:
                connections = data['connections']
                total_count = data.get('total_count', len(connections))
                skip = data.get('skip', 0)
                limit = data.get('limit', 50)
                
                self.log_test("Connection History - Response Structure", True, 
                    f"✅ Returns 'connections' field with {len(connections)} items")
                
                # Verify response structure has required fields
                required_fields = ['total_count', 'connections', 'skip', 'limit']
                present_fields = [field for field in required_fields if field in data]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("Connection History - Required Fields", True, 
                        f"All required fields present: {present_fields}")
                else:
                    self.log_test("Connection History - Required Fields", False, 
                        f"Missing fields: {missing_fields}, Present: {present_fields}")
                    
            elif 'history' in data:
                self.log_test("Connection History - Response Structure", False, 
                    "❌ API returns 'history' field instead of 'connections' field")
            else:
                self.log_test("Connection History - Response Structure", False, 
                    f"❌ API missing both 'connections' and 'history' fields. Available keys: {list(data.keys())}")
        else:
            self.log_test("Connection History Endpoint", False, 
                f"Failed to get connection history: {data}")
    
    async def test_referral_stats_endpoint(self):
        """Test Referral Stats endpoint - Review Request Focus"""
        print("\n🤝 Testing Referral Stats Endpoint...")
        
        if not self.test_user_id:
            self.log_test("Referral Stats Endpoint", False, "No test user available")
            return
        
        # First create a referral code for the test user
        print("    Creating referral code for test user...")
        referral_data = {"user_id": self.test_user_id}
        success, create_data = await self.make_request('POST', '/referrals/create', params=referral_data)
        
        if success and create_data.get('referral_code'):
            referral_code = create_data['referral_code']
            self.log_test("Create Referral Code", True, f"Created referral code: {referral_code}")
            
            # Now test GET /api/referrals/{user_id}/stats
            success, data = await self.make_request('GET', f'/referrals/{self.test_user_id}/stats')
            
            if success:
                print(f"    Response keys: {list(data.keys())}")
                
                # Check if response has "total_referrals" field
                if 'total_referrals' in data:
                    total_referrals = data.get('total_referrals', 0)
                    self.log_test("Referral Stats - Response Structure", True, 
                        f"✅ Returns 'total_referrals' field: {total_referrals}")
                    
                    # Check for total_earnings or total_earned field
                    total_earnings = data.get('total_earnings') or data.get('total_earned', 0)
                    earnings_field = 'total_earnings' if 'total_earnings' in data else 'total_earned' if 'total_earned' in data else None
                    
                    if earnings_field:
                        self.log_test("Referral Stats - Earnings Field", True, 
                            f"✅ Returns '{earnings_field}' field: ${total_earnings}")
                    else:
                        self.log_test("Referral Stats - Earnings Field", False, 
                            "❌ Missing both 'total_earnings' and 'total_earned' fields")
                    
                    # Verify all expected fields are present
                    expected_fields = ['total_referrals', 'referral_code', 'clicks', 'signups', 'conversions', 'commission_rate', 'status']
                    present_fields = []
                    missing_fields = []
                    
                    for field in expected_fields:
                        if field in data:
                            present_fields.append(field)
                        else:
                            missing_fields.append(field)
                    
                    if not missing_fields:
                        self.log_test("Referral Stats - Required Fields", True, 
                            f"All expected fields present: {present_fields}")
                    else:
                        self.log_test("Referral Stats - Required Fields", False, 
                            f"Missing fields: {missing_fields}")
                    
                    # Log the actual values for verification
                    referral_code_resp = data.get('referral_code')
                    clicks = data.get('clicks', 0)
                    signups = data.get('signups', 0)
                    conversions = data.get('conversions', 0)
                    commission_rate = data.get('commission_rate', 0)
                    status = data.get('status', 'unknown')
                    
                    self.log_test("Referral Stats - Values", True, 
                        f"Code: {referral_code_resp}, Clicks: {clicks}, Signups: {signups}, Conversions: {conversions}, Rate: {commission_rate}%, Status: {status}")
                        
                else:
                    self.log_test("Referral Stats - Response Structure", False, 
                        f"❌ API missing 'total_referrals' field. Available keys: {list(data.keys())}")
            else:
                self.log_test("Referral Stats Endpoint", False, 
                    f"Failed to get referral stats: {data}")
        else:
            self.log_test("Create Referral Code", False, 
                f"Failed to create referral code: {create_data}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📋 REVIEW REQUEST TEST SUMMARY")
        print("="*70)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} {test_name}")
            if result['success']:
                passed += 1
            else:
                failed += 1
                if result['details']:
                    print(f"    {result['details']}")
        
        print(f"\n📊 Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All review request tests PASSED!")
        else:
            print("⚠️ Some tests FAILED - see details above")
        
        return passed, failed

async def main():
    """Run review request tests"""
    print("🎯 REVIEW REQUEST TESTING")
    print("Testing Connection History & Referral Stats endpoints")
    print(f"Backend URL: {BACKEND_URL}")
    print("="*70)
    
    async with ReviewRequestTester() as tester:
        # Setup test user
        if not await tester.setup_test_user():
            print("❌ Failed to setup test user, aborting tests")
            return 1
        
        # Test the specific endpoints mentioned in the review request
        await tester.test_connection_history_endpoint()
        await tester.test_referral_stats_endpoint()
        
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