"""
Build Studio Backend API Tests
Tests all Build Studio endpoints: hub, channel, agent, starter, projects
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"
TEST_EMAIL = "admin@getszy.com"
TEST_PASSWORD = "Admin@123"

class BuildStudioTester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.channel_id = None
        self.agent_id = None
        self.starter_ids = []
        self.project_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=120):
        """Run a single API test"""
        url = f"{BASE_URL}/{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=timeout)
            else:
                self.log(f"❌ Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ Passed - Status: {response.status_code}")
            else:
                self.log(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except requests.exceptions.Timeout:
            self.log(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            self.log(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login and get token"""
        self.log("\n=== AUTH TESTS ===")
        success, response = self.run_test(
            "Login",
            "POST",
            "auth/login",
            200,
            data={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"✅ Token obtained: {self.token[:20]}...")
            return True
        self.log("❌ Login failed - cannot proceed with authenticated tests")
        return False

    def test_auth_required(self):
        """Test that endpoints require auth (401 without token)"""
        self.log("\n=== AUTH REQUIRED TESTS ===")
        saved_token = self.token
        self.token = None
        
        endpoints = [
            ("builder/hub", "GET"),
            ("builder/channel", "GET"),
            ("builder/agent", "GET"),
            ("builder/starter", "GET"),
            ("builder/projects", "GET"),
        ]
        
        all_passed = True
        for endpoint, method in endpoints:
            success, _ = self.run_test(
                f"401 check: {endpoint}",
                method,
                endpoint,
                401
            )
            if not success:
                all_passed = False
        
        self.token = saved_token
        return all_passed

    def test_hub(self):
        """Test GET /api/builder/hub"""
        self.log("\n=== HUB TESTS ===")
        success, response = self.run_test(
            "Get Build Hub",
            "GET",
            "builder/hub",
            200
        )
        
        if success:
            # Verify structure
            if 'counts' not in response:
                self.log("❌ Missing 'counts' in response")
                return False
            if 'categories' not in response:
                self.log("❌ Missing 'categories' in response")
                return False
            
            # Check counts keys
            expected_keys = ['webapps', 'channels', 'agents', 'starters', 'videos']
            for key in expected_keys:
                if key not in response['counts']:
                    self.log(f"❌ Missing count key: {key}")
                    return False
            
            # Check categories count
            if len(response['categories']) != 6:
                self.log(f"❌ Expected 6 categories, got {len(response['categories'])}")
                return False
            
            # Check category IDs
            expected_cats = ['webapp', 'channel', 'agent', 'mobileapp', 'fullstack', 'blog']
            cat_ids = [c['id'] for c in response['categories']]
            for cat in expected_cats:
                if cat not in cat_ids:
                    self.log(f"❌ Missing category: {cat}")
                    return False
            
            self.log(f"✅ Hub structure valid: {response['counts']}")
            return True
        
        return False

    def test_channel_plan(self):
        """Test POST /api/builder/channel/plan"""
        self.log("\n=== CHANNEL TESTS ===")
        success, response = self.run_test(
            "Create Channel Plan",
            "POST",
            "builder/channel/plan",
            200,
            data={
                "niche": "AI tools for Indian students",
                "audience": "Indian college students",
                "style": "energetic",
                "posts_per_week": 5,
                "language": "hinglish",
                "orientation": "9:16"
            },
            timeout=90
        )
        
        if success:
            if 'id' not in response:
                self.log("❌ Missing 'id' in channel plan response")
                return False
            if 'plan' not in response:
                self.log("❌ Missing 'plan' in response")
                return False
            if 'videos' not in response.get('plan', {}):
                self.log("❌ Missing 'videos' array in plan")
                return False
            
            self.channel_id = response['id']
            video_count = len(response['plan']['videos'])
            self.log(f"✅ Channel plan created with {video_count} videos, ID: {self.channel_id}")
            return True
        
        return False

    def test_channel_execute(self):
        """Test POST /api/builder/channel/execute"""
        if not self.channel_id:
            self.log("⚠️  Skipping channel execute - no channel_id")
            return False
        
        success, response = self.run_test(
            "Execute Channel Videos",
            "POST",
            "builder/channel/execute",
            200,
            data={
                "channel_id": self.channel_id,
                "max_videos": 2
            },
            timeout=30
        )
        
        if success:
            if 'queued_video_ids' not in response:
                self.log("❌ Missing 'queued_video_ids' in response")
                return False
            if not isinstance(response['queued_video_ids'], list):
                self.log("❌ 'queued_video_ids' is not a list")
                return False
            if len(response['queued_video_ids']) == 0:
                self.log("❌ No video IDs returned")
                return False
            
            self.log(f"✅ Queued {len(response['queued_video_ids'])} videos: {response['queued_video_ids']}")
            return True
        
        return False

    def test_channel_list(self):
        """Test GET /api/builder/channel"""
        success, response = self.run_test(
            "List Channels",
            "GET",
            "builder/channel",
            200
        )
        
        if success:
            if 'items' not in response:
                self.log("❌ Missing 'items' in response")
                return False
            self.log(f"✅ Found {len(response['items'])} channels")
            return True
        
        return False

    def test_channel_delete(self):
        """Test DELETE /api/builder/channel/{id}"""
        if not self.channel_id:
            self.log("⚠️  Skipping channel delete - no channel_id")
            return False
        
        success, response = self.run_test(
            "Delete Channel",
            "DELETE",
            f"builder/channel/{self.channel_id}",
            200
        )
        
        if success:
            if response.get('deleted', 0) > 0:
                self.log(f"✅ Channel deleted: {self.channel_id}")
                return True
            else:
                self.log("❌ Delete returned 0 deleted count")
                return False
        
        return False

    def test_agent_create(self):
        """Test POST /api/builder/agent"""
        self.log("\n=== AGENT TESTS ===")
        
        # Test validation: name too short
        success, _ = self.run_test(
            "Agent validation (name < 2 chars)",
            "POST",
            "builder/agent",
            400,
            data={
                "name": "A",
                "role": "Test agent",
                "system_prompt": "You are a test agent"
            }
        )
        
        # Create valid agent
        success, response = self.run_test(
            "Create Custom Agent",
            "POST",
            "builder/agent",
            200,
            data={
                "name": "Test Blog Writer",
                "role": "Writes blog posts for Indian audiences",
                "system_prompt": "You are a blog writer. Given a topic, output JSON with title, intro, sections, conclusion.",
                "param_keys": ["topic", "audience"],
                "color": "#7c3aed",
                "icon": "Bot"
            }
        )
        
        if success:
            if 'id' not in response:
                self.log("❌ Missing 'id' in agent response")
                return False
            
            self.agent_id = response['id']
            self.log(f"✅ Agent created, ID: {self.agent_id}")
            return True
        
        return False

    def test_agent_list(self):
        """Test GET /api/builder/agent"""
        success, response = self.run_test(
            "List Custom Agents",
            "GET",
            "builder/agent",
            200
        )
        
        if success:
            if 'items' not in response:
                self.log("❌ Missing 'items' in response")
                return False
            self.log(f"✅ Found {len(response['items'])} agents")
            return True
        
        return False

    def test_agent_run(self):
        """Test POST /api/builder/agent/{id}/run"""
        if not self.agent_id:
            self.log("⚠️  Skipping agent run - no agent_id")
            return False
        
        success, response = self.run_test(
            "Run Custom Agent",
            "POST",
            f"builder/agent/{self.agent_id}/run",
            200,
            data={
                "params": {
                    "topic": "Personal finance tips for Indian millennials",
                    "audience": "Young professionals in India"
                }
            },
            timeout=90
        )
        
        if success:
            if 'id' not in response:
                self.log("❌ Missing 'id' in run response")
                return False
            if 'raw' not in response:
                self.log("❌ Missing 'raw' output in response")
                return False
            
            self.log(f"✅ Agent run completed, output length: {len(response.get('raw', ''))}")
            return True
        
        return False

    def test_agent_delete(self):
        """Test DELETE /api/builder/agent/{id}"""
        if not self.agent_id:
            self.log("⚠️  Skipping agent delete - no agent_id")
            return False
        
        success, response = self.run_test(
            "Delete Custom Agent",
            "DELETE",
            f"builder/agent/{self.agent_id}",
            200
        )
        
        if success:
            if response.get('deleted', 0) > 0:
                self.log(f"✅ Agent deleted: {self.agent_id}")
                return True
            else:
                self.log("❌ Delete returned 0 deleted count")
                return False
        
        return False

    def test_starter_mobileapp(self):
        """Test POST /api/builder/starter with kind=mobileapp"""
        self.log("\n=== STARTER TESTS ===")
        success, response = self.run_test(
            "Create Mobile App Starter",
            "POST",
            "builder/starter",
            200,
            data={
                "kind": "mobileapp",
                "prompt": "Indian food delivery app with order tracking",
                "app_name": "FoodExpress"
            },
            timeout=90
        )
        
        if success:
            if 'id' not in response:
                self.log("❌ Missing 'id' in starter response")
                return False
            if 'download_url' not in response:
                self.log("❌ Missing 'download_url' in response")
                return False
            if response.get('size_bytes', 0) < 1000:
                self.log(f"❌ Starter size too small: {response.get('size_bytes')} bytes")
                return False
            
            self.starter_ids.append(response['id'])
            self.log(f"✅ Mobile app starter created, size: {response['size_bytes']} bytes")
            return True
        
        return False

    def test_starter_fullstack(self):
        """Test POST /api/builder/starter with kind=fullstack"""
        success, response = self.run_test(
            "Create Full-Stack Starter",
            "POST",
            "builder/starter",
            200,
            data={
                "kind": "fullstack",
                "prompt": "Task manager with categories and due dates",
                "app_name": "TaskMaster"
            },
            timeout=90
        )
        
        if success:
            if response.get('size_bytes', 0) < 1000:
                self.log(f"❌ Starter size too small: {response.get('size_bytes')} bytes")
                return False
            
            self.starter_ids.append(response['id'])
            self.log(f"✅ Full-stack starter created, size: {response['size_bytes']} bytes")
            return True
        
        return False

    def test_starter_blog(self):
        """Test POST /api/builder/starter with kind=blog"""
        success, response = self.run_test(
            "Create Blog Starter",
            "POST",
            "builder/starter",
            200,
            data={
                "kind": "blog",
                "prompt": "Personal finance blog for Indian millennials",
                "app_name": "FinanceGuru"
            },
            timeout=90
        )
        
        if success:
            if response.get('size_bytes', 0) < 1000:
                self.log(f"❌ Starter size too small: {response.get('size_bytes')} bytes")
                return False
            
            self.starter_ids.append(response['id'])
            self.log(f"✅ Blog starter created, size: {response['size_bytes']} bytes")
            return True
        
        return False

    def test_starter_invalid(self):
        """Test POST /api/builder/starter with invalid kind"""
        success, _ = self.run_test(
            "Create Starter with Invalid Kind",
            "POST",
            "builder/starter",
            400,
            data={
                "kind": "invalid",
                "prompt": "Test prompt"
            }
        )
        
        return success

    def test_starter_list(self):
        """Test GET /api/builder/starter"""
        success, response = self.run_test(
            "List Starters",
            "GET",
            "builder/starter",
            200
        )
        
        if success:
            if 'items' not in response:
                self.log("❌ Missing 'items' in response")
                return False
            self.log(f"✅ Found {len(response['items'])} starters")
            return True
        
        return False

    def test_starter_download(self):
        """Test GET /api/builder/starter/{id}/download"""
        if not self.starter_ids:
            self.log("⚠️  Skipping starter download - no starter_ids")
            return False
        
        starter_id = self.starter_ids[0]
        url = f"{BASE_URL}/builder/starter/{starter_id}/download"
        
        self.tests_run += 1
        self.log(f"🔍 Testing Download Starter...")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                if response.headers.get('content-type') == 'application/zip':
                    self.tests_passed += 1
                    self.log(f"✅ Passed - Downloaded {len(response.content)} bytes as ZIP")
                    return True
                else:
                    self.log(f"❌ Wrong content-type: {response.headers.get('content-type')}")
                    return False
            else:
                self.log(f"❌ Failed - Status: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Failed - Error: {str(e)}")
            return False

    def test_starter_delete(self):
        """Test DELETE /api/builder/starter/{id}"""
        if not self.starter_ids:
            self.log("⚠️  Skipping starter delete - no starter_ids")
            return False
        
        for starter_id in self.starter_ids:
            success, response = self.run_test(
                f"Delete Starter {starter_id[:8]}",
                "DELETE",
                f"builder/starter/{starter_id}",
                200
            )
            
            if not success or not response.get('ok'):
                return False
        
        self.log(f"✅ All {len(self.starter_ids)} starters deleted")
        return True

    def test_projects(self):
        """Test POST /api/builder/projects (existing web app builder)"""
        self.log("\n=== WEB APP BUILDER TESTS ===")
        success, response = self.run_test(
            "Create Web App Project",
            "POST",
            "builder/projects",
            200,
            data={
                "prompt": "Modern landing page for a Kathak dance academy in Jaipur",
                "name": "Kathak Academy"
            },
            timeout=90
        )
        
        if success:
            if 'id' not in response:
                self.log("❌ Missing 'id' in project response")
                return False
            if 'html_content' not in response:
                self.log("❌ Missing 'html_content' in response")
                return False
            
            self.project_id = response['id']
            self.log(f"✅ Web app project created, ID: {self.project_id}")
            return True
        
        return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("=" * 60)
        self.log("BUILD STUDIO BACKEND API TESTS")
        self.log("=" * 60)
        
        # Auth
        if not self.test_login():
            self.log("\n❌ Cannot proceed without authentication")
            return False
        
        # Auth required tests
        self.test_auth_required()
        
        # Hub
        self.test_hub()
        
        # Channel
        self.test_channel_plan()
        self.test_channel_execute()
        self.test_channel_list()
        self.test_channel_delete()
        
        # Agent
        self.test_agent_create()
        self.test_agent_list()
        self.test_agent_run()
        self.test_agent_delete()
        
        # Starter
        self.test_starter_mobileapp()
        self.test_starter_fullstack()
        self.test_starter_blog()
        self.test_starter_invalid()
        self.test_starter_list()
        self.test_starter_download()
        self.test_starter_delete()
        
        # Web App Builder
        self.test_projects()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log(f"TESTS COMPLETED: {self.tests_passed}/{self.tests_run} passed")
        self.log("=" * 60)
        
        return self.tests_passed == self.tests_run


def main():
    tester = BuildStudioTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
