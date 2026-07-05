"""Backend API tests for Universal AI Chat Builder (Phase 15)."""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"

class ChatBuilderTester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=40):
        """Run a single API test."""
        url = f"{BASE_URL}{endpoint}"
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        if headers:
            h.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testing: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=h, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=h, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=h, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=h, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - {name} (Status: {response.status_code})")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ FAIL - {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:300]}")
                except:
                    pass
                self.failed_tests.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            self.log(f"❌ FAIL - {name} - Error: {str(e)}")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {}

    def login(self, email, password):
        """Login and get token."""
        self.log(f"\n🔐 Logging in as {email}...")
        success, response = self.test(
            "Login",
            "POST",
            "/auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"✅ Login successful, token obtained")
            return True
        self.log(f"❌ Login failed")
        return False

    def test_capabilities(self):
        """Test GET /api/chat/capabilities."""
        self.log("\n" + "="*60)
        self.log("🎯 TESTING CAPABILITIES ENDPOINT")
        self.log("="*60)

        success, response = self.test(
            "GET /api/chat/capabilities - returns 13 capabilities",
            "GET",
            "/chat/capabilities",
            200
        )
        
        if success:
            caps = response.get('capabilities', [])
            count = response.get('count', 0)
            self.log(f"   ✓ Found {count} capabilities")
            
            expected_caps = [
                'write_script', 'score_hook', 'viral_score', 'predict_trends',
                'competitor_gap', 'generate_video', 'plan_channel', 'build_webapp',
                'starter_mobileapp', 'starter_fullstack', 'starter_blog',
                'run_workforce', 'sourcing_scan'
            ]
            
            cap_ids = [c.get('id') for c in caps]
            for exp in expected_caps:
                if exp in cap_ids:
                    self.log(f"   ✓ {exp} present")
                else:
                    self.log(f"   ❌ {exp} MISSING")
                    self.failed_tests.append(f"Missing capability: {exp}")
            
            if count != 13:
                self.log(f"   ⚠ Expected 13 capabilities, got {count}")

    def test_session_crud(self):
        """Test session CRUD operations."""
        self.log("\n" + "="*60)
        self.log("📝 TESTING SESSION CRUD")
        self.log("="*60)

        # Test 1: Create session without first_message
        success, response = self.test(
            "POST /api/chat/session - creates empty session",
            "POST",
            "/chat/session",
            200,
            data={"title": "Test Session"}
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created with ID: {session_id}")
            self.log(f"   ✓ Title: {response.get('title')}")
            self.log(f"   ✓ Status: {response.get('status')}")
        
        # Test 2: List sessions
        success, response = self.test(
            "GET /api/chat/sessions - lists user sessions",
            "GET",
            "/chat/sessions?limit=50",
            200
        )
        
        if success and 'items' in response:
            self.log(f"   ✓ Found {len(response['items'])} sessions")
        
        # Test 3: Get session detail
        if session_id:
            success, response = self.test(
                f"GET /api/chat/session/{session_id} - returns session detail",
                "GET",
                f"/chat/session/{session_id}",
                200
            )
            
            if success:
                self.log(f"   ✓ Project: {response.get('project', {}).get('title')}")
                self.log(f"   ✓ Messages: {len(response.get('messages', []))}")
                self.log(f"   ✓ Assets: {len(response.get('assets', []))}")
        
        # Test 4: Rename session
        if session_id:
            success, response = self.test(
                f"PATCH /api/chat/session/{session_id} - renames session",
                "PATCH",
                f"/chat/session/{session_id}",
                200,
                data={"title": "Renamed Test Session"}
            )
        
        # Test 5: Delete session
        if session_id:
            success, response = self.test(
                f"DELETE /api/chat/session/{session_id} - removes session",
                "DELETE",
                f"/chat/session/{session_id}",
                200
            )

    def test_messaging_and_polling(self):
        """Test message sending and event polling."""
        self.log("\n" + "="*60)
        self.log("💬 TESTING MESSAGING & POLLING")
        self.log("="*60)

        # Create session with first_message
        success, response = self.test(
            "POST /api/chat/session with first_message - triggers orchestrator",
            "POST",
            "/chat/session",
            200,
            data={
                "title": "Polling Test",
                "first_message": "hello, what can you do?"
            },
            timeout=5
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created with ID: {session_id}")
            
            # Wait a bit for background processing
            time.sleep(2)
            
            # Poll for events
            success, response = self.test(
                f"GET /api/chat/session/{session_id}/events - polls for new events",
                "GET",
                f"/chat/session/{session_id}/events?since=",
                200,
                timeout=10
            )
            
            if success:
                events = response.get('events', [])
                messages = response.get('messages', [])
                assets = response.get('assets', [])
                self.log(f"   ✓ Events: {len(events)}")
                self.log(f"   ✓ Messages: {len(messages)}")
                self.log(f"   ✓ Assets: {len(assets)}")
                self.log(f"   ✓ Server time: {response.get('server_time')}")
                
                # Check for user message
                user_msgs = [m for m in messages if m.get('role') == 'user']
                if user_msgs:
                    self.log(f"   ✓ User message found: {user_msgs[0].get('content')[:50]}")
            
            # Send another message
            success, response = self.test(
                f"POST /api/chat/session/{session_id}/message - sends message",
                "POST",
                f"/chat/session/{session_id}/message",
                200,
                data={"content": "Tell me more about your capabilities"},
                timeout=5
            )
            
            if success:
                self.log(f"   ✓ Message accepted: {response.get('accepted')}")
            
            # Clean up
            self.test(
                f"DELETE /api/chat/session/{session_id}",
                "DELETE",
                f"/chat/session/{session_id}",
                200
            )

    def test_e2e_write_script(self):
        """End-to-end test: Write a Hinglish reel script."""
        self.log("\n" + "="*60)
        self.log("🎬 E2E TEST: Write Script")
        self.log("="*60)

        success, response = self.test(
            "Create session with script request",
            "POST",
            "/chat/session",
            200,
            data={
                "first_message": "Write a Hinglish reel script: 5 AI tools for Indian students"
            },
            timeout=5
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created: {session_id}")
            
            # Wait for LLM processing (25-35s as per requirements)
            self.log(f"   ⏳ Waiting for script generation (max 35s)...")
            max_wait = 35
            start_time = time.time()
            script_found = False
            
            while time.time() - start_time < max_wait:
                time.sleep(3)
                success, response = self.test(
                    f"Poll for script asset",
                    "GET",
                    f"/chat/session/{session_id}/events?since=",
                    200,
                    timeout=10
                )
                
                if success:
                    assets = response.get('assets', [])
                    events = response.get('events', [])
                    
                    # Check for script asset
                    script_assets = [a for a in assets if a.get('kind') == 'script']
                    if script_assets:
                        script = script_assets[0]
                        self.log(f"   ✅ Script asset created!")
                        self.log(f"   ✓ Title: {script.get('title')}")
                        self.log(f"   ✓ Kind: {script.get('kind')}")
                        data = script.get('data', {})
                        if data.get('hook'):
                            self.log(f"   ✓ Hook: {data['hook'][:60]}...")
                        if data.get('body'):
                            self.log(f"   ✓ Body length: {len(data['body'])} chars")
                        if data.get('cta'):
                            self.log(f"   ✓ CTA: {data['cta'][:60]}...")
                        if data.get('hashtags'):
                            self.log(f"   ✓ Hashtags: {data['hashtags']}")
                        script_found = True
                        break
                    
                    # Check for done event
                    done_events = [e for e in events if e.get('kind') == 'done']
                    if done_events and not script_assets:
                        self.log(f"   ⚠ Done event found but no script asset")
                        break
            
            if not script_found:
                self.log(f"   ❌ Script not generated within {max_wait}s")
                self.failed_tests.append("E2E write_script: Script not generated in time")
            
            # Clean up
            if session_id:
                self.test(
                    f"DELETE session {session_id}",
                    "DELETE",
                    f"/chat/session/{session_id}",
                    200
                )

    def test_e2e_build_webapp(self):
        """End-to-end test: Build a landing page."""
        self.log("\n" + "="*60)
        self.log("🌐 E2E TEST: Build Web App")
        self.log("="*60)

        success, response = self.test(
            "Create session with webapp request",
            "POST",
            "/chat/session",
            200,
            data={
                "first_message": "Build a landing page for a Kathak academy in Jaipur"
            },
            timeout=5
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created: {session_id}")
            
            # Wait for LLM processing
            self.log(f"   ⏳ Waiting for webapp generation (max 35s)...")
            max_wait = 35
            start_time = time.time()
            webapp_found = False
            
            while time.time() - start_time < max_wait:
                time.sleep(3)
                success, response = self.test(
                    f"Poll for webapp asset",
                    "GET",
                    f"/chat/session/{session_id}/events?since=",
                    200,
                    timeout=10
                )
                
                if success:
                    assets = response.get('assets', [])
                    
                    # Check for webapp asset
                    webapp_assets = [a for a in assets if a.get('kind') == 'webapp']
                    if webapp_assets:
                        webapp = webapp_assets[0]
                        self.log(f"   ✅ Webapp asset created!")
                        self.log(f"   ✓ Title: {webapp.get('title')}")
                        self.log(f"   ✓ Kind: {webapp.get('kind')}")
                        data = webapp.get('data', {})
                        if data.get('preview_url'):
                            self.log(f"   ✓ Preview URL: {data['preview_url']}")
                        if data.get('project_id'):
                            self.log(f"   ✓ Project ID: {data['project_id']}")
                        if data.get('size_bytes'):
                            self.log(f"   ✓ Size: {data['size_bytes'] // 1024} KB")
                        webapp_found = True
                        break
            
            if not webapp_found:
                self.log(f"   ❌ Webapp not generated within {max_wait}s")
                self.failed_tests.append("E2E build_webapp: Webapp not generated in time")
            
            # Clean up
            if session_id:
                self.test(
                    f"DELETE session {session_id}",
                    "DELETE",
                    f"/chat/session/{session_id}",
                    200
                )

    def test_e2e_predict_trends(self):
        """End-to-end test: Predict trending topics."""
        self.log("\n" + "="*60)
        self.log("📈 E2E TEST: Predict Trends")
        self.log("="*60)

        success, response = self.test(
            "Create session with trends request",
            "POST",
            "/chat/session",
            200,
            data={
                "first_message": "Predict trending topics for personal finance for Indian audience"
            },
            timeout=5
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created: {session_id}")
            
            # Wait for LLM processing
            self.log(f"   ⏳ Waiting for trends prediction (max 35s)...")
            max_wait = 35
            start_time = time.time()
            trends_found = False
            
            while time.time() - start_time < max_wait:
                time.sleep(3)
                success, response = self.test(
                    f"Poll for trends asset",
                    "GET",
                    f"/chat/session/{session_id}/events?since=",
                    200,
                    timeout=10
                )
                
                if success:
                    assets = response.get('assets', [])
                    
                    # Check for trends asset
                    trends_assets = [a for a in assets if a.get('kind') == 'trends']
                    if trends_assets:
                        trends = trends_assets[0]
                        self.log(f"   ✅ Trends asset created!")
                        self.log(f"   ✓ Title: {trends.get('title')}")
                        self.log(f"   ✓ Kind: {trends.get('kind')}")
                        data = trends.get('data', {})
                        predictions = data.get('predictions', [])
                        if predictions:
                            self.log(f"   ✓ Predictions count: {len(predictions)}")
                            for i, pred in enumerate(predictions[:3]):
                                self.log(f"   ✓ Trend {i+1}: {pred.get('topic', 'N/A')}")
                        trends_found = True
                        break
            
            if not trends_found:
                self.log(f"   ❌ Trends not generated within {max_wait}s")
                self.failed_tests.append("E2E predict_trends: Trends not generated in time")
            
            # Clean up
            if session_id:
                self.test(
                    f"DELETE session {session_id}",
                    "DELETE",
                    f"/chat/session/{session_id}",
                    200
                )

    def test_e2e_general_chat(self):
        """End-to-end test: General chat (no capability dispatch)."""
        self.log("\n" + "="*60)
        self.log("💭 E2E TEST: General Chat")
        self.log("="*60)

        success, response = self.test(
            "Create session with general chat",
            "POST",
            "/chat/session",
            200,
            data={
                "first_message": "hello, what can you do?"
            },
            timeout=5
        )
        
        session_id = None
        if success and 'id' in response:
            session_id = response['id']
            self.log(f"   ✓ Session created: {session_id}")
            
            # Wait for response
            self.log(f"   ⏳ Waiting for general chat response (max 15s)...")
            max_wait = 15
            start_time = time.time()
            reply_found = False
            
            while time.time() - start_time < max_wait:
                time.sleep(2)
                success, response = self.test(
                    f"Poll for assistant reply",
                    "GET",
                    f"/chat/session/{session_id}/events?since=",
                    200,
                    timeout=10
                )
                
                if success:
                    messages = response.get('messages', [])
                    events = response.get('events', [])
                    
                    # Check for assistant message
                    assistant_msgs = [m for m in messages if m.get('role') == 'assistant']
                    if assistant_msgs:
                        self.log(f"   ✅ Assistant reply received!")
                        self.log(f"   ✓ Content: {assistant_msgs[0].get('content')[:100]}...")
                        
                        # Check intent
                        intent_events = [e for e in events if e.get('kind') == 'intent']
                        if intent_events:
                            intent = intent_events[0].get('payload', {}).get('intent')
                            self.log(f"   ✓ Intent: {intent}")
                            if intent == 'general_chat':
                                self.log(f"   ✓ Correctly classified as general_chat")
                            else:
                                self.log(f"   ⚠ Expected general_chat, got {intent}")
                        
                        reply_found = True
                        break
            
            if not reply_found:
                self.log(f"   ❌ No reply within {max_wait}s")
                self.failed_tests.append("E2E general_chat: No reply received")
            
            # Clean up
            if session_id:
                self.test(
                    f"DELETE session {session_id}",
                    "DELETE",
                    f"/chat/session/{session_id}",
                    200
                )

    def test_auth_required(self):
        """Test that all chat endpoints require auth."""
        self.log("\n" + "="*60)
        self.log("🔒 TESTING AUTH REQUIREMENTS")
        self.log("="*60)

        # Temporarily remove token
        original_token = self.token
        self.token = None

        endpoints = [
            ("GET", "/chat/capabilities"),
            ("POST", "/chat/session"),
            ("GET", "/chat/sessions"),
        ]

        for method, endpoint in endpoints:
            self.test(
                f"{method} {endpoint} - requires auth (401)",
                method,
                endpoint,
                401
            )

        # Restore token
        self.token = original_token

    def test_existing_endpoints(self):
        """Verify existing endpoints still work."""
        self.log("\n" + "="*60)
        self.log("🔄 TESTING EXISTING ENDPOINTS")
        self.log("="*60)

        endpoints = [
            ("GET", "/products", 200),
            ("GET", "/video/voices", 200),
            ("GET", "/workforce/agents", 200),
        ]

        for method, endpoint, expected in endpoints:
            self.test(
                f"{method} {endpoint} - still works",
                method,
                endpoint,
                expected
            )

    def print_summary(self):
        """Print test summary."""
        self.log("\n" + "="*60)
        self.log("📊 TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}")
        self.log(f"Failed: {self.tests_run - self.tests_passed}")
        self.log(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ Failed tests:")
            for test in self.failed_tests:
                self.log(f"   - {test}")
        
        return 0 if self.tests_passed == self.tests_run else 1


def main():
    tester = ChatBuilderTester()
    
    # Login
    if not tester.login("admin@getszy.com", "Admin@123"):
        print("❌ Login failed, cannot proceed with tests")
        return 1

    # Run all test suites
    tester.test_capabilities()
    tester.test_session_crud()
    tester.test_messaging_and_polling()
    tester.test_e2e_general_chat()
    tester.test_e2e_write_script()
    tester.test_e2e_build_webapp()
    tester.test_e2e_predict_trends()
    tester.test_auth_required()
    tester.test_existing_endpoints()

    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
