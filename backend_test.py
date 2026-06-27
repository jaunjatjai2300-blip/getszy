"""
Comprehensive backend API testing for getszy.com
Tests all endpoints including the HERO feature: AI Admin Chat
"""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "https://getszy-all-in-one.preview.emergentagent.com/api"

class GetszyAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.customer_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_product_id = None
        self.test_order_id = None
        self.test_supplier_id = None
        
    def log(self, emoji, message):
        print(f"{emoji} {message}")
        
    def test(self, name, method, endpoint, expected_status, data=None, token=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        self.tests_run += 1
        self.log("🔍", f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log("✅", f"PASSED - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log("❌", f"FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log("📄", f"Response: {response.text[:200]}")
                except:
                    pass
                return False, {}
        except Exception as e:
            self.log("❌", f"FAILED - Error: {str(e)}")
            return False, {}
    
    def test_health(self):
        """Test health endpoint"""
        self.log("🏥", "=== TESTING HEALTH ===")
        success, data = self.test("Health Check", "GET", "health", 200)
        if success and data.get('status') == 'ok':
            self.log("✅", "Health check passed")
            return True
        return False
    
    def test_categories(self):
        """Test categories endpoint"""
        self.log("📂", "=== TESTING CATEGORIES ===")
        success, data = self.test("Get Categories", "GET", "categories", 200)
        if success:
            count = len(data)
            self.log("📊", f"Found {count} categories")
            if count == 7:
                self.log("✅", "Expected 7 categories - PASSED")
                return True
            else:
                self.log("❌", f"Expected 7 categories, got {count}")
        return False
    
    def test_products(self):
        """Test products endpoints"""
        self.log("🛍️", "=== TESTING PRODUCTS ===")
        
        # Get all products
        success, data = self.test("Get All Products", "GET", "products", 200)
        if not success:
            return False
        
        count = len(data)
        self.log("📊", f"Found {count} products")
        if count != 14:
            self.log("⚠️", f"Expected 14 products, got {count}")
        
        # Store a product ID for later tests
        if data:
            self.test_product_id = data[0]['id']
        
        # Filter by category=jewellery
        success, jewellery = self.test("Filter by category=jewellery", "GET", "products", 200, 
                                       params={'category': 'jewellery'})
        if success:
            self.log("📊", f"Found {len(jewellery)} jewellery products")
        
        # Search for dress
        success, dress_results = self.test("Search for 'dress'", "GET", "products", 200,
                                          params={'search': 'dress'})
        if success:
            self.log("📊", f"Found {len(dress_results)} products matching 'dress'")
        
        # Filter featured products
        success, featured = self.test("Filter featured=true", "GET", "products", 200,
                                     params={'featured': 'true'})
        if success:
            self.log("📊", f"Found {len(featured)} featured products")
        
        return True
    
    def test_auth_signup(self):
        """Test signup endpoint"""
        self.log("👤", "=== TESTING AUTH - SIGNUP ===")
        timestamp = datetime.now().strftime("%H%M%S")
        email = f"test{timestamp}@getszy.com"
        
        success, data = self.test("Signup New Customer", "POST", "auth/signup", 200,
                                 data={
                                     "name": f"Test User {timestamp}",
                                     "email": email,
                                     "password": "Test@123"
                                 })
        if success and data.get('token'):
            self.log("✅", "Signup successful, JWT token received")
            
            # Test /auth/me with new token
            success2, user_data = self.test("Get Current User", "GET", "auth/me", 200,
                                           token=data['token'])
            if success2:
                self.log("✅", f"User data retrieved: {user_data.get('email')}")
                return True
        return False
    
    def test_auth_login(self):
        """Test login endpoints"""
        self.log("🔐", "=== TESTING AUTH - LOGIN ===")
        
        # Login as admin
        success, data = self.test("Login as Admin", "POST", "auth/login", 200,
                                 data={
                                     "email": "admin@getszy.com",
                                     "password": "Admin@123"
                                 })
        if success and data.get('token'):
            self.admin_token = data['token']
            role = data.get('user', {}).get('role')
            if role == 'admin':
                self.log("✅", "Admin login successful, role verified")
            else:
                self.log("❌", f"Expected admin role, got {role}")
                return False
        else:
            self.log("❌", "Admin login failed")
            return False
        
        # Login as customer
        success, data = self.test("Login as Customer", "POST", "auth/login", 200,
                                 data={
                                     "email": "customer@getszy.com",
                                     "password": "Demo@123"
                                 })
        if success and data.get('token'):
            self.customer_token = data['token']
            self.log("✅", "Customer login successful")
            return True
        return False
    
    def test_customer_flow(self):
        """Test complete customer flow: cart + checkout"""
        self.log("🛒", "=== TESTING CUSTOMER FLOW ===")
        
        if not self.customer_token:
            self.log("❌", "Customer token not available")
            return False
        
        # Get cart (should be empty initially)
        success, cart = self.test("Get Cart", "GET", "cart", 200, token=self.customer_token)
        if not success:
            return False
        
        # Add product to cart
        if not self.test_product_id:
            self.log("❌", "No product ID available")
            return False
        
        success, _ = self.test("Add to Cart", "POST", "cart/add", 200,
                              data={"product_id": self.test_product_id, "quantity": 2},
                              token=self.customer_token)
        if not success:
            return False
        
        # Get cart again (should have items)
        success, cart = self.test("Get Cart with Items", "GET", "cart", 200, 
                                 token=self.customer_token)
        if success:
            count = cart.get('count', 0)
            self.log("📊", f"Cart has {count} items")
        
        # Checkout
        success, order = self.test("Checkout Order", "POST", "orders/checkout", 200,
                                  data={
                                      "address": {
                                          "full_name": "Test Customer",
                                          "phone": "+91-9999999999",
                                          "line1": "123 Test Street",
                                          "line2": "Apt 4B",
                                          "city": "Mumbai",
                                          "state": "Maharashtra",
                                          "pincode": "400001",
                                          "country": "India"
                                      },
                                      "notes": "Test order"
                                  },
                                  token=self.customer_token)
        if success:
            self.test_order_id = order.get('id')
            order_number = order.get('order_number')
            self.log("✅", f"Order placed successfully: {order_number}")
        else:
            return False
        
        # Get my orders
        success, orders = self.test("Get My Orders", "GET", "orders/mine", 200,
                                   token=self.customer_token)
        if success:
            self.log("📊", f"Found {len(orders)} orders")
            return True
        return False
    
    def test_admin_stats(self):
        """Test admin stats endpoint"""
        self.log("📊", "=== TESTING ADMIN STATS ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        success, stats = self.test("Get Admin Stats (month)", "GET", "admin/stats", 200,
                                  params={'range': 'month'},
                                  token=self.admin_token)
        if success:
            if 'series_7d' in stats:
                self.log("✅", "Stats with series_7d received")
                self.log("📊", f"Revenue: ₹{stats.get('revenue', 0)}, Orders: {stats.get('orders_count', 0)}")
                return True
            else:
                self.log("❌", "series_7d not found in stats")
        return False
    
    def test_admin_orders(self):
        """Test admin orders endpoints"""
        self.log("📦", "=== TESTING ADMIN ORDERS ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        # Get all orders
        success, orders = self.test("Get All Orders", "GET", "admin/orders", 200,
                                   token=self.admin_token)
        if not success:
            return False
        
        self.log("📊", f"Found {len(orders)} orders")
        
        # Update order status
        if self.test_order_id:
            success, updated = self.test("Update Order Status", "PUT", 
                                        f"admin/orders/{self.test_order_id}/status", 200,
                                        data={
                                            "status": "shipped",
                                            "tracking_number": "TRACK123456"
                                        },
                                        token=self.admin_token)
            if success:
                self.log("✅", f"Order status updated to: {updated.get('status')}")
                return True
        return False
    
    def test_admin_customers(self):
        """Test admin customers endpoint"""
        self.log("👥", "=== TESTING ADMIN CUSTOMERS ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        success, customers = self.test("Get Customers", "GET", "admin/customers", 200,
                                      token=self.admin_token)
        if success:
            self.log("📊", f"Found {len(customers)} customers")
            return True
        return False
    
    def test_admin_product_crud(self):
        """Test admin product CRUD operations"""
        self.log("🔧", "=== TESTING ADMIN PRODUCT CRUD ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        # Create product
        timestamp = datetime.now().strftime("%H%M%S")
        success, product = self.test("Create Product", "POST", "admin/products", 200,
                                    data={
                                        "name": f"Test Product {timestamp}",
                                        "description": "Test description",
                                        "images": ["https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600"],
                                        "price": 999,
                                        "cost_price": 400,
                                        "stock": 10,
                                        "category": "fashion",
                                        "supplier": "Test Supplier"
                                    },
                                    token=self.admin_token)
        if not success:
            return False
        
        created_id = product.get('id')
        self.log("✅", f"Product created with ID: {created_id}")
        
        # Update product
        success, updated = self.test("Update Product", "PUT", f"admin/products/{created_id}", 200,
                                    data={"price": 1099, "stock": 15},
                                    token=self.admin_token)
        if success:
            self.log("✅", f"Product updated - Price: {updated.get('price')}, Stock: {updated.get('stock')}")
        
        # Delete product
        success, _ = self.test("Delete Product", "DELETE", f"admin/products/{created_id}", 200,
                              token=self.admin_token)
        if success:
            self.log("✅", "Product deleted successfully")
            return True
        return False
    
    def test_admin_supplier_crud(self):
        """Test admin supplier CRUD operations"""
        self.log("🏭", "=== TESTING ADMIN SUPPLIER CRUD ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        # Create supplier
        timestamp = datetime.now().strftime("%H%M%S")
        success, supplier = self.test("Create Supplier", "POST", "admin/suppliers", 200,
                                     data={
                                         "name": f"Test Supplier {timestamp}",
                                         "contact": "+91-9999000011",
                                         "notes": "Test supplier"
                                     },
                                     token=self.admin_token)
        if not success:
            return False
        
        self.test_supplier_id = supplier.get('id')
        self.log("✅", f"Supplier created with ID: {self.test_supplier_id}")
        
        # Update supplier
        success, updated = self.test("Update Supplier", "PUT", f"admin/suppliers/{self.test_supplier_id}", 200,
                                    data={"contact": "+91-8888000011"},
                                    token=self.admin_token)
        if success:
            self.log("✅", f"Supplier updated - Contact: {updated.get('contact')}")
        
        # Get all suppliers
        success, suppliers = self.test("Get All Suppliers", "GET", "admin/suppliers", 200,
                                      token=self.admin_token)
        if success:
            self.log("📊", f"Found {len(suppliers)} suppliers")
            return True
        return False
    
    def test_ai_admin_chat(self):
        """Test AI Admin Chat - THE HERO FEATURE (Phase 1 intents)"""
        self.log("🤖", "=== TESTING AI ADMIN CHAT (PHASE 1 INTENTS) ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        test_commands = [
            {
                "name": "Add Product via AI",
                "message": "Add product Test Dress 1299 in fashion, supplier Surat Textiles, cost 500, stock 20",
                "expected_intent": "add_product",
                "check_db": True
            },
            {
                "name": "Show Today's Orders",
                "message": "Show today's orders",
                "expected_intent": "list_orders"
            },
            {
                "name": "Show Month Revenue Stats",
                "message": "Show this month revenue stats",
                "expected_intent": "show_stats",
                "check_revenue": True
            },
            {
                "name": "Show Low Stock Products",
                "message": "Show low stock products",
                "expected_intent": "low_stock"
            },
            {
                "name": "Add Supplier via AI",
                "message": "Add supplier TestSup1, contact +91-9999000011",
                "expected_intent": "add_supplier"
            },
            {
                "name": "List Jewellery Products",
                "message": "List jewellery products",
                "expected_intent": "list_products"
            },
            {
                "name": "Reject Dangerous Command",
                "message": "Delete all products",
                "expected_intent": "reject"
            },
            {
                "name": "Clarify Incomplete Command",
                "message": "Add a product",
                "expected_intent": "clarify"
            }
        ]
        
        passed = 0
        for i, cmd in enumerate(test_commands, 1):
            self.log("🎯", f"\n[{i}/8] Testing: {cmd['name']}")
            self.log("💬", f"Command: '{cmd['message']}'")
            
            success, response = self.test(
                f"AI Chat Command {i}",
                "POST",
                "admin/chat",
                200,
                data={"message": cmd['message']},
                token=self.admin_token
            )
            
            if success:
                intent = response.get('intent')
                result = response.get('result', {})
                result_ok = result.get('ok', False)
                
                self.log("📋", f"Intent: {intent}, Result OK: {result_ok}")
                
                # Check intent matches
                if intent == cmd['expected_intent']:
                    self.log("✅", f"Intent matches expected: {intent}")
                    
                    # Additional checks
                    if cmd.get('check_db') and result_ok:
                        product_data = result.get('data', {})
                        if product_data.get('name'):
                            self.log("✅", f"Product created in DB: {product_data.get('name')}")
                            passed += 1
                        else:
                            self.log("⚠️", "Product data not found in result")
                    elif cmd.get('check_revenue') and result_ok:
                        stats_data = result.get('data', {})
                        if 'revenue' in stats_data:
                            self.log("✅", f"Stats with revenue: ₹{stats_data.get('revenue')}")
                            passed += 1
                        else:
                            self.log("⚠️", "Revenue field not found in stats")
                    else:
                        if result_ok or intent in ['reject', 'clarify']:
                            passed += 1
                else:
                    self.log("❌", f"Intent mismatch - Expected: {cmd['expected_intent']}, Got: {intent}")
            else:
                self.log("❌", f"API call failed for command {i}")
        
        self.log("📊", f"\n=== AI CHAT PHASE 1 RESULTS: {passed}/8 commands passed ===")
        
        # Test chat history endpoints
        success, sessions = self.test("Get Chat Sessions", "GET", "admin/chat/sessions", 200,
                                     token=self.admin_token)
        if success:
            self.log("✅", f"Chat sessions retrieved: {len(sessions)} sessions")
        
        if sessions:
            session_id = sessions[0].get('session_id')
            success, history = self.test("Get Chat History", "GET", "admin/chat/history", 200,
                                        params={'session_id': session_id},
                                        token=self.admin_token)
            if success:
                self.log("✅", f"Chat history retrieved: {len(history)} messages")
        
        return passed >= 6  # At least 6/8 should pass
    
    def test_courses_catalog(self):
        """Test courses catalog endpoints (Phase 2)"""
        self.log("🎓", "=== TESTING COURSES CATALOG (PHASE 2) ===")
        
        # Get all courses
        success, courses = self.test("Get All Courses", "GET", "courses", 200)
        if not success:
            return False
        
        count = len(courses)
        self.log("📊", f"Found {count} courses")
        if count != 4:
            self.log("⚠️", f"Expected 4 courses, got {count}")
        
        # Check course slugs
        expected_slugs = ['ai-foundations-for-women', 'chatgpt-and-prompting-mastery', 
                         'build-income-with-ai-no-code', 'become-ai-independent-career-path']
        found_slugs = [c['slug'] for c in courses]
        for slug in expected_slugs:
            if slug in found_slugs:
                self.log("✅", f"Found course: {slug}")
            else:
                self.log("❌", f"Missing course: {slug}")
        
        # Filter by level=Beginner
        success, beginner = self.test("Filter by level=Beginner", "GET", "courses", 200,
                                     params={'level': 'Beginner'})
        if success:
            self.log("📊", f"Found {len(beginner)} Beginner courses")
            if len(beginner) == 1:
                self.log("✅", "Expected 1 Beginner course - PASSED")
        
        # Filter by featured=true
        success, featured = self.test("Filter by featured=true", "GET", "courses", 200,
                                     params={'featured': 'true'})
        if success:
            self.log("📊", f"Found {len(featured)} featured courses")
            if len(featured) == 3:
                self.log("✅", "Expected 3 featured courses - PASSED")
        
        # Get specific course with modules and lessons
        success, course = self.test("Get Course Detail (ai-foundations-for-women)", "GET", 
                                   "courses/ai-foundations-for-women", 200)
        if success:
            modules = course.get('modules', [])
            total_lessons = course.get('total_lessons', 0)
            self.log("📊", f"Course has {len(modules)} modules, {total_lessons} lessons")
            if total_lessons == 5:
                self.log("✅", "Expected 5 lessons - PASSED")
            else:
                self.log("⚠️", f"Expected 5 lessons, got {total_lessons}")
            return True
        return False
    
    def test_enrollment_flow(self):
        """Test course enrollment flow (Phase 2)"""
        self.log("📝", "=== TESTING ENROLLMENT FLOW (PHASE 2) ===")
        
        if not self.customer_token:
            self.log("❌", "Customer token not available")
            return False
        
        course_slug = 'ai-foundations-for-women'
        
        # Enroll in course
        success, enrollment = self.test("Enroll in Course", "POST", 
                                       f"courses/{course_slug}/enroll", 200,
                                       token=self.customer_token)
        if not success:
            return False
        
        self.log("✅", f"Enrolled in course: {enrollment.get('course_slug')}")
        
        # Get my enrollments
        success, enrollments = self.test("Get My Enrollments", "GET", "me/enrollments", 200,
                                        token=self.customer_token)
        if success:
            self.log("📊", f"Found {len(enrollments)} enrollments")
            # Check if course details are enriched
            if enrollments and enrollments[0].get('course'):
                self.log("✅", "Enrollment enriched with course details")
        
        # Access learn page
        success, learn_data = self.test("Access Learn Page", "GET", 
                                       f"courses/{course_slug}/learn", 200,
                                       token=self.customer_token)
        if success:
            course = learn_data.get('course', {})
            enr = learn_data.get('enrollment', {})
            self.log("✅", f"Learn page data retrieved - Progress: {enr.get('progress', 0)*100}%")
            
            # Get first lesson ID for completion test
            modules = course.get('modules', [])
            if modules and modules[0].get('lessons'):
                first_lesson_id = modules[0]['lessons'][0]['id']
                
                # Mark lesson as complete
                success, progress = self.test("Mark Lesson Complete", "POST",
                                            f"lessons/{first_lesson_id}/complete", 200,
                                            token=self.customer_token)
                if success:
                    new_progress = progress.get('progress', 0)
                    self.log("✅", f"Lesson marked complete - Progress: {new_progress*100}%")
                    if abs(new_progress - 0.2) < 0.01:  # 1/5 = 0.2
                        self.log("✅", "Progress calculation correct (0.2 for 1/5 lessons)")
                        return True
        return False
    
    def test_ai_tutor(self):
        """Test AI Tutor endpoint (Phase 2) - may take 5-15 seconds"""
        self.log("🤖", "=== TESTING AI TUTOR (PHASE 2) ===")
        
        if not self.customer_token:
            self.log("❌", "Customer token not available")
            return False
        
        course_slug = 'ai-foundations-for-women'
        
        self.log("⏳", "Sending tutor message (may take 5-15 seconds for LLM response)...")
        
        # Test tutor with longer timeout
        url = f"{self.base_url}/courses/{course_slug}/tutor"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.customer_token}'
        }
        
        self.tests_run += 1
        try:
            response = requests.post(
                url,
                json={"message": "Explain what AI is in simple words"},
                headers=headers,
                timeout=30  # Longer timeout for LLM
            )
            
            if response.status_code == 200:
                self.tests_passed += 1
                data = response.json()
                reply = data.get('reply', '')
                session_id = data.get('session_id', '')
                
                if reply and len(reply) > 10:
                    self.log("✅", f"AI Tutor replied (length: {len(reply)} chars)")
                    self.log("💬", f"Reply preview: {reply[:100]}...")
                    if session_id:
                        self.log("✅", f"Session ID: {session_id}")
                    return True
                else:
                    self.log("❌", "AI Tutor reply too short or empty")
            else:
                self.log("❌", f"AI Tutor failed - Status: {response.status_code}")
        except Exception as e:
            self.log("❌", f"AI Tutor error: {str(e)}")
        
        return False
    
    def test_certificate(self):
        """Test certificate endpoint (Phase 2)"""
        self.log("🏆", "=== TESTING CERTIFICATE (PHASE 2) ===")
        
        if not self.customer_token:
            self.log("❌", "Customer token not available")
            return False
        
        course_slug = 'ai-foundations-for-women'
        
        # Try to get certificate (should fail since not 100% complete)
        success, data = self.test("Get Certificate (incomplete)", "GET",
                                 f"me/courses/{course_slug}/certificate", 400,
                                 token=self.customer_token)
        if success:
            self.log("✅", "Certificate correctly returns 400 when course not complete")
            return True
        return False
    
    def test_admin_courses_crud(self):
        """Test admin course CRUD operations (Phase 2)"""
        self.log("🔧", "=== TESTING ADMIN COURSES CRUD (PHASE 2) ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        # Get all courses (admin)
        success, courses = self.test("Get All Courses (Admin)", "GET", "admin/courses", 200,
                                    token=self.admin_token)
        if not success:
            return False
        
        self.log("📊", f"Admin sees {len(courses)} courses")
        
        # Create course
        timestamp = datetime.now().strftime("%H%M%S")
        success, course = self.test("Create Course", "POST", "admin/courses", 200,
                                   data={
                                       "title": f"Test Course {timestamp}",
                                       "subtitle": "Test subtitle",
                                       "description": "Test description",
                                       "level": "Intermediate",
                                       "duration_hours": 3.5,
                                       "thumbnail": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800",
                                       "outcomes": ["Learn testing", "Build confidence"],
                                       "is_featured": False
                                   },
                                   token=self.admin_token)
        if not success:
            return False
        
        created_slug = course.get('slug')
        self.log("✅", f"Course created with slug: {created_slug}")
        
        # Update course
        success, updated = self.test("Update Course", "PUT", f"admin/courses/{created_slug}", 200,
                                    data={"duration_hours": 4.0, "is_featured": True},
                                    token=self.admin_token)
        if success:
            self.log("✅", f"Course updated - Duration: {updated.get('duration_hours')}h, Featured: {updated.get('is_featured')}")
        
        # Delete course
        success, _ = self.test("Delete Course", "DELETE", f"admin/courses/{created_slug}", 200,
                              token=self.admin_token)
        if success:
            self.log("✅", "Course deleted successfully")
            return True
        return False
    
    def test_admin_lessons_crud(self):
        """Test admin lesson CRUD operations (Phase 2)"""
        self.log("📚", "=== TESTING ADMIN LESSONS CRUD (PHASE 2) ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        # Get course detail to find module_id
        success, course = self.test("Get Course for Lesson Test", "GET",
                                   "courses/ai-foundations-for-women", 200)
        if not success or not course.get('modules'):
            self.log("❌", "Could not get course modules")
            return False
        
        module_id = course['modules'][0]['id']
        
        # Create lesson
        timestamp = datetime.now().strftime("%H%M%S")
        success, lesson = self.test("Create Lesson", "POST", "admin/lessons", 200,
                                   data={
                                       "course_slug": "ai-foundations-for-women",
                                       "module_id": module_id,
                                       "title": f"Test Lesson {timestamp}",
                                       "description": "Test lesson description",
                                       "video_url": "https://www.youtube.com/embed/test",
                                       "duration_min": 15,
                                       "order": 99
                                   },
                                   token=self.admin_token)
        if not success:
            return False
        
        lesson_id = lesson.get('id')
        self.log("✅", f"Lesson created with ID: {lesson_id}")
        
        # Delete lesson
        success, _ = self.test("Delete Lesson", "DELETE", f"admin/lessons/{lesson_id}", 200,
                              token=self.admin_token)
        if success:
            self.log("✅", "Lesson deleted successfully")
            return True
        return False
    
    def test_ai_admin_chat_extended(self):
        """Test AI Admin Chat extended intents (Phase 2)"""
        self.log("🤖", "=== TESTING AI ADMIN CHAT EXTENDED INTENTS (PHASE 2) ===")
        
        if not self.admin_token:
            self.log("❌", "Admin token not available")
            return False
        
        test_commands = [
            {
                "name": "Create Course via AI",
                "message": "Create a new course called Voice AI Mastery, level Intermediate",
                "expected_intent": "create_course"
            },
            {
                "name": "List All Courses",
                "message": "List all courses",
                "expected_intent": "list_courses"
            },
            {
                "name": "Show Enrollments",
                "message": "Show enrollments for AI Foundations",
                "expected_intent": "show_enrollments"
            }
        ]
        
        passed = 0
        for i, cmd in enumerate(test_commands, 1):
            self.log("🎯", f"\n[{i}/3] Testing: {cmd['name']}")
            self.log("💬", f"Command: '{cmd['message']}'")
            
            success, response = self.test(
                f"AI Chat Extended Command {i}",
                "POST",
                "admin/chat",
                200,
                data={"message": cmd['message']},
                token=self.admin_token
            )
            
            if success:
                intent = response.get('intent')
                result = response.get('result', {})
                result_ok = result.get('ok', False)
                
                self.log("📋", f"Intent: {intent}, Result OK: {result_ok}")
                
                if intent == cmd['expected_intent']:
                    self.log("✅", f"Intent matches expected: {intent}")
                    if result_ok:
                        passed += 1
                else:
                    self.log("❌", f"Intent mismatch - Expected: {cmd['expected_intent']}, Got: {intent}")
        
        self.log("📊", f"\n=== AI CHAT EXTENDED RESULTS: {passed}/3 commands passed ===")
        return passed >= 2  # At least 2/3 should pass
    
    def run_all_tests(self):
        """Run all backend tests - Phase 1 + Phase 2"""
        self.log("🚀", "=" * 60)
        self.log("🚀", "STARTING GETSZY BACKEND API TESTS - PHASE 2")
        self.log("🚀", "=" * 60)
        
        # ===== PHASE 1 REGRESSION TESTS =====
        self.log("🔄", "\n=== PHASE 1 REGRESSION TESTS ===")
        self.test_health()
        self.test_categories()
        self.test_products()
        
        # Auth tests
        self.test_auth_signup()
        self.test_auth_login()
        
        # Customer flow
        self.test_customer_flow()
        
        # Admin tests
        self.test_admin_stats()
        self.test_admin_orders()
        self.test_admin_customers()
        self.test_admin_product_crud()
        self.test_admin_supplier_crud()
        
        # HERO FEATURE - AI Admin Chat (Phase 1 intents)
        self.test_ai_admin_chat()
        
        # ===== PHASE 2 NEW FEATURES =====
        self.log("🆕", "\n=== PHASE 2 NEW FEATURES - LEARNING ACADEMY ===")
        self.test_courses_catalog()
        self.test_enrollment_flow()
        self.test_ai_tutor()
        self.test_certificate()
        self.test_admin_courses_crud()
        self.test_admin_lessons_crud()
        self.test_ai_admin_chat_extended()
        
        # Final results
        self.log("🏁", "=" * 60)
        self.log("📊", f"FINAL RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        self.log("📊", f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        self.log("🏁", "=" * 60)
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    tester = GetszyAPITester()
    sys.exit(tester.run_all_tests())
