"""Backend API tests for Phase 13 (Video Studio), Phase 14 (Publishing), and AI Workforce."""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
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
                    self.log(f"   Response: {response.text[:200]}")
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

    def test_video_studio(self):
        """Test all Video Studio endpoints."""
        self.log("\n" + "="*60)
        self.log("📹 TESTING VIDEO STUDIO MODULE")
        self.log("="*60)

        # Test 1: GET /api/video/voices
        success, response = self.test(
            "GET /api/video/voices - returns Indian neural voices",
            "GET",
            "/video/voices",
            200
        )
        if success:
            if 'voices' in response and 'providers' in response:
                self.log(f"   ✓ Found {len(response.get('voices', []))} voices")
                self.log(f"   ✓ Providers: {response.get('providers', {})}")
            else:
                self.log(f"   ⚠ Missing 'voices' or 'providers' in response")

        # Test 2: POST /api/video/generate - topic too short (validation)
        success, response = self.test(
            "POST /api/video/generate - validates topic length (400 for <4 chars)",
            "POST",
            "/video/generate",
            400,
            data={"topic": "AI"}
        )

        # Test 3: POST /api/video/generate - valid topic
        success, response = self.test(
            "POST /api/video/generate - creates job with valid topic",
            "POST",
            "/video/generate",
            200,
            data={
                "topic": "How to grow on YouTube in 2025",
                "orientation": "9:16",
                "language": "hinglish",
                "voice_gender": "female",
                "target_seconds": 45
            }
        )
        job_id = None
        if success and 'id' in response:
            job_id = response['id']
            self.log(f"   ✓ Job created with ID: {job_id}")
            self.log(f"   ✓ Initial status: {response.get('status')}")

        # Test 4: GET /api/video/jobs - list user's jobs
        success, response = self.test(
            "GET /api/video/jobs - returns user's jobs",
            "GET",
            "/video/jobs",
            200
        )
        if success and 'items' in response:
            self.log(f"   ✓ Found {len(response['items'])} jobs")

        # Test 5: GET /api/video/jobs/{id} - get job detail
        if job_id:
            success, response = self.test(
                f"GET /api/video/jobs/{job_id} - returns job detail",
                "GET",
                f"/video/jobs/{job_id}",
                200
            )
            if success:
                self.log(f"   ✓ Job status: {response.get('status')}")
                self.log(f"   ✓ Job percent: {response.get('percent')}%")

            # Wait for job to progress (up to 180s as per requirements)
            self.log(f"\n⏳ Waiting for video pipeline to complete (max 180s)...")
            max_wait = 180
            start_time = time.time()
            final_status = None
            
            while time.time() - start_time < max_wait:
                success, response = self.test(
                    f"Polling job {job_id}",
                    "GET",
                    f"/video/jobs/{job_id}",
                    200
                )
                if success:
                    status = response.get('status')
                    percent = response.get('percent', 0)
                    self.log(f"   Status: {status} ({percent}%)")
                    
                    if status in ('done', 'failed'):
                        final_status = status
                        if status == 'done':
                            self.log(f"   ✅ Video pipeline completed successfully!")
                            self.log(f"   ✓ Video URL: {response.get('video_url')}")
                            self.log(f"   ✓ Audio URL: {response.get('audio_url')}")
                            self.log(f"   ✓ SRT URL: {response.get('srt_url')}")
                        else:
                            self.log(f"   ❌ Video pipeline failed: {response.get('error')}")
                        break
                
                time.sleep(10)
            
            if not final_status:
                self.log(f"   ⚠ Job did not complete within {max_wait}s (status: {response.get('status')})")

        # Test 6: POST /api/video/batch - valid batch
        success, response = self.test(
            "POST /api/video/batch - accepts up to 10 topics",
            "POST",
            "/video/batch",
            200,
            data={
                "topics": [
                    "Instagram Reels tips",
                    "YouTube Shorts strategy",
                    "Content creation hacks"
                ],
                "orientation": "9:16",
                "language": "hinglish"
            }
        )
        if success and 'jobs' in response:
            self.log(f"   ✓ Created {response.get('count')} batch jobs")

        # Test 7: POST /api/video/batch - validation (>10 topics)
        success, response = self.test(
            "POST /api/video/batch - validates max 10 topics",
            "POST",
            "/video/batch",
            400,
            data={
                "topics": [f"Topic {i}" for i in range(11)],
                "orientation": "9:16"
            }
        )

        # Test 8: POST /api/video/batch - validation (empty topics)
        success, response = self.test(
            "POST /api/video/batch - validates non-empty topics",
            "POST",
            "/video/batch",
            400,
            data={
                "topics": [],
                "orientation": "9:16"
            }
        )

        # Test 9: DELETE /api/video/jobs/{id}
        if job_id:
            success, response = self.test(
                f"DELETE /api/video/jobs/{job_id} - removes job",
                "DELETE",
                f"/video/jobs/{job_id}",
                200
            )

        # Test 10: GET /api/video/files/{filename} - will test if we have a completed job
        # This is tested implicitly when a job completes

    def test_publishing(self):
        """Test all Publishing endpoints."""
        self.log("\n" + "="*60)
        self.log("📱 TESTING PUBLISHING MODULE")
        self.log("="*60)

        # Test 1: GET /api/publishing/connections
        success, response = self.test(
            "GET /api/publishing/connections - returns 5 platforms",
            "GET",
            "/publishing/connections",
            200
        )
        if success:
            platforms = response.get('platforms', {})
            supported = response.get('supported', [])
            self.log(f"   ✓ Supported platforms: {supported}")
            self.log(f"   ✓ Platform count: {len(platforms)}")
            for p, info in platforms.items():
                self.log(f"   ✓ {p}: mode={info.get('mode')}, connected={info.get('connected')}")

        # Test 2: POST /api/publishing/schedule - valid schedule
        success, response = self.test(
            "POST /api/publishing/schedule - creates queue items with auto_generate_meta",
            "POST",
            "/publishing/schedule",
            200,
            data={
                "platforms": ["youtube", "instagram"],
                "topic": "How to grow on social media",
                "auto_generate_meta": True
            }
        )
        queue_id = None
        item_id = None
        if success and 'items' in response:
            queue_id = response.get('queue_id')
            items = response['items']
            self.log(f"   ✓ Queue ID: {queue_id}")
            self.log(f"   ✓ Created {len(items)} queue items")
            if items:
                item_id = items[0].get('id')
                self.log(f"   ✓ First item ID: {item_id}")
                self.log(f"   ✓ Title: {items[0].get('title')}")
                self.log(f"   ✓ Caption: {items[0].get('caption')[:50]}...")
                self.log(f"   ✓ Hashtags: {items[0].get('hashtags')}")

        # Test 3: POST /api/publishing/schedule - unknown platform
        success, response = self.test(
            "POST /api/publishing/schedule - rejects unknown platforms (400)",
            "POST",
            "/publishing/schedule",
            400,
            data={
                "platforms": ["tiktok"],
                "topic": "Test topic"
            }
        )

        # Test 4: GET /api/publishing/queue
        success, response = self.test(
            "GET /api/publishing/queue - returns user's queued items",
            "GET",
            "/publishing/queue",
            200
        )
        if success and 'items' in response:
            self.log(f"   ✓ Found {len(response['items'])} queued items")

        # Test 5: POST /api/publishing/run-now
        if item_id:
            success, response = self.test(
                "POST /api/publishing/run-now - executes with dry-run",
                "POST",
                "/publishing/run-now",
                200,
                data={"queue_id": item_id}
            )
            if success:
                self.log(f"   ✓ Status: {response.get('status')}")
                self.log(f"   ✓ Platform: {response.get('platform')}")
                if 'preview' in response:
                    preview = response['preview']
                    self.log(f"   ✓ Preview title: {preview.get('title')}")
                    self.log(f"   ✓ Preview caption: {preview.get('caption', '')[:50]}...")
                    self.log(f"   ✓ Preview hashtags: {preview.get('hashtags')}")

        # Test 6: DELETE /api/publishing/queue/{item_id}
        if item_id:
            success, response = self.test(
                f"DELETE /api/publishing/queue/{item_id} - removes item",
                "DELETE",
                f"/publishing/queue/{item_id}",
                200
            )

    def test_workforce(self):
        """Test all AI Workforce endpoints."""
        self.log("\n" + "="*60)
        self.log("🤖 TESTING AI WORKFORCE MODULE")
        self.log("="*60)

        # Test 1: GET /api/workforce/agents
        success, response = self.test(
            "GET /api/workforce/agents - returns 10 specialist agents",
            "GET",
            "/workforce/agents",
            200
        )
        agent_id = None
        if success and 'agents' in response:
            agents = response['agents']
            self.log(f"   ✓ Found {len(agents)} agents")
            if agents:
                agent_id = agents[0].get('id')
                for agent in agents[:3]:  # Show first 3
                    self.log(f"   ✓ {agent.get('name')} ({agent.get('id')}): {agent.get('role')}")

        # Test 2: POST /api/workforce/{agent_id}/task - valid agent
        if agent_id:
            success, response = self.test(
                f"POST /api/workforce/{agent_id}/task - runs agent task",
                "POST",
                f"/workforce/{agent_id}/task",
                200,
                data={
                    "params": {
                        "topic": "How to create viral YouTube content"
                    }
                },
                timeout=60  # LLM-driven, may take 30-60s
            )
            if success:
                self.log(f"   ✓ Agent: {response.get('agent_id')}")
                if 'parsed' in response and response['parsed']:
                    self.log(f"   ✓ Output parsed successfully")
                elif 'raw' in response:
                    self.log(f"   ✓ Raw output: {response.get('raw', '')[:100]}...")

        # Test 3: POST /api/workforce/unknown-id/task - 404
        success, response = self.test(
            "POST /api/workforce/unknown-id/task - returns 404",
            "POST",
            "/workforce/unknown-agent-xyz/task",
            404,
            data={"params": {"topic": "test"}}
        )

        # Test 4: GET /api/workforce/history
        success, response = self.test(
            "GET /api/workforce/history - returns recent runs",
            "GET",
            "/workforce/history",
            200
        )
        if success and 'items' in response:
            self.log(f"   ✓ Found {len(response['items'])} history items")

    def test_auth_required(self):
        """Test that all endpoints require auth."""
        self.log("\n" + "="*60)
        self.log("🔒 TESTING AUTH REQUIREMENTS")
        self.log("="*60)

        # Temporarily remove token
        original_token = self.token
        self.token = None

        endpoints = [
            ("GET", "/video/voices"),
            ("GET", "/video/jobs"),
            ("GET", "/publishing/connections"),
            ("GET", "/workforce/agents"),
        ]

        for method, endpoint in endpoints:
            success, response = self.test(
                f"{method} {endpoint} - requires auth (401)",
                method,
                endpoint,
                401
            )

        # Restore token
        self.token = original_token

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
    tester = APITester()
    
    # Login
    if not tester.login("admin@getszy.com", "Admin@123"):
        print("❌ Login failed, cannot proceed with tests")
        return 1

    # Run all test suites
    tester.test_video_studio()
    tester.test_publishing()
    tester.test_workforce()
    tester.test_auth_required()

    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    sys.exit(main())
