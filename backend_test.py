#!/usr/bin/env python3
"""
Phase 6 Monetization Backend API Tests
Tests subscription, pricing, gating, and AI provider sanitization
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

class APITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.admin_token = None
        self.customer_token = None
        self.fresh_user_token = None
        self.fresh_user_email = None
        self.failed_tests = []

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
                    self.log(f"Response: {response.json()}", Colors.YELLOW)
                except:
                    self.log(f"Response: {response.text[:200]}", Colors.YELLOW)
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            self.log(f"❌ FAIL - Error: {str(e)}", Colors.RED)
            return False, {}

    def check_sanitization(self, data, test_name):
        """Check if AI provider info is leaked"""
        data_str = json.dumps(data).lower()
        leaked_words = []
        for word in ['provider', 'ollama', 'emergent', 'openai', 'gpt']:
            if word in data_str:
                leaked_words.append(word)
        
        if leaked_words:
            self.log(f"⚠️  WARNING: AI provider info leaked in {test_name}: {leaked_words}", Colors.YELLOW)
            return False
        return True

    def run_all_tests(self):
        self.log("=" * 80, Colors.BLUE)
        self.log("PHASE 6 MONETIZATION BACKEND TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # ===== 1. SANITIZATION TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("1. AI PROVIDER SANITIZATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        success, data = self.test("Health endpoint sanitization", "GET", "/health", 200)
        if success:
            self.check_sanitization(data, "health endpoint")
            if data.get('ai') == 'Getszy AI':
                self.log("✅ Health endpoint has correct branding: 'Getszy AI'", Colors.GREEN)
            else:
                self.log(f"⚠️  Health endpoint ai field: {data.get('ai')}", Colors.YELLOW)

        success, data = self.test("Root endpoint sanitization", "GET", "/", 200)
        if success:
            self.check_sanitization(data, "root endpoint")
            if data.get('ai') == 'Getszy AI':
                self.log("✅ Root endpoint has correct branding: 'Getszy AI'", Colors.GREEN)

        # ===== 2. AUTHENTICATION =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("2. AUTHENTICATION TESTS", Colors.BLUE)
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
            self.log(f"✅ Admin token obtained", Colors.GREEN)

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
            self.log(f"✅ Customer token obtained", Colors.GREEN)

        # Create fresh user for gating tests
        timestamp = datetime.now().strftime("%H%M%S")
        self.fresh_user_email = f"free-test-{timestamp}@example.com"
        success, data = self.test(
            "Create fresh free user",
            "POST",
            "/auth/signup",
            200,
            data={
                "name": "Free Test User",
                "email": self.fresh_user_email,
                "password": "Test@123",
                "phone": "9999999999"
            }
        )
        if success and 'token' in data:
            self.fresh_user_token = data['token']
            self.log(f"✅ Fresh user created: {self.fresh_user_email}", Colors.GREEN)

        # ===== 3. PRICING ENDPOINT =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("3. PRICING ENDPOINT TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        success, data = self.test("Get pricing plans", "GET", "/pricing", 200)
        if success:
            plans = data.get('plans', [])
            if len(plans) == 3:
                self.log(f"✅ Found 3 pricing plans", Colors.GREEN)
                for plan in plans:
                    self.log(f"  - {plan.get('name')}: ₹{plan.get('price_monthly')}/mo, ₹{plan.get('price_yearly')}/yr", Colors.BLUE)
            else:
                self.log(f"⚠️  Expected 3 plans, found {len(plans)}", Colors.YELLOW)

        # ===== 4. SUBSCRIPTION ENDPOINTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("4. SUBSCRIPTION ENDPOINTS TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Get customer subscription (default free)
        success, data = self.test(
            "Get customer subscription",
            "GET",
            "/me/subscription",
            200,
            token=self.customer_token
        )
        if success:
            self.log(f"  Plan: {data.get('plan')}, Status: {data.get('status')}", Colors.BLUE)
            self.log(f"  Studio builds: {data.get('studio_builds_used', 0)}/{data.get('quota', {}).get('studio_builds', 0)}", Colors.BLUE)

        # Get auth/me with embedded subscription
        success, data = self.test(
            "Get /auth/me with subscription",
            "GET",
            "/auth/me",
            200,
            token=self.customer_token
        )
        if success:
            if 'subscription' in data:
                self.log(f"✅ User has embedded subscription field", Colors.GREEN)
                self.log(f"  Plan: {data['subscription'].get('plan')}", Colors.BLUE)
            else:
                self.log(f"⚠️  No subscription field in /auth/me response", Colors.YELLOW)

        # ===== 5. TRIAL ACTIVATION =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("5. TRIAL ACTIVATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Start trial for fresh user
        success, data = self.test(
            "Start 7-day free trial (fresh user)",
            "POST",
            "/me/subscription/start-trial",
            200,
            token=self.fresh_user_token
        )
        if success:
            if data.get('plan') == 'pro' and data.get('status') == 'trial':
                self.log(f"✅ Trial activated: plan={data.get('plan')}, status={data.get('status')}", Colors.GREEN)
                self.log(f"  Trial ends: {data.get('trial_ends_at')}", Colors.BLUE)
            else:
                self.log(f"⚠️  Trial response: {data}", Colors.YELLOW)

        # Try to start trial again (should fail)
        success, data = self.test(
            "Start trial again (should fail with 400)",
            "POST",
            "/me/subscription/start-trial",
            400,
            token=self.fresh_user_token
        )
        if success:
            self.log(f"✅ Correctly rejected second trial attempt", Colors.GREEN)

        # Verify subscription after trial
        success, data = self.test(
            "Get subscription after trial",
            "GET",
            "/me/subscription",
            200,
            token=self.fresh_user_token
        )
        if success:
            if data.get('plan') == 'pro' and data.get('status') == 'trial':
                self.log(f"✅ Subscription shows Pro Trial", Colors.GREEN)
                quota = data.get('quota', {})
                if quota.get('studio_builds') == 10:
                    self.log(f"✅ Studio builds quota: {quota.get('studio_builds')}", Colors.GREEN)
                else:
                    self.log(f"⚠️  Studio builds quota: {quota.get('studio_builds')} (expected 10)", Colors.YELLOW)

        # ===== 6. UPGRADE ENDPOINT (STUB) =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("6. UPGRADE ENDPOINT (RAZORPAY STUB) TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        success, data = self.test(
            "Upgrade to Pro (stub)",
            "POST",
            "/me/subscription/upgrade",
            200,
            data={"plan": "pro", "interval": "monthly"},
            token=self.customer_token
        )
        if success:
            if data.get('status') == 'pending':
                self.log(f"✅ Upgrade returns 'pending' status (Razorpay stub)", Colors.GREEN)
                self.log(f"  Message: {data.get('message')}", Colors.BLUE)
            else:
                self.log(f"⚠️  Upgrade response: {data}", Colors.YELLOW)

        # ===== 7. COURSE GATING =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("7. COURSE GATING TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Create another fresh user for course gating (to avoid trial interference)
        timestamp2 = datetime.now().strftime("%H%M%S%f")
        fresh_email2 = f"course-test-{timestamp2}@example.com"
        success, data = self.test(
            "Create fresh user for course gating",
            "POST",
            "/auth/signup",
            200,
            data={
                "name": "Course Test User",
                "email": fresh_email2,
                "password": "Test@123",
                "phone": "8888888888"
            }
        )
        fresh_token2 = None
        if success and 'token' in data:
            fresh_token2 = data['token']
            self.log(f"✅ Fresh user created: {fresh_email2}", Colors.GREEN)

        # Try to enroll in Advanced course (should fail with 402)
        if fresh_token2:
            success, data = self.test(
                "Enroll in Advanced course (should fail 402)",
                "POST",
                "/courses/become-ai-independent-career-path/enroll",
                402,
                token=fresh_token2
            )
            if success:
                self.log(f"✅ Advanced course correctly gated for free users", Colors.GREEN)

            # Try to enroll in Beginner course (should succeed)
            success, data = self.test(
                "Enroll in Beginner course (should succeed)",
                "POST",
                "/courses/ai-foundations-for-women/enroll",
                200,
                token=fresh_token2
            )
            if success:
                self.log(f"✅ Beginner course enrollment succeeded", Colors.GREEN)

        # ===== 8. STUDIO GATING =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("8. STUDIO GATING TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # Create another fresh user for studio gating
        timestamp3 = datetime.now().strftime("%H%M%S%f")
        fresh_email3 = f"studio-test-{timestamp3}@example.com"
        success, data = self.test(
            "Create fresh user for studio gating",
            "POST",
            "/auth/signup",
            200,
            data={
                "name": "Studio Test User",
                "email": fresh_email3,
                "password": "Test@123",
                "phone": "7777777777"
            }
        )
        fresh_token3 = None
        if success and 'token' in data:
            fresh_token3 = data['token']
            self.log(f"✅ Fresh user created: {fresh_email3}", Colors.GREEN)

        # Try to create studio project as free user (should fail with 402)
        if fresh_token3:
            success, data = self.test(
                "Create studio project as free user (should fail 402)",
                "POST",
                "/builder/projects",
                402,
                data={"prompt": "Build a test website"},
                token=fresh_token3
            )
            if success:
                self.log(f"✅ Studio correctly gated for free users", Colors.GREEN)

        # Create studio project as PRO user (with trial)
        success, data = self.test(
            "Create studio project as PRO user",
            "POST",
            "/builder/projects",
            200,
            data={"prompt": "Build a simple landing page for testing"},
            token=self.fresh_user_token
        )
        if success:
            self.log(f"✅ PRO user can create studio project", Colors.GREEN)
            project_id = data.get('id')
            
            # Check if studio_builds_used incremented
            success2, sub_data = self.test(
                "Check studio builds usage after creation",
                "GET",
                "/me/subscription",
                200,
                token=self.fresh_user_token
            )
            if success2:
                builds_used = sub_data.get('studio_builds_used', 0)
                if builds_used >= 1:
                    self.log(f"✅ Studio builds incremented: {builds_used}", Colors.GREEN)
                else:
                    self.log(f"⚠️  Studio builds not incremented: {builds_used}", Colors.YELLOW)

        # ===== 9. VIDEO URL MIGRATION =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("9. VIDEO URL MIGRATION TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        # This requires direct DB access or checking a lesson endpoint
        # For now, we'll check via course detail
        success, data = self.test(
            "Get course with lessons",
            "GET",
            "/courses/ai-foundations-for-women",
            200
        )
        if success:
            modules = data.get('modules', [])
            all_cleared = True
            for module in modules:
                for lesson in module.get('lessons', []):
                    video_url = lesson.get('video_url', '')
                    if video_url and ('youtube' in video_url.lower() or 'youtu.be' in video_url.lower() or 'vimeo' in video_url.lower()):
                        all_cleared = False
                        self.log(f"⚠️  Lesson '{lesson.get('title')}' still has external video: {video_url}", Colors.YELLOW)
            
            if all_cleared:
                self.log(f"✅ All lessons have cleared video URLs (no YouTube/Vimeo)", Colors.GREEN)

        # ===== 10. ADMIN ENDPOINTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("10. ADMIN SUBSCRIPTION ENDPOINTS TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            success, data = self.test(
                "Get admin subscriptions stats",
                "GET",
                "/admin/subscriptions",
                200,
                token=self.admin_token
            )
            if success:
                self.log(f"✅ Admin subscriptions endpoint working", Colors.GREEN)
                self.log(f"  Total users: {data.get('total_users')}", Colors.BLUE)
                self.log(f"  Pro count: {data.get('pro_count')}", Colors.BLUE)
                self.log(f"  Elite count: {data.get('elite_count')}", Colors.BLUE)
                self.log(f"  Trial count: {data.get('trial_count')}", Colors.BLUE)
                self.log(f"  MRR: ₹{data.get('mrr')}", Colors.BLUE)

            # Grant plan to customer
            success, data = self.test(
                "Admin grant Pro plan to customer",
                "POST",
                "/admin/subscriptions/grant",
                200,
                data={"email": "customer@getszy.com", "plan": "pro", "days": 30},
                token=self.admin_token
            )
            if success:
                self.log(f"✅ Admin can grant plans", Colors.GREEN)
                self.log(f"  Granted to: {data.get('user')}", Colors.BLUE)

        # ===== SUMMARY =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        self.log(f"\nTotal tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED)
        self.log(f"Success rate: {success_rate:.1f}%", Colors.BLUE)
        
        if self.failed_tests:
            self.log(f"\nFailed tests:", Colors.RED)
            for test in self.failed_tests:
                self.log(f"  - {test}", Colors.RED)
        
        return 0 if self.tests_failed == 0 else 1

def main():
    tester = APITester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
