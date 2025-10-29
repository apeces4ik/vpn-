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
BACKEND_URL = "https://privacyshield-19.preview.emergentagent.com/api"

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
        """Create a test user for the review request tests"""
        print("\n🔧 Setting up test user...")
        
        # Create user with realistic data
        user_data = {"email": "john.doe@example.com"}
        success, data = await self.make_request('POST', '/users', params=user_data)
        
        if success and data.get('id'):
            self.test_data['user_id'] = data['id']
            self.log_test("Setup Test User", True, f"Created user: {data['id']}")
            return True
        else:
            self.log_test("Setup Test User", False, "Failed to create test user", data)
            return False
    
    async def test_referral_code_creation(self):
        """Test 1: Referral Code Creation Fix - POST /api/referrals/create?user_id={test_user_id}"""
        print("\n🤝 Testing Referral Code Creation Fix...")
        
        if not self.test_data['user_id']:
            self.log_test("Referral Code Creation", False, "No test user available")
            return
        
        user_id = self.test_data['user_id']
        
        # Test POST /api/referrals/create?user_id={test_user_id}
        success, data = await self.make_request('POST', f'/referrals/create?user_id={user_id}')
        
        if success:
            # Check if response contains required fields
            has_referral_code = 'referral_code' in data
            has_referral_url = 'referral_url' in data
            
            if has_referral_code and has_referral_url:
                self.test_data['referral_code'] = data['referral_code']
                self.log_test("Referral Code Creation - Success", True, 
                    f"✅ Created referral code: {data['referral_code']}, URL: {data['referral_url']}")
                
                # Test creating again - should return existing code
                success2, data2 = await self.make_request('POST', f'/referrals/create?user_id={user_id}')
                
                if success2 and data2.get('referral_code') == data['referral_code']:
                    self.log_test("Referral Code Creation - Existing Code", True, 
                        f"✅ Returns existing code when called again: {data2['referral_code']}")
                else:
                    self.log_test("Referral Code Creation - Existing Code", False, 
                        f"Should return existing code, got: {data2}")
            else:
                self.log_test("Referral Code Creation - Response Format", False, 
                    f"Missing required fields. Has referral_code: {has_referral_code}, Has referral_url: {has_referral_url}")
        else:
            self.log_test("Referral Code Creation", False, 
                f"Failed to create referral code: {data}")
    
    async def test_support_ticket_with_telegram(self):
        """Test 2: Support Ticket with Telegram Username"""
        print("\n🎫 Testing Support Ticket with Telegram Username...")
        
        if not self.test_data['user_id']:
            self.log_test("Support Ticket Creation", False, "No test user available")
            return
        
        user_id = self.test_data['user_id']
        
        # Test POST /api/support/tickets with telegram_username
        ticket_payload = {
            "user_id": user_id,
            "telegram_username": "test_username",
            "subject": "Support Request",
            "description": "Test ticket",
            "priority": "medium",
            "category": "general"
        }
        
        success, data = await self.make_request('POST', '/support/tickets', json=ticket_payload)
        
        if success:
            # Check if ticket was created successfully
            has_ticket_id = 'ticket_id' in data
            has_message = 'message' in data
            
            if has_ticket_id and has_message:
                self.test_data['ticket_id'] = data['ticket_id']
                self.log_test("Support Ticket Creation - Success", True, 
                    f"✅ Created ticket: {data['ticket_id']}, Message: {data['message']}")
                
            else:
                self.log_test("Support Ticket Creation - Response Format", False, 
                    f"Missing required fields. Has ticket_id: {has_ticket_id}, Has message: {has_message}")
        else:
            self.log_test("Support Ticket Creation", False, 
                f"Failed to create support ticket: {data}")
    
    async def test_get_support_tickets(self):
        """Test 3: Get Support Tickets - should include telegram_username field"""
        print("\n📋 Testing Get Support Tickets...")
        
        if not self.test_data['user_id']:
            self.log_test("Get Support Tickets", False, "No test user available")
            return
        
        user_id = self.test_data['user_id']
        
        # Test GET /api/support/tickets/{user_id}
        success, data = await self.make_request('GET', f'/support/tickets/{user_id}')
        
        if success:
            # Check if response has tickets array
            has_tickets = 'tickets' in data
            has_total = 'total' in data
            
            if has_tickets and has_total:
                tickets = data['tickets']
                total = data['total']
                
                self.log_test("Get Support Tickets - Response Structure", True, 
                    f"✅ Returns tickets array with {len(tickets)} tickets, total: {total}")
                
                # Check if tickets include telegram_username field
                if tickets and len(tickets) > 0:
                    first_ticket = tickets[0]
                    has_telegram_username = 'telegram_username' in first_ticket
                    
                    if has_telegram_username:
                        telegram_username = first_ticket['telegram_username']
                        self.log_test("Get Support Tickets - Telegram Username Field", True, 
                            f"✅ Ticket includes telegram_username: {telegram_username}")
                        
                        # Verify it's the correct username we set
                        if telegram_username == "test_username":
                            self.log_test("Get Support Tickets - Correct Telegram Username", True, 
                                f"✅ Telegram username matches expected value: {telegram_username}")
                        else:
                            self.log_test("Get Support Tickets - Correct Telegram Username", False, 
                                f"Expected 'test_username', got: {telegram_username}")
                    else:
                        self.log_test("Get Support Tickets - Telegram Username Field", False, 
                            f"❌ Ticket missing telegram_username field. Available fields: {list(first_ticket.keys())}")
                        
                    # Check other required fields
                    required_fields = ['id', 'user_id', 'subject', 'description', 'priority', 'status', 'category', 'created_at']
                    missing_fields = [field for field in required_fields if field not in first_ticket]
                    
                    if not missing_fields:
                        self.log_test("Get Support Tickets - Required Fields", True, 
                            f"✅ All required fields present: {required_fields}")
                    else:
                        self.log_test("Get Support Tickets - Required Fields", False, 
                            f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Get Support Tickets - No Tickets", True, 
                        "No tickets found (expected if no tickets were created)")
            else:
                self.log_test("Get Support Tickets - Response Structure", False, 
                    f"Missing required fields. Has tickets: {has_tickets}, Has total: {has_total}")
        else:
            self.log_test("Get Support Tickets", False, 
                f"Failed to get support tickets: {data}")
    
    async def run_all_tests(self):
        """Run all review request tests"""
        print("🚀 Starting Review Request Testing...")
        print("=" * 60)
        
        # Setup
        if not await self.setup_test_user():
            print("❌ Cannot proceed without test user")
            return
        
        # Run the specific tests mentioned in the review request
        await self.test_referral_code_creation()
        await self.test_support_ticket_with_telegram()
        await self.test_get_support_tickets()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 REVIEW REQUEST TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {test_name}")
            if result['details']:
                print(f"    {result['details']}")
        
        print("\n" + "=" * 60)
        
        # Return summary for main agent
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'results': self.test_results
        }

async def main():
    """Main test execution"""
    async with ReviewRequestTester() as tester:
        return await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())