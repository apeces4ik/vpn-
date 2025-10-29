#!/usr/bin/env python3
"""
Enterprise Endpoints Testing Suite
Tests the fixed enterprise endpoints that now accept JSON body instead of query parameters
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://privacyshield-19.preview.emergentagent.com/api"

class EnterpriseEndpointsTester:
    def __init__(self):
        self.session = None
        self.test_results = {}
        self.test_data = {
            'user_id': None,
            'server_id': None,
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
        """Setup test data - create test user and get server"""
        print("\n🔧 Setting up test data...")
        
        # Create test user
        user_data = {"email": "enterprise-test@anonvpn.example"}
        success, data = await self.make_request('POST', '/users', params=user_data)
        
        if success and data.get('id'):
            self.test_data['user_id'] = data['id']
            print(f"    Created test user: {data['id']}")
        else:
            print(f"    Failed to create test user: {data}")
            return False
        
        # Get servers list
        success, data = await self.make_request('GET', '/servers')
        if success and isinstance(data, list) and len(data) > 0:
            self.test_data['server_id'] = data[0]['id']
            print(f"    Using server: {data[0]['id']}")
        else:
            print(f"    Failed to get servers: {data}")
            return False
        
        return True
    
    async def test_dedicated_ip_endpoints(self):
        """Test Dedicated IP Management endpoints"""
        print("\n🌐 Testing Dedicated IP Management...")
        
        if not all([self.test_data['user_id'], self.test_data['server_id']]):
            self.log_test("Dedicated IP Setup", False, "Missing test data")
            return
        
        # Test POST /api/dedicated-ip/assign with JSON body
        assign_data = {
            "user_id": self.test_data['user_id'],
            "server_id": self.test_data['server_id']
        }
        
        success, data = await self.make_request('POST', '/dedicated-ip/assign', 
                                              json=assign_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("Dedicated IP Assign (JSON Body)", True, 
                         f"Successfully assigned dedicated IP: {data}")
        else:
            self.log_test("Dedicated IP Assign (JSON Body)", False, 
                         f"Failed to assign dedicated IP: {data}")
        
        # Test GET /api/dedicated-ip/{user_id}
        success, data = await self.make_request('GET', f'/dedicated-ip/{self.test_data["user_id"]}')
        
        if success:
            self.log_test("Get Dedicated IP", True, 
                         f"Successfully retrieved dedicated IP info: {data}")
        else:
            self.log_test("Get Dedicated IP", False, 
                         f"Failed to get dedicated IP: {data}")
    
    async def test_gdpr_compliance_endpoints(self):
        """Test GDPR Compliance endpoints - CRITICAL TEST"""
        print("\n🔒 Testing GDPR Compliance (CRITICAL)...")
        
        if not self.test_data['user_id']:
            self.log_test("GDPR Setup", False, "Missing user_id")
            return
        
        # Test POST /api/gdpr/data-export with JSON body
        export_data = {
            "user_id": self.test_data['user_id']
        }
        
        success, data = await self.make_request('POST', '/gdpr/data-export',
                                              json=export_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("GDPR Data Export (JSON Body)", True, 
                         f"Successfully created export request: {data}")
        else:
            self.log_test("GDPR Data Export (JSON Body)", False, 
                         f"Failed to create export request: {data}")
        
        # Test POST /api/gdpr/data-deletion with JSON body
        deletion_data = {
            "user_id": self.test_data['user_id'],
            "confirm": True
        }
        
        success, data = await self.make_request('POST', '/gdpr/data-deletion',
                                              json=deletion_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("GDPR Data Deletion (JSON Body)", True, 
                         f"Successfully created deletion request: {data}")
        else:
            self.log_test("GDPR Data Deletion (JSON Body)", False, 
                         f"Failed to create deletion request: {data}")
        
        # Test GET /api/gdpr/requests/{user_id} - CRITICAL: Should NOT return Internal Server Error
        success, data = await self.make_request('GET', f'/gdpr/requests/{self.test_data["user_id"]}')
        
        if success:
            self.log_test("GDPR Get Requests (CRITICAL)", True, 
                         f"✅ NO Internal Server Error - Successfully retrieved GDPR requests: {data}")
        else:
            error_msg = str(data)
            if "Internal Server Error" in error_msg or "500" in error_msg:
                self.log_test("GDPR Get Requests (CRITICAL)", False, 
                             f"❌ CRITICAL: Internal Server Error still present: {data}")
            else:
                self.log_test("GDPR Get Requests (CRITICAL)", False, 
                             f"Failed to get GDPR requests (non-500 error): {data}")
    
    async def test_no_log_audit_system(self):
        """Test No-Log Audit System endpoints"""
        print("\n📋 Testing No-Log Audit System...")
        
        # Test POST /api/audit/log with JSON body
        audit_data = {
            "action": "user_login",
            "result": "success",
            "details": "Test audit entry",
            "auditor": "system"
        }
        
        success, data = await self.make_request('POST', '/audit/log',
                                              json=audit_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("Audit Log Create (JSON Body)", True, 
                         f"Successfully created audit log: {data}")
        else:
            self.log_test("Audit Log Create (JSON Body)", False, 
                         f"Failed to create audit log: {data}")
        
        # Test GET /api/audit/no-log-report
        success, data = await self.make_request('GET', '/audit/no-log-report')
        
        if success:
            self.log_test("No-Log Report", True, 
                         f"Successfully retrieved no-log report: {data}")
        else:
            self.log_test("No-Log Report", False, 
                         f"Failed to get no-log report: {data}")
    
    async def test_security_incidents_endpoints(self):
        """Test Security Incidents Management endpoints"""
        print("\n🚨 Testing Security Incidents Management...")
        
        # Test POST /api/security/incidents with JSON body
        incident_data = {
            "title": "Test Security Incident",
            "description": "Test incident description for enterprise testing",
            "severity": "low",
            "affected_systems": ["web_server", "database"]
        }
        
        success, data = await self.make_request('POST', '/security/incidents',
                                              json=incident_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("Security Incident Create (JSON Body)", True, 
                         f"Successfully created security incident: {data}")
        else:
            self.log_test("Security Incident Create (JSON Body)", False, 
                         f"Failed to create security incident: {data}")
        
        # Test GET /api/security/incidents
        success, data = await self.make_request('GET', '/security/incidents')
        
        if success:
            self.log_test("Get Security Incidents", True, 
                         f"Successfully retrieved security incidents: {data}")
        else:
            self.log_test("Get Security Incidents", False, 
                         f"Failed to get security incidents: {data}")
    
    async def test_alerts_system_endpoints(self):
        """Test Alerts System endpoints"""
        print("\n🚨 Testing Alerts System...")
        
        # Test POST /api/alerts/create with JSON body
        alert_data = {
            "alert_type": "server_down",
            "severity": "high",
            "title": "Test Alert",
            "message": "Test alert message for enterprise testing",
            "source": "monitoring"
        }
        
        success, data = await self.make_request('POST', '/alerts/create',
                                              json=alert_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("Alert Create (JSON Body)", True, 
                         f"Successfully created alert: {data}")
        else:
            self.log_test("Alert Create (JSON Body)", False, 
                         f"Failed to create alert: {data}")
        
        # Test GET /api/alerts/active
        success, data = await self.make_request('GET', '/alerts/active')
        
        if success:
            self.log_test("Get Active Alerts", True, 
                         f"Successfully retrieved active alerts: {data}")
        else:
            self.log_test("Get Active Alerts", False, 
                         f"Failed to get active alerts: {data}")
    
    async def test_dmca_notices_endpoints(self):
        """Test DMCA Notices endpoints"""
        print("\n⚖️ Testing DMCA Notices...")
        
        # Test POST /api/legal/dmca-notice with JSON body
        dmca_data = {
            "complainant_name": "Test Corporation",
            "complainant_email": "legal@testcorp.example",
            "content_description": "Test content description for DMCA notice"
        }
        
        success, data = await self.make_request('POST', '/legal/dmca-notice',
                                              json=dmca_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("DMCA Notice Create (JSON Body)", True, 
                         f"Successfully created DMCA notice: {data}")
        else:
            self.log_test("DMCA Notice Create (JSON Body)", False, 
                         f"Failed to create DMCA notice: {data}")
        
        # Test GET /api/legal/dmca-notices
        success, data = await self.make_request('GET', '/legal/dmca-notices')
        
        if success:
            self.log_test("Get DMCA Notices", True, 
                         f"Successfully retrieved DMCA notices: {data}")
        else:
            self.log_test("Get DMCA Notices", False, 
                         f"Failed to get DMCA notices: {data}")
    
    async def test_security_audits_endpoints(self):
        """Test Security Audits endpoints"""
        print("\n🔍 Testing Security Audits...")
        
        # Test POST /api/security/audits/schedule with JSON body
        audit_data = {
            "audit_type": "penetration_test",
            "scheduled_date": "2025-02-01",
            "auditor": "External Security Auditor"
        }
        
        success, data = await self.make_request('POST', '/security/audits/schedule',
                                              json=audit_data,
                                              headers={'Content-Type': 'application/json'})
        
        if success:
            self.log_test("Security Audit Schedule (JSON Body)", True, 
                         f"Successfully scheduled security audit: {data}")
        else:
            self.log_test("Security Audit Schedule (JSON Body)", False, 
                         f"Failed to schedule security audit: {data}")
        
        # Test GET /api/security/audits
        success, data = await self.make_request('GET', '/security/audits')
        
        if success:
            self.log_test("Get Security Audits", True, 
                         f"Successfully retrieved security audits: {data}")
        else:
            self.log_test("Get Security Audits", False, 
                         f"Failed to get security audits: {data}")
    
    async def test_validation_and_error_handling(self):
        """Test validation and error handling for enterprise endpoints"""
        print("\n🧪 Testing Validation & Error Handling...")
        
        # Test with missing required fields
        incomplete_data = {
            "user_id": self.test_data['user_id']
            # Missing server_id for dedicated IP
        }
        
        success, data = await self.make_request('POST', '/dedicated-ip/assign',
                                              json=incomplete_data,
                                              headers={'Content-Type': 'application/json'})
        
        if not success:
            error_msg = str(data)
            if "required" in error_msg.lower() or "missing" in error_msg.lower() or "server_id" in error_msg.lower():
                self.log_test("Validation - Missing Fields", True, 
                             f"Proper validation error for missing fields: {error_msg}")
            else:
                self.log_test("Validation - Missing Fields", False, 
                             f"Unclear validation error: {error_msg}")
        else:
            self.log_test("Validation - Missing Fields", False, 
                         "Should have failed with missing server_id")
        
        # Test with invalid data types
        invalid_data = {
            "user_id": 12345,  # Should be string
            "server_id": "valid-server-id"
        }
        
        success, data = await self.make_request('POST', '/dedicated-ip/assign',
                                              json=invalid_data,
                                              headers={'Content-Type': 'application/json'})
        
        if not success:
            error_msg = str(data)
            if "validation" in error_msg.lower() or "type" in error_msg.lower():
                self.log_test("Validation - Invalid Types", True, 
                             f"Proper validation error for invalid types: {error_msg}")
            else:
                self.log_test("Validation - Invalid Types", False, 
                             f"Unclear validation error: {error_msg}")
        else:
            self.log_test("Validation - Invalid Types", False, 
                         "Should have failed with invalid data types")
    
    async def run_all_tests(self):
        """Run all enterprise endpoint tests"""
        print("🚀 Starting Enterprise Endpoints Testing Suite")
        print("=" * 60)
        
        # Setup test data
        if not await self.setup_test_data():
            print("❌ Failed to setup test data. Aborting tests.")
            return
        
        # Run all tests
        await self.test_dedicated_ip_endpoints()
        await self.test_gdpr_compliance_endpoints()  # CRITICAL TEST
        await self.test_no_log_audit_system()
        await self.test_security_incidents_endpoints()
        await self.test_alerts_system_endpoints()
        await self.test_dmca_notices_endpoints()
        await self.test_security_audits_endpoints()
        await self.test_validation_and_error_handling()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 ENTERPRISE ENDPOINTS TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"  • {test_name}: {result['details']}")
        
        # Highlight critical GDPR test result
        gdpr_test = self.test_results.get("GDPR Get Requests (CRITICAL)")
        if gdpr_test:
            if gdpr_test['success']:
                print(f"\n🎉 CRITICAL SUCCESS: GDPR GET endpoint is working without Internal Server Error!")
            else:
                print(f"\n🚨 CRITICAL FAILURE: GDPR GET endpoint still has Internal Server Error!")
        
        print("\n" + "=" * 60)

async def main():
    """Main test runner"""
    async with EnterpriseEndpointsTester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())