#!/usr/bin/env python3
"""
Phase 18 Backend API Tests - Neo as GetZzy AI Operating System
Tests role hierarchy, role-gated capabilities, workspace endpoints, and admin/founder features
"""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class Phase18Tester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.customer_token = None
        self.founder_token = None
        self.visitor_token = None
        self.failed_tests = []
        self.project_id = None

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None, token=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        h = {'Content-Type': 'application/json'}
        if token:
            h['Authorization'] = f'Bearer {token}'
        if headers:
            h.update(headers)

        self.tests_run += 1
        self.log(f"\n🔍 Test {self.tests_run}: {name}", Colors.BLUE)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=h, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=h, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=h, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=h, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=h, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}", Colors.GREEN)
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", Colors.RED)
                try:
                    self.log(f"Response: {json.dumps(response.json(), indent=2)}", Colors.YELLOW)
                except:
                    self.log(f"Response: {response.text[:500]}", Colors.YELLOW)
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"❌ FAIL - Error: {str(e)}", Colors.RED)
            return False, {}

    def run_all_tests(self):
        self.log("=" * 80, Colors.BLUE)
        self.log("PHASE 18 BACKEND TESTS - NEO AS GETSZY AI OPERATING SYSTEM", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # ===== 1. AUTHENTICATION & ROLE SETUP =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("1. AUTHENTICATION & ROLE SETUP", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Admin login
        success, data = self.test(
            "Admin login",
            "POST",
            "/auth/login",
            200,
            data={"email": "admin@getszy.com", "password": "Admin@123"}
        )
        if success and 'token' in data:
            self.admin_token = data['token']
            self.log(f"✅ Admin token obtained, role: {data.get('user', {}).get('role')}", Colors.GREEN)

        # Customer login
        success, data = self.test(
            "Customer login",
            "POST",
            "/auth/login",
            200,
            data={"email": "customer@getszy.com", "password": "Demo@123"}
        )
        if success and 'token' in data:
            self.customer_token = data['token']
            self.log(f"✅ Customer token obtained, role: {data.get('user', {}).get('role')}", Colors.GREEN)

        # ===== 2. ROLE HIERARCHY TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("2. ROLE HIERARCHY TESTS (visitor < customer < founder < admin)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Test capabilities endpoint for admin (should see 19 capabilities)
        success, data = self.test(
            "GET /api/chat/capabilities (admin) - should see 19 caps",
            "GET",
            "/chat/capabilities",
            200,
            token=self.admin_token
        )
        if success:
            caps = data.get('capabilities', [])
            count = len(caps)
            role = data.get('user_role')
            self.log(f"  Admin sees {count} capabilities, role: {role}", Colors.BLUE)
            
            # Check for admin capabilities
            admin_caps = [c for c in caps if c['id'].startswith('admin_')]
            labs_caps = [c for c in caps if c['id'].startswith('labs_')]
            
            if count == 19:
                self.log(f"✅ Admin sees exactly 19 capabilities", Colors.GREEN)
            else:
                self.log(f"⚠️  Expected 19 capabilities, got {count}", Colors.YELLOW)
            
            if len(admin_caps) == 5:
                self.log(f"✅ Admin sees 5 admin_* capabilities: {[c['id'] for c in admin_caps]}", Colors.GREEN)
            else:
                self.log(f"⚠️  Expected 5 admin_* capabilities, got {len(admin_caps)}", Colors.YELLOW)
            
            if len(labs_caps) == 1:
                self.log(f"✅ Admin sees 1 labs_* capability: {[c['id'] for c in labs_caps]}", Colors.GREEN)
            else:
                self.log(f"⚠️  Expected 1 labs_* capability, got {len(labs_caps)}", Colors.YELLOW)

        # Test capabilities endpoint for customer (should see 13 capabilities, no admin_* or labs_*)
        success, data = self.test(
            "GET /api/chat/capabilities (customer) - should see 13 caps",
            "GET",
            "/chat/capabilities",
            200,
            token=self.customer_token
        )
        if success:
            caps = data.get('capabilities', [])
            count = len(caps)
            role = data.get('user_role')
            self.log(f"  Customer sees {count} capabilities, role: {role}", Colors.BLUE)
            
            # Check that no admin or labs capabilities are visible
            admin_caps = [c for c in caps if c['id'].startswith('admin_')]
            labs_caps = [c for c in caps if c['id'].startswith('labs_')]
            
            if count == 13:
                self.log(f"✅ Customer sees exactly 13 capabilities", Colors.GREEN)
            else:
                self.log(f"⚠️  Expected 13 capabilities, got {count}", Colors.YELLOW)
            
            if len(admin_caps) == 0:
                self.log(f"✅ Customer sees NO admin_* capabilities", Colors.GREEN)
            else:
                self.log(f"❌ Customer should NOT see admin_* capabilities: {[c['id'] for c in admin_caps]}", Colors.RED)
            
            if len(labs_caps) == 0:
                self.log(f"✅ Customer sees NO labs_* capabilities", Colors.GREEN)
            else:
                self.log(f"❌ Customer should NOT see labs_* capabilities: {[c['id'] for c in labs_caps]}", Colors.RED)

        # ===== 3. ADMIN CAPABILITIES TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("3. ADMIN CAPABILITIES TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            # Create a chat session for admin
            success, data = self.test(
                "Create admin chat session",
                "POST",
                "/chat/session",
                200,
                data={"title": "Admin Test Session"},
                token=self.admin_token
            )
            admin_session_id = None
            if success:
                admin_session_id = data.get('id')
                self.log(f"✅ Admin session created: {admin_session_id}", Colors.GREEN)

            if admin_session_id:
                # Test admin_analytics capability
                self.log(f"\n⏳ Testing admin_analytics capability (may take 5-10 seconds)...", Colors.YELLOW)
                success, data = self.test(
                    "Admin asks for platform analytics",
                    "POST",
                    f"/chat/session/{admin_session_id}/message",
                    200,
                    data={"content": "Show platform analytics"},
                    token=self.admin_token
                )
                if success:
                    self.log(f"✅ Admin analytics request accepted", Colors.GREEN)
                    
                    # Poll for events to see if admin_analytics was invoked
                    import time
                    time.sleep(3)
                    success2, events_data = self.test(
                        "Get admin session events",
                        "GET",
                        f"/chat/session/{admin_session_id}/events",
                        200,
                        token=self.admin_token
                    )
                    if success2:
                        events = events_data.get('events', [])
                        intent_events = [e for e in events if e.get('kind') == 'intent']
                        asset_events = [e for e in events if e.get('kind') == 'asset']
                        
                        if intent_events:
                            intent = intent_events[-1].get('payload', {}).get('intent')
                            self.log(f"  Intent detected: {intent}", Colors.BLUE)
                            if intent == 'admin_analytics':
                                self.log(f"✅ admin_analytics capability invoked", Colors.GREEN)
                            else:
                                self.log(f"⚠️  Expected admin_analytics, got {intent}", Colors.YELLOW)
                        
                        if asset_events:
                            asset = asset_events[-1].get('payload', {})
                            if asset.get('kind') == 'admin_analytics':
                                asset_data = asset.get('data', {})
                                self.log(f"✅ admin_analytics returned data:", Colors.GREEN)
                                self.log(f"  Users: {asset_data.get('users')}", Colors.BLUE)
                                self.log(f"  Revenue: ₹{asset_data.get('revenue')}", Colors.BLUE)
                                self.log(f"  Orders: {asset_data.get('orders')}", Colors.BLUE)

                # Test admin_list_users capability
                self.log(f"\n⏳ Testing admin_list_users capability (may take 5-10 seconds)...", Colors.YELLOW)
                success, data = self.test(
                    "Admin asks to list founders",
                    "POST",
                    f"/chat/session/{admin_session_id}/message",
                    200,
                    data={"content": "list founders"},
                    token=self.admin_token
                )
                if success:
                    time.sleep(3)
                    success2, events_data = self.test(
                        "Get admin session events (list_users)",
                        "GET",
                        f"/chat/session/{admin_session_id}/events?since={datetime.now().isoformat()}",
                        200,
                        token=self.admin_token
                    )
                    if success2:
                        events = events_data.get('events', [])
                        intent_events = [e for e in events if e.get('kind') == 'intent']
                        if intent_events:
                            intent = intent_events[-1].get('payload', {}).get('intent')
                            if intent == 'admin_list_users':
                                self.log(f"✅ admin_list_users capability invoked", Colors.GREEN)

        # ===== 4. SERVER-SIDE AUTHORIZATION TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("4. SERVER-SIDE AUTHORIZATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.customer_token:
            # Create a chat session for customer
            success, data = self.test(
                "Create customer chat session",
                "POST",
                "/chat/session",
                200,
                data={"title": "Customer Test Session"},
                token=self.customer_token
            )
            customer_session_id = None
            if success:
                customer_session_id = data.get('id')
                self.log(f"✅ Customer session created: {customer_session_id}", Colors.GREEN)

            if customer_session_id:
                # Customer tries to ask for platform analytics (should route to general_chat)
                self.log(f"\n⏳ Testing server-side authorization (customer asks for analytics)...", Colors.YELLOW)
                success, data = self.test(
                    "Customer asks for platform analytics (should be blocked)",
                    "POST",
                    f"/chat/session/{customer_session_id}/message",
                    200,
                    data={"content": "Show platform analytics"},
                    token=self.customer_token
                )
                if success:
                    import time
                    time.sleep(3)
                    success2, events_data = self.test(
                        "Get customer session events",
                        "GET",
                        f"/chat/session/{customer_session_id}/events",
                        200,
                        token=self.customer_token
                    )
                    if success2:
                        events = events_data.get('events', [])
                        intent_events = [e for e in events if e.get('kind') == 'intent']
                        
                        if intent_events:
                            intent = intent_events[-1].get('payload', {}).get('intent')
                            reply = intent_events[-1].get('payload', {}).get('reply', '')
                            self.log(f"  Intent: {intent}", Colors.BLUE)
                            self.log(f"  Reply: {reply}", Colors.BLUE)
                            
                            if intent == 'general_chat' or 'role chahiye' in reply.lower():
                                self.log(f"✅ Server-side authorization working: customer blocked from admin capability", Colors.GREEN)
                            elif intent == 'admin_analytics':
                                self.log(f"❌ CRITICAL: Customer was able to invoke admin_analytics!", Colors.RED)
                            else:
                                self.log(f"⚠️  Unexpected intent: {intent}", Colors.YELLOW)

        # ===== 5. WORKSPACE ENDPOINTS TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("5. WORKSPACE ENDPOINTS TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Test workspace endpoints require auth (401 without token)
        success, data = self.test(
            "GET /api/workspace/{id} without auth (should fail 401)",
            "GET",
            "/workspace/test-id",
            401
        )
        if success:
            self.log(f"✅ Workspace endpoint requires auth", Colors.GREEN)

        if self.customer_token:
            # Create a chat project for workspace testing
            success, data = self.test(
                "Create chat project for workspace",
                "POST",
                "/chat/session",
                200,
                data={"title": "Workspace Test Project"},
                token=self.customer_token
            )
            if success:
                self.project_id = data.get('id')
                self.log(f"✅ Project created for workspace: {self.project_id}", Colors.GREEN)

            if self.project_id:
                # Test GET /api/workspace/{project_id}
                success, data = self.test(
                    "GET /api/workspace/{project_id}",
                    "GET",
                    f"/workspace/{self.project_id}",
                    200,
                    token=self.customer_token
                )
                if success:
                    required_keys = ['project', 'messages', 'assets', 'plan', 'tasks', 'versions', 'deployments']
                    missing_keys = [k for k in required_keys if k not in data]
                    if not missing_keys:
                        self.log(f"✅ Workspace endpoint returns all required keys", Colors.GREEN)
                    else:
                        self.log(f"❌ Missing keys in workspace response: {missing_keys}", Colors.RED)

                # Test PUT /api/workspace/{id}/plan
                success, data = self.test(
                    "PUT /api/workspace/{id}/plan",
                    "PUT",
                    f"/workspace/{self.project_id}/plan",
                    200,
                    data={"summary": "Test plan summary", "steps": ["Step 1", "Step 2", "Step 3"]},
                    token=self.customer_token
                )
                if success:
                    self.log(f"✅ Plan set successfully", Colors.GREEN)

                # Test POST /api/workspace/{id}/task
                success, data = self.test(
                    "POST /api/workspace/{id}/task",
                    "POST",
                    f"/workspace/{self.project_id}/task",
                    200,
                    data={"title": "Test task", "description": "Test description", "status": "todo", "priority": "high"},
                    token=self.customer_token
                )
                task_id = None
                if success:
                    task_id = data.get('id')
                    self.log(f"✅ Task created: {task_id}", Colors.GREEN)

                # Test PATCH /api/workspace/{id}/task/{task_id}
                if task_id:
                    success, data = self.test(
                        "PATCH /api/workspace/{id}/task/{task_id}",
                        "PATCH",
                        f"/workspace/{self.project_id}/task/{task_id}",
                        200,
                        data={"status": "done"},
                        token=self.customer_token
                    )
                    if success:
                        if data.get('status') == 'done':
                            self.log(f"✅ Task updated successfully", Colors.GREEN)

                    # Test DELETE /api/workspace/{id}/task/{task_id}
                    success, data = self.test(
                        "DELETE /api/workspace/{id}/task/{task_id}",
                        "DELETE",
                        f"/workspace/{self.project_id}/task/{task_id}",
                        200,
                        token=self.customer_token
                    )
                    if success:
                        if data.get('deleted', 0) == 1:
                            self.log(f"✅ Task deleted successfully", Colors.GREEN)

                # Test POST /api/workspace/{id}/version
                success, data = self.test(
                    "POST /api/workspace/{id}/version",
                    "POST",
                    f"/workspace/{self.project_id}/version",
                    200,
                    data={"label": "v1.0"},
                    token=self.customer_token
                )
                if success:
                    version_id = data.get('id')
                    if version_id and 'message_count' in data and 'asset_count' in data:
                        self.log(f"✅ Version snapshot created: {version_id}", Colors.GREEN)
                        self.log(f"  Messages: {data.get('message_count')}, Assets: {data.get('asset_count')}", Colors.BLUE)

                # Test GET /api/workspace/{id}/timeline
                success, data = self.test(
                    "GET /api/workspace/{id}/timeline",
                    "GET",
                    f"/workspace/{self.project_id}/timeline",
                    200,
                    token=self.customer_token
                )
                if success:
                    items = data.get('items', [])
                    self.log(f"✅ Timeline retrieved: {len(items)} items", Colors.GREEN)
                    # Check that items have 'type' and 'at' fields
                    if items:
                        item_types = set(item.get('type') for item in items)
                        self.log(f"  Item types: {item_types}", Colors.BLUE)

                # Test POST /api/workspace/{id}/deployment
                success, data = self.test(
                    "POST /api/workspace/{id}/deployment",
                    "POST",
                    f"/workspace/{self.project_id}/deployment",
                    200,
                    data={"kind": "webapp", "target": "test.getszy.com", "url": "https://test.getszy.com", "meta": {"version": "1.0"}},
                    token=self.customer_token
                )
                if success:
                    deployment_id = data.get('id')
                    if deployment_id:
                        self.log(f"✅ Deployment recorded: {deployment_id}", Colors.GREEN)

        # ===== 6. EXISTING ENDPOINTS STILL WORK =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("6. EXISTING ENDPOINTS STILL WORK", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Test /api/products
        success, data = self.test(
            "GET /api/products",
            "GET",
            "/products",
            200
        )
        if success:
            products = data if isinstance(data, list) else data.get('products', [])
            self.log(f"✅ Products endpoint working: {len(products)} products", Colors.GREEN)

        # Test /api/video/voices (requires auth)
        if self.customer_token:
            success, data = self.test(
                "GET /api/video/voices",
                "GET",
                "/video/voices",
                200,
                token=self.customer_token
            )
            if success:
                voices = data.get('voices', [])
                self.log(f"✅ Video voices endpoint working: {len(voices)} voices", Colors.GREEN)

        # Test /api/workforce/agents (requires auth)
        if self.customer_token:
            success, data = self.test(
                "GET /api/workforce/agents",
                "GET",
                "/workforce/agents",
                200,
                token=self.customer_token
            )
            if success:
                agents = data.get('agents', [])
                self.log(f"✅ Workforce agents endpoint working: {len(agents)} agents", Colors.GREEN)

        # Test /api/chat/sessions
        if self.customer_token:
            success, data = self.test(
                "GET /api/chat/sessions",
                "GET",
                "/chat/sessions",
                200,
                token=self.customer_token
            )
            if success:
                items = data.get('items', [])
                self.log(f"✅ Chat sessions endpoint working: {len(items)} sessions", Colors.GREEN)

        # Test /api/builder/hub (requires auth)
        if self.customer_token:
            success, data = self.test(
                "GET /api/builder/hub",
                "GET",
                "/builder/hub",
                200,
                token=self.customer_token
            )
            if success:
                self.log(f"✅ Builder hub endpoint working", Colors.GREEN)

        # ===== SUMMARY =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        self.log(f"Total tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED if self.tests_failed > 0 else Colors.GREEN)
        
        if self.failed_tests:
            self.log(f"\nFailed tests:", Colors.RED)
            for test in self.failed_tests:
                self.log(f"  - {test}", Colors.RED)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess rate: {success_rate:.1f}%", Colors.GREEN if success_rate >= 90 else Colors.YELLOW)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = Phase18Tester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
