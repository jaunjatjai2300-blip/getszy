#!/usr/bin/env python3
"""
Phase 5 AI Ops Dashboard + Phase 6 Monetization + Phase 7 Sourcing + Phase 8 Media Studio Backend API Tests
Tests AI Ops Dashboard, subscription, pricing, gating, AI provider sanitization, sourcing, and media studio
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
        self.log("PHASE 5 AI OPS + PHASE 6 MONETIZATION BACKEND TESTS", Colors.BLUE)
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

        # ===== 11. AI OPS DASHBOARD (PHASE 5) =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("11. AI OPS DASHBOARD (PHASE 5) TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            # Test admin access to AI Ops stats
            success, data = self.test(
                "Get AI Ops stats (admin)",
                "GET",
                "/admin/ai-ops/stats",
                200,
                token=self.admin_token
            )
            if success:
                self.log(f"✅ Admin can access AI Ops stats", Colors.GREEN)
                
                # Verify response structure
                if 'engine' in data:
                    self.log(f"  Engine: {data['engine'].get('provider')} / {data['engine'].get('model')}", Colors.BLUE)
                
                if 'agents' in data and isinstance(data['agents'], list):
                    self.log(f"✅ Found {len(data['agents'])} agents", Colors.GREEN)
                    for agent in data['agents']:
                        self.log(f"  - {agent.get('name')}: {agent.get('total')} total, {agent.get('today')} today", Colors.BLUE)
                else:
                    self.log(f"⚠️  No agents data in response", Colors.YELLOW)
                
                if 'intents' in data:
                    self.log(f"✅ Intents data present ({len(data.get('intents', []))} intents)", Colors.GREEN)
                
                if 'feed' in data:
                    self.log(f"✅ Activity feed present ({len(data.get('feed', []))} items)", Colors.GREEN)
                
                if 'series_7d' in data:
                    self.log(f"✅ 7-day series data present ({len(data.get('series_7d', []))} days)", Colors.GREEN)

        if self.customer_token:
            # Test non-admin access (should fail with 403)
            success, data = self.test(
                "Get AI Ops stats (non-admin, should fail 403)",
                "GET",
                "/admin/ai-ops/stats",
                403,
                token=self.customer_token
            )
            if success:
                self.log(f"✅ Non-admin correctly blocked from AI Ops", Colors.GREEN)

        # ===== 12. PHASE 7 SOURCING TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("12. PHASE 7 SOURCING TESTS (ADMIN ONLY)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            # Test sourcing status
            success, data = self.test(
                "Get sourcing status (admin)",
                "GET",
                "/admin/sourcing/status",
                200,
                token=self.admin_token
            )
            if success:
                self.log(f"✅ Admin can access sourcing status", Colors.GREEN)
                if data.get('getszy_source', {}).get('enabled'):
                    self.log(f"  ✅ Getszy Source: enabled", Colors.GREEN)
                if not data.get('cj_dropshipping', {}).get('enabled'):
                    self.log(f"  ✅ CJ Dropshipping: disabled (expected)", Colors.GREEN)
                if not data.get('shiprocket', {}).get('enabled'):
                    self.log(f"  ✅ Shiprocket: disabled (expected)", Colors.GREEN)

            # Test markup check - physical product (40% margin)
            success, data = self.test(
                "Markup check - physical product (40% margin)",
                "POST",
                "/admin/sourcing/markup/check",
                200,
                data={"cost_price": 100, "is_digital": False},
                token=self.admin_token
            )
            if success:
                suggested = data.get('suggested_price', 0)
                margin = data.get('margin_pct', 0)
                if margin >= 40:
                    self.log(f"✅ Physical margin enforced: {margin}% (cost=100, sell={suggested})", Colors.GREEN)
                else:
                    self.log(f"❌ Physical margin too low: {margin}% (expected >= 40%)", Colors.RED)

            # Test markup check - digital product (70%+ margin)
            success, data = self.test(
                "Markup check - digital product (70%+ margin)",
                "POST",
                "/admin/sourcing/markup/check",
                200,
                data={"cost_price": 100, "is_digital": True},
                token=self.admin_token
            )
            if success:
                suggested = data.get('suggested_price', 0)
                margin = data.get('margin_pct', 0)
                if margin >= 70:
                    self.log(f"✅ Digital margin enforced: {margin}% (cost=100, sell={suggested})", Colors.GREEN)
                else:
                    self.log(f"❌ Digital margin too low: {margin}% (expected >= 70%)", Colors.RED)

            # Test trending scan (may take 8-15 seconds due to LLM)
            self.log(f"\n⏳ Scanning trending products (may take 8-15 seconds)...", Colors.YELLOW)
            success, data = self.test(
                "Scan trending products (limit=12)",
                "POST",
                "/admin/sourcing/trending/scan?limit=12",
                200,
                token=self.admin_token
            )
            if success:
                items = data.get('items', [])
                count = data.get('count', 0)
                if count == 12:
                    self.log(f"✅ Trending scan returned 12 items", Colors.GREEN)
                    # Check first item structure
                    if items:
                        item = items[0]
                        if all(k in item for k in ['title', 'cost_price', 'suggested_price', 'margin_pct']):
                            self.log(f"  ✅ Item structure valid", Colors.GREEN)
                            if item['margin_pct'] >= 40:
                                self.log(f"  ✅ Margin enforced: {item['margin_pct']}%", Colors.GREEN)
                            else:
                                self.log(f"  ⚠️  Margin: {item['margin_pct']}% (expected >= 40%)", Colors.YELLOW)
                else:
                    self.log(f"⚠️  Expected 12 items, got {count}", Colors.YELLOW)

            # Test get cached trending
            success, data = self.test(
                "Get cached trending products",
                "GET",
                "/admin/sourcing/trending",
                200,
                token=self.admin_token
            )
            if success:
                items = data.get('items', [])
                if len(items) > 0:
                    self.log(f"✅ Cached trending returned {len(items)} items", Colors.GREEN)

            # Test import product
            success, data = self.test(
                "Import trending product",
                "POST",
                "/admin/sourcing/import",
                200,
                data={
                    "title": "Test Product Import",
                    "cost_price": 100,
                    "suggested_price": 149,
                    "category": "fashion",
                    "hero_image": "https://example.com/image.jpg",
                    "audience": "women",
                    "niche": "test-niche"
                },
                token=self.admin_token
            )
            if success:
                product = data.get('product', {})
                margin = data.get('margin', {})
                if product.get('id'):
                    self.log(f"✅ Product imported: {product.get('name')}", Colors.GREEN)
                    if margin.get('margin_pct', 0) >= 40:
                        self.log(f"  ✅ Margin enforced: {margin.get('margin_pct')}%", Colors.GREEN)

        # Test non-admin access (should fail with 403)
        if self.customer_token:
            success, data = self.test(
                "Sourcing status (non-admin, should fail 403)",
                "GET",
                "/admin/sourcing/status",
                403,
                token=self.customer_token
            )
            if success:
                self.log(f"✅ Non-admin correctly blocked from sourcing", Colors.GREEN)

        # ===== 13. PHASE 8 MEDIA STUDIO TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("13. PHASE 8 MEDIA STUDIO TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.customer_token:
            # Test media tools list
            success, data = self.test(
                "Get media tools list",
                "GET",
                "/media/tools",
                200,
                token=self.customer_token
            )
            if success:
                tools = data.get('tools', [])
                if len(tools) == 5:
                    self.log(f"✅ Found 5 media tools", Colors.GREEN)
                    for tool in tools:
                        status = tool.get('status')
                        badge = tool.get('badge')
                        name = tool.get('name')
                        if tool['id'] in ['image', 'logo']:
                            if status == 'live' and badge == 'Free':
                                self.log(f"  ✅ {name}: live, Free badge", Colors.GREEN)
                            else:
                                self.log(f"  ⚠️  {name}: status={status}, badge={badge}", Colors.YELLOW)
                        elif tool['id'] in ['voice', 'video', 'mirror']:
                            if status == 'pending':
                                self.log(f"  ✅ {name}: pending (expected)", Colors.GREEN)
                            else:
                                self.log(f"  ⚠️  {name}: status={status} (expected pending)", Colors.YELLOW)
                else:
                    self.log(f"⚠️  Expected 5 tools, found {len(tools)}", Colors.YELLOW)

            # Test media quota
            success, data = self.test(
                "Get media quota",
                "GET",
                "/media/quota",
                200,
                token=self.customer_token
            )
            if success:
                plan = data.get('plan')
                quota = data.get('quota', {})
                self.log(f"✅ Media quota retrieved for plan: {plan}", Colors.GREEN)
                self.log(f"  Images: {quota.get('images')}, Logos: {quota.get('logos')}", Colors.BLUE)

            # Test image generation
            success, data = self.test(
                "Generate image (Pollinations)",
                "POST",
                "/media/image",
                200,
                data={
                    "prompt": "A beautiful sunset over mountains",
                    "style": "photoreal",
                    "width": 1024,
                    "height": 1024
                },
                token=self.customer_token
            )
            if success:
                if data.get('id') and data.get('url'):
                    self.log(f"✅ Image generated: {data.get('id')}", Colors.GREEN)
                    url = data.get('url', '')
                    if 'pollinations.ai' in url:
                        self.log(f"  ✅ URL is Pollinations pattern", Colors.GREEN)
                    else:
                        self.log(f"  ⚠️  URL pattern: {url[:50]}...", Colors.YELLOW)

            # Test logo generation
            success, data = self.test(
                "Generate logo (4 variants)",
                "POST",
                "/media/logo",
                200,
                data={
                    "brand_name": "TestBrand",
                    "tagline": "Innovation First",
                    "style": "minimal",
                    "palette": "monochrome"
                },
                token=self.customer_token
            )
            if success:
                variants = data.get('variants', [])
                if len(variants) == 4:
                    self.log(f"✅ Logo generated with 4 variants", Colors.GREEN)
                else:
                    self.log(f"⚠️  Expected 4 variants, got {len(variants)}", Colors.YELLOW)

            # Test voice generation (should return pending_provider)
            success, data = self.test(
                "Generate voice (should return pending_provider)",
                "POST",
                "/media/voice",
                200,
                data={
                    "text": "Hello, this is a test voice generation",
                    "voice": "female-warm"
                },
                token=self.customer_token
            )
            if success:
                if data.get('status') == 'pending_provider':
                    self.log(f"✅ Voice returns 'pending_provider' (expected)", Colors.GREEN)
                    self.log(f"  Message: {data.get('message')}", Colors.BLUE)
                else:
                    self.log(f"⚠️  Voice status: {data.get('status')} (expected pending_provider)", Colors.YELLOW)

            # Test video generation (should return pending_provider)
            success, data = self.test(
                "Generate video (should return pending_provider)",
                "POST",
                "/media/video",
                200,
                data={
                    "prompt": "A cat playing with a ball",
                    "duration_seconds": 5,
                    "aspect": "16:9"
                },
                token=self.customer_token
            )
            if success:
                if data.get('status') == 'pending_provider':
                    self.log(f"✅ Video returns 'pending_provider' (expected)", Colors.GREEN)
                else:
                    self.log(f"⚠️  Video status: {data.get('status')} (expected pending_provider)", Colors.YELLOW)

            # Test media history
            success, data = self.test(
                "Get media history",
                "GET",
                "/media/history",
                200,
                token=self.customer_token
            )
            if success:
                items = data.get('items', [])
                self.log(f"✅ Media history retrieved: {len(items)} items", Colors.GREEN)

        # Test quota enforcement (create fresh user and hit limit)
        timestamp4 = datetime.now().strftime("%H%M%S%f")
        fresh_email4 = f"quota-test-{timestamp4}@example.com"
        success, data = self.test(
            "Create fresh user for quota test",
            "POST",
            "/auth/signup",
            200,
            data={
                "name": "Quota Test User",
                "email": fresh_email4,
                "password": "Test@123",
                "phone": "6666666666"
            }
        )
        fresh_token4 = None
        if success and 'token' in data:
            fresh_token4 = data['token']
            self.log(f"✅ Fresh user created: {fresh_email4}", Colors.GREEN)

        if fresh_token4:
            # Generate 5 images (free plan limit)
            self.log(f"\n⏳ Testing quota enforcement (generating 5 images)...", Colors.YELLOW)
            for i in range(5):
                success, data = self.test(
                    f"Generate image {i+1}/5",
                    "POST",
                    "/media/image",
                    200,
                    data={"prompt": f"Test image {i+1}", "style": "photoreal"},
                    token=fresh_token4
                )
                if not success:
                    self.log(f"⚠️  Image {i+1} failed", Colors.YELLOW)
                    break

            # Try 6th image (should fail with 402)
            success, data = self.test(
                "Generate 6th image (should fail 402)",
                "POST",
                "/media/image",
                402,
                data={"prompt": "This should fail", "style": "photoreal"},
                token=fresh_token4
            )
            if success:
                self.log(f"✅ Quota enforcement working (6th image blocked)", Colors.GREEN)

        # ===== 14. PHASE 9 DEPLOY DASHBOARD TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("14. PHASE 9 DEPLOY DASHBOARD TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            # Test deploy status
            success, data = self.test(
                "Get deploy status (admin)",
                "GET",
                "/admin/deploy/status",
                200,
                token=self.admin_token
            )
            if success:
                github = data.get('github', {})
                webhook = data.get('webhook', {})
                if github.get('configured'):
                    self.log(f"✅ GitHub configured: repo={github.get('repo')}", Colors.GREEN)
                    token_preview = github.get('token_preview', '')
                    if token_preview and '...' in token_preview:
                        self.log(f"  ✅ Token redacted: {token_preview}", Colors.GREEN)
                    else:
                        self.log(f"  ⚠️  Token preview: {token_preview}", Colors.YELLOW)
                else:
                    self.log(f"⚠️  GitHub not configured", Colors.YELLOW)
                
                if not webhook.get('configured'):
                    self.log(f"✅ Webhook not configured (expected)", Colors.GREEN)
                else:
                    self.log(f"⚠️  Webhook configured: {webhook.get('url')}", Colors.YELLOW)

            # Test agent swarm build
            self.log(f"\n⏳ Running agent swarm (may take 15-30 seconds)...", Colors.YELLOW)
            success, data = self.test(
                "Run agent swarm build",
                "POST",
                "/admin/deploy/build",
                200,
                data={
                    "brief": "Add a simple contact form to the homepage",
                    "target": "page",
                    "autopush": False
                },
                token=self.admin_token
            )
            job_id = None
            if success:
                job_id = data.get('id')
                agents = data.get('agents', {})
                if job_id:
                    self.log(f"✅ Agent swarm completed: job_id={job_id}", Colors.GREEN)
                
                # Check all 4 agents
                required_agents = ['planner', 'designer', 'coder', 'reviewer']
                for agent in required_agents:
                    if agent in agents and agents[agent]:
                        self.log(f"  ✅ {agent.capitalize()}: {len(agents[agent])} chars", Colors.GREEN)
                    else:
                        self.log(f"  ❌ {agent.capitalize()}: missing or empty", Colors.RED)

            # Test get jobs list
            success, data = self.test(
                "Get deploy jobs list",
                "GET",
                "/admin/deploy/jobs",
                200,
                token=self.admin_token
            )
            if success:
                items = data.get('items', [])
                if len(items) > 0:
                    self.log(f"✅ Found {len(items)} deploy jobs", Colors.GREEN)
                else:
                    self.log(f"⚠️  No deploy jobs found", Colors.YELLOW)

            # Test push to GitHub (if job_id exists)
            if job_id:
                success, data = self.test(
                    "Push job to GitHub",
                    "POST",
                    f"/admin/deploy/{job_id}/push",
                    200,
                    token=self.admin_token
                )
                if success:
                    if data.get('ok'):
                        self.log(f"✅ GitHub push succeeded: commit_sha={data.get('commit_sha', '')[:8]}", Colors.GREEN)
                    else:
                        # Dry run or error is also acceptable
                        mode = data.get('mode', 'unknown')
                        message = data.get('message', '')
                        self.log(f"  Mode: {mode}, Message: {message[:100]}", Colors.BLUE)

                # Test webhook trigger (should return 'not configured')
                success, data = self.test(
                    "Trigger webhook (should return not configured)",
                    "POST",
                    f"/admin/deploy/{job_id}/webhook",
                    200,
                    token=self.admin_token
                )
                if success:
                    if not data.get('ok') and 'not configured' in data.get('message', '').lower():
                        self.log(f"✅ Webhook correctly returns 'not configured'", Colors.GREEN)
                    else:
                        self.log(f"⚠️  Webhook response: {data}", Colors.YELLOW)

        # Test non-admin access to deploy endpoints (should fail with 403)
        if self.customer_token:
            success, data = self.test(
                "Deploy status (non-admin, should fail 403)",
                "GET",
                "/admin/deploy/status",
                403,
                token=self.customer_token
            )
            if success:
                self.log(f"✅ Non-admin correctly blocked from deploy dashboard", Colors.GREEN)

        # ===== 15. MIRROR AI TRY-ON TESTS =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("15. MIRROR AI TRY-ON TESTS", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.customer_token:
            # Test try-on generation
            success, data = self.test(
                "Generate Mirror AI try-on",
                "POST",
                "/media/tryon",
                200,
                data={
                    "product_id": "test-product-123",
                    "product_name": "Ethnic kurti set",
                    "setting": "studio"
                },
                token=self.customer_token
            )
            if success:
                if data.get('id') and data.get('url') and data.get('kind') == 'tryon':
                    self.log(f"✅ Try-on generated: {data.get('id')}", Colors.GREEN)
                    url = data.get('url', '')
                    if 'pollinations.ai' in url or '/api/media/file/' in url:
                        self.log(f"  ✅ URL is valid pattern", Colors.GREEN)
                    else:
                        self.log(f"  ⚠️  URL pattern: {url[:50]}...", Colors.YELLOW)
                else:
                    self.log(f"⚠️  Try-on response incomplete: {data}", Colors.YELLOW)

        # Test quota enforcement for Mirror AI (free user should get 402)
        timestamp5 = datetime.now().strftime("%H%M%S%f")
        fresh_email5 = f"mirror-test-{timestamp5}@example.com"
        success, data = self.test(
            "Create fresh user for Mirror AI quota test",
            "POST",
            "/auth/signup",
            200,
            data={
                "name": "Mirror Test User",
                "email": fresh_email5,
                "password": "Test@123",
                "phone": "5555555555"
            }
        )
        fresh_token5 = None
        if success and 'token' in data:
            fresh_token5 = data['token']
            self.log(f"✅ Fresh user created: {fresh_email5}", Colors.GREEN)

        if fresh_token5:
            # Free user should get 402 (mirror quota is 0 for free plan)
            success, data = self.test(
                "Try-on as free user (should fail 402)",
                "POST",
                "/media/tryon",
                402,
                data={
                    "product_id": "test-product-456",
                    "product_name": "Test product",
                    "setting": "outdoor"
                },
                token=fresh_token5
            )
            if success:
                self.log(f"✅ Mirror AI quota enforcement working (free user blocked)", Colors.GREEN)

        # ===== 16. TRENDING IMAGES BUG FIX VERIFICATION =====
        self.log("\n" + "=" * 80, Colors.BLUE)
        self.log("16. TRENDING IMAGES BUG FIX VERIFICATION (CRITICAL)", Colors.BLUE)
        self.log("=" * 80, Colors.BLUE)

        if self.admin_token:
            # Test GET /admin/sourcing/trending - verify NO picsum URLs
            success, data = self.test(
                "Get trending products (verify NO picsum URLs)",
                "GET",
                "/admin/sourcing/trending",
                200,
                token=self.admin_token
            )
            if success:
                items = data.get('items', [])
                picsum_found = False
                pollinations_count = 0
                cached_count = 0
                
                for item in items:
                    hero_image = item.get('hero_image', '')
                    if 'picsum.photos' in hero_image:
                        picsum_found = True
                        self.log(f"❌ CRITICAL BUG: Picsum URL found in item '{item.get('title')}': {hero_image}", Colors.RED)
                    elif 'pollinations.ai' in hero_image:
                        pollinations_count += 1
                        # Check if niche is in URL
                        niche = item.get('niche', '').lower()
                        if niche and niche.replace(' ', '%20') not in hero_image and niche.replace(' ', '+') not in hero_image:
                            self.log(f"⚠️  Pollinations URL may not contain niche '{niche}': {hero_image[:80]}...", Colors.YELLOW)
                    elif '/api/media/file/' in hero_image:
                        cached_count += 1
                
                if not picsum_found:
                    self.log(f"✅ CRITICAL BUG FIXED: NO picsum URLs found in {len(items)} items", Colors.GREEN)
                    self.log(f"  Pollinations URLs: {pollinations_count}, Cached URLs: {cached_count}", Colors.BLUE)
                else:
                    self.log(f"❌ CRITICAL BUG NOT FIXED: Picsum URLs still present", Colors.RED)

            # Test POST /admin/sourcing/trending/scan - verify NO picsum URLs
            self.log(f"\n⏳ Scanning trending products to verify bug fix (may take 8-15 seconds)...", Colors.YELLOW)
            success, data = self.test(
                "Scan trending products (verify NO picsum URLs)",
                "POST",
                "/admin/sourcing/trending/scan?limit=6",
                200,
                token=self.admin_token
            )
            if success:
                items = data.get('items', [])
                picsum_found = False
                pollinations_count = 0
                cached_count = 0
                
                for item in items:
                    hero_image = item.get('hero_image', '')
                    if 'picsum.photos' in hero_image:
                        picsum_found = True
                        self.log(f"❌ CRITICAL BUG: Picsum URL found in scanned item '{item.get('title')}': {hero_image}", Colors.RED)
                    elif 'pollinations.ai' in hero_image:
                        pollinations_count += 1
                    elif '/api/media/file/' in hero_image:
                        cached_count += 1
                
                if not picsum_found:
                    self.log(f"✅ CRITICAL BUG FIXED: NO picsum URLs in scan results ({len(items)} items)", Colors.GREEN)
                    self.log(f"  Pollinations URLs: {pollinations_count}, Cached URLs: {cached_count}", Colors.BLUE)
                else:
                    self.log(f"❌ CRITICAL BUG NOT FIXED: Picsum URLs still in scan results", Colors.RED)

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
