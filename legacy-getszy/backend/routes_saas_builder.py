import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/saas-builder', tags=['saas-builder'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


TEMPLATES = {
    'crm': {
        'name': 'CRM',
        'description': 'Customer Relationship Management with contacts, deals, pipeline, and activity tracking',
        'collections': ['contacts', 'deals', 'pipeline_stages', 'activities', 'notes', 'tags'],
        'features': ['contacts', 'deals', 'pipeline', 'activities', 'notes', 'tags', 'email_integration', 'reporting'],
        'preview_image': '/templates/crm-preview.png',
        'tech_stack': ['React', 'FastAPI', 'MongoDB', 'TailwindCSS'],
        'use_cases': ['Sales teams', 'Customer support', 'Business development'],
    },
    'erp': {
        'name': 'ERP',
        'description': 'Enterprise Resource Planning with inventory, accounting, HR, and supply chain',
        'collections': ['products', 'orders', 'invoices', 'employees', 'departments', 'suppliers', 'ledger'],
        'features': ['inventory', 'accounting', 'hr', 'procurement', 'reporting', 'audit_log', 'multi_currency'],
        'preview_image': '/templates/erp-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'PostgreSQL', 'TailwindCSS'],
        'use_cases': ['Manufacturing', 'Wholesale', 'Enterprise operations'],
    },
    'lms': {
        'name': 'LMS',
        'description': 'Learning Management System with courses, lessons, enrollments, and progress tracking',
        'collections': ['courses', 'lessons', 'modules', 'enrollments', 'progress', 'quizzes', 'certificates'],
        'features': ['courses', 'lessons', 'enrollments', 'progress_tracking', 'quizzes', 'certificates', 'video_hosting', 'discussions'],
        'preview_image': '/templates/lms-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'MongoDB', 'TailwindCSS'],
        'use_cases': ['Online education', 'Corporate training', 'Skill development'],
    },
    'hrms': {
        'name': 'HRMS',
        'description': 'Human Resource Management with employees, payroll, attendance, and performance',
        'collections': ['employees', 'departments', 'attendance', 'payroll', 'leave_requests', 'performance_reviews', 'documents'],
        'features': ['employee_management', 'attendance', 'payroll', 'leave_management', 'performance', 'onboarding', 'document_storage'],
        'preview_image': '/templates/hrms-preview.png',
        'tech_stack': ['React', 'FastAPI', 'MongoDB', 'TailwindCSS'],
        'use_cases': ['HR departments', 'Mid-size companies', 'Startups'],
    },
    'ecommerce': {
        'name': 'E-Commerce',
        'description': 'Full e-commerce with products, cart, checkout, orders, and inventory',
        'collections': ['products', 'categories', 'cart', 'orders', 'customers', 'reviews', 'coupons', 'inventory'],
        'features': ['products', 'cart', 'checkout', 'orders', 'payments', 'inventory', 'reviews', 'coupons', 'wishlists'],
        'preview_image': '/templates/ecommerce-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'MongoDB', 'Stripe'],
        'use_cases': ['Online stores', 'D2C brands', 'Marketplace sellers'],
    },
    'booking': {
        'name': 'Booking',
        'description': 'Appointment and booking system with services, slots, calendar, and payments',
        'collections': ['services', 'slots', 'appointments', 'customers', 'reviews', 'staff', 'availability'],
        'features': ['services', 'time_slots', 'appointments', 'calendar', 'payments', 'reminders', 'reviews', 'staff_management'],
        'preview_image': '/templates/booking-preview.png',
        'tech_stack': ['React', 'FastAPI', 'MongoDB', 'TailwindCSS'],
        'use_cases': ['Salons', 'Clinics', 'Consulting', 'Fitness studios'],
    },
    'marketplace': {
        'name': 'Marketplace',
        'description': 'Multi-vendor marketplace with sellers, products, orders, and payouts',
        'collections': ['sellers', 'products', 'orders', 'customers', 'payouts', 'reviews', 'categories', 'disputes'],
        'features': ['multi_vendor', 'seller_dashboard', 'products', 'orders', 'payouts', 'reviews', 'disputes', 'analytics'],
        'preview_image': '/templates/marketplace-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'MongoDB', 'Stripe'],
        'use_cases': ['Multi-seller platforms', 'Niche marketplaces', 'Service marketplaces'],
    },
    'social': {
        'name': 'Social',
        'description': 'Social platform with posts, feeds, comments, likes, and user profiles',
        'collections': ['users', 'posts', 'comments', 'likes', 'follows', 'messages', 'stories', 'notifications'],
        'features': ['posts', 'feed', 'comments', 'likes', 'follows', 'dm', 'stories', 'notifications', 'user_profiles'],
        'preview_image': '/templates/social-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'MongoDB', 'WebSockets'],
        'use_cases': ['Community platforms', 'Niche social networks', 'Internal team social'],
    },
    'portfolio': {
        'name': 'Portfolio',
        'description': 'Professional portfolio with projects, blog, testimonials, and contact',
        'collections': ['projects', 'blog_posts', 'testimonials', 'skills', 'messages', 'page_views'],
        'features': ['projects', 'blog', 'testimonials', 'contact_form', 'analytics', 'seo', 'dark_mode'],
        'preview_image': '/templates/portfolio-preview.png',
        'tech_stack': ['Next.js', 'FastAPI', 'MongoDB', 'TailwindCSS'],
        'use_cases': ['Freelancers', 'Developers', 'Designers', 'Agencies'],
    },
}

TEMPLATE_FILE_GENERATORS = {
    'crm': {
        'contacts': '''from pydantic import BaseModel
from typing import List, Optional

class Contact(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    tags: List[str] = []
    notes: str = ""
    owner_id: str
    source: Optional[str] = None
    status: str = "lead"
    created_at: str
    updated_at: str

class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    tags: List[str] = []
    notes: str = ""
    source: Optional[str] = None
    status: str = "lead"
''',
        'deals': '''from pydantic import BaseModel
from typing import Optional

class Deal(BaseModel):
    id: str
    title: str
    contact_id: str
    value: float
    currency: str = "USD"
    stage: str = "lead"
    probability: int = 10
    expected_close: Optional[str] = None
    owner_id: str
    notes: str = ""
    created_at: str
    updated_at: str

class DealCreate(BaseModel):
    title: str
    contact_id: str
    value: float
    currency: str = "USD"
    stage: str = "lead"
    probability: int = 10
    expected_close: Optional[str] = None
    notes: str = ""
''',
        'pipeline_stages': '''from pydantic import BaseModel
from typing import List

class PipelineStage(BaseModel):
    id: str
    name: str
    order: int
    probability: int
    color: str = "#3b82f6"
    deal_count: int = 0
    total_value: float = 0.0
''',
    },
    'lms': {
        'courses': '''from pydantic import BaseModel
from typing import List, Optional

class Course(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    thumbnail: Optional[str] = None
    price: float = 0.0
    instructor_id: str
    category: str
    level: str = "beginner"
    duration_hours: float = 0.0
    enrollment_count: int = 0
    rating: float = 0.0
    is_published: bool = False
    tags: List[str] = []
    created_at: str
    updated_at: str

class CourseCreate(BaseModel):
    title: str
    description: str
    thumbnail: Optional[str] = None
    price: float = 0.0
    category: str
    level: str = "beginner"
    tags: List[str] = []
''',
        'lessons': '''from pydantic import BaseModel
from typing import Optional

class Lesson(BaseModel):
    id: str
    course_id: str
    module_id: Optional[str] = None
    title: str
    content: str
    video_url: Optional[str] = None
    duration_minutes: int = 0
    order: int = 0
    is_free: bool = False
    created_at: str

class LessonCreate(BaseModel):
    course_id: str
    module_id: Optional[str] = None
    title: str
    content: str
    video_url: Optional[str] = None
    duration_minutes: int = 0
    order: int = 0
    is_free: bool = False
''',
        'enrollments': '''from pydantic import BaseModel
from typing import List

class Enrollment(BaseModel):
    id: str
    user_id: str
    course_id: str
    progress: float = 0.0
    completed_lessons: List[str] = []
    enrolled_at: str
    completed_at: Optional[str] = None
    last_accessed: str
''',
    },
    'booking': {
        'services': '''from pydantic import BaseModel
from typing import Optional

class Service(BaseModel):
    id: str
    name: str
    description: str
    duration_minutes: int
    price: float
    currency: str = "USD"
    category: Optional[str] = None
    image: Optional[str] = None
    is_active: bool = True
    created_at: str

class ServiceCreate(BaseModel):
    name: str
    description: str
    duration_minutes: int
    price: float
    currency: str = "USD"
    category: Optional[str] = None
    image: Optional[str] = None
''',
        'slots': '''from pydantic import BaseModel
from typing import List

class TimeSlot(BaseModel):
    id: str
    service_id: str
    staff_id: Optional[str] = None
    date: str
    start_time: str
    end_time: str
    is_available: bool = True
    appointment_id: Optional[str] = None

class SlotCreate(BaseModel):
    service_id: str
    staff_id: Optional[str] = None
    date: str
    start_time: str
    end_time: str
''',
        'appointments': '''from pydantic import BaseModel
from typing import Optional

class Appointment(BaseModel):
    id: str
    service_id: str
    customer_id: str
    slot_id: str
    staff_id: Optional[str] = None
    date: str
    time: str
    status: str = "confirmed"
    notes: str = ""
    payment_status: str = "pending"
    created_at: str

class AppointmentCreate(BaseModel):
    service_id: str
    slot_id: str
    staff_id: Optional[str] = None
    notes: str = ""
''',
    },
    'ecommerce': {
        'products': '''from pydantic import BaseModel
from typing import List, Optional

class Product(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    price: float
    compare_price: Optional[float] = None
    images: List[str] = []
    category: str
    tags: List[str] = []
    stock: int = 0
    sku: Optional[str] = None
    is_active: bool = True
    is_featured: bool = False
    rating: float = 0.0
    review_count: int = 0
    created_at: str
    updated_at: str

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    compare_price: Optional[float] = None
    images: List[str] = []
    category: str
    tags: List[str] = []
    stock: int = 0
    sku: Optional[str] = None
    is_featured: bool = False
''',
        'orders': '''from pydantic import BaseModel
from typing import List, Optional

class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int
    image: Optional[str] = None

class Order(BaseModel):
    id: str
    order_number: str
    customer_id: str
    items: List[OrderItem]
    subtotal: float
    shipping: float = 0.0
    tax: float = 0.0
    total: float
    status: str = "pending"
    payment_status: str = "pending"
    shipping_address: Optional[dict] = None
    notes: str = ""
    created_at: str
    updated_at: str

class OrderCreate(BaseModel):
    items: List[dict]
    shipping_address: dict
    notes: str = ""
''',
    },
}

SCAFFOLD_BASE_FILES = {
    'docker-compose.yml': '''version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URL=mongodb://mongo:27017
      - DB_NAME={project_name}
    depends_on:
      - mongo
  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
volumes:
  mongo_data:
''',
    'Dockerfile': '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
    'requirements.txt': '''fastapi>=0.104.0
uvicorn>=0.24.0
motor>=3.3.0
pydantic>=2.5.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
httpx>=0.25.0
''',
    'env.example': '''MONGO_URL=mongodb://localhost:27017
DB_NAME={project_name}
JWT_SECRET=change-this-to-a-random-string
OLLAMA_BASE_URL=http://localhost:11434
STRIPE_SECRET_KEY=sk_test_xxx
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx
''',
    '.gitignore': '''__pycache__/
*.pyc
.env
node_modules/
frontend/.next/
frontend/dist/
*.log
.DS_Store
''',
}


class SaaSGenerateIn(BaseModel):
    name: str
    template: str
    features: List[str] = []
    database: str = "mongodb"
    frontend: str = "nextjs"
    auth_provider: str = "jwt"
    payment: str = "razorpay"
    deployment: str = "docker"


class FileUpdateIn(BaseModel):
    content: str


class AIEnhanceIn(BaseModel):
    file_path: str
    instruction: str


class GenerateAPIIn(BaseModel):
    collection_names: List[str]


class CloneIn(BaseModel):
    new_name: str


async def _ollama_generate_file(filename: str, context: Dict[str, Any]) -> str:
    system = (
        "You are a senior full-stack developer. Generate production-ready code files for a SaaS project. "
        "Output ONLY the raw code content. No markdown fences. No explanations. No comments unless absolutely necessary. "
        "Follow best practices: proper error handling, input validation, clean architecture."
    )
    user = (
        f"Generate the file `{filename}` for a {context['template'].upper()} SaaS application.\n"
        f"Tech stack: {context['frontend']} frontend, FastAPI backend, {context['database']} database.\n"
        f"Auth provider: {context['auth_provider']}. Payment: {context['payment']}.\n"
        f"Project name: {context['name']}\n"
        f"Features enabled: {', '.join(context['features'])}\n"
        f"Required imports and patterns: use Pydantic BaseModel for models, motor for MongoDB, "
        f"FastAPI APIRouter for routes, bcrypt for passwords, python-jose for JWT.\n"
        f"Return the complete file content only."
    )
    try:
        raw = await chat_completion(system=system, user=user, temperature=0.3)
        return raw.strip()
    except Exception:
        return f"# Auto-generated: {filename}\n# Template: {context['template']}\n# Features: {', '.join(context['features'])}\n"


def _build_file_tree(template: str, features: List[str], frontend: str, database: str) -> Dict[str, str]:
    tree = {}
    for fname, content in SCAFFOLD_BASE_FILES.items():
        tree[fname] = content

    tree['backend/main.py'] = (
        'from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\n'
        'from routes import router\n\n'
        'app = FastAPI(title="{name}", version="1.0.0")\n'
        'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\n'
        'app.include_router(router, prefix="/api")\n\n'
        '@app.get("/health")\n'
        'async def health():\n    return {{"status": "ok"}}\n'
    )

    template_cfg = TEMPLATES.get(template, {})
    collections = template_cfg.get('collections', [])

    tree['backend/db.py'] = (
        'import os\nfrom motor.motor_asyncio import AsyncIOMotorClient\n\n'
        'client = AsyncIOMotorClient(os.environ["MONGO_URL"])\n'
        'db = client[os.environ.get("DB_NAME", "saas_app")]\n\n'
        'def serialize(doc):\n'
        '    if doc is None:\n        return None\n'
        '    doc["id"] = doc.pop("_id", None) or doc.get("id")\n'
        '    return {k: v for k, v in doc.items() if k != "_id"}\n'
    )

    tree['backend/auth.py'] = (
        'import os, bcrypt, jwt\nfrom datetime import datetime, timedelta, timezone\n'
        'from fastapi import Depends, HTTPException\n'
        'from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials\n'
        'from db import db\n\n'
        'SECRET = os.environ.get("JWT_SECRET", "change-me")\n'
        'bearer = HTTPBearer(auto_error=False)\n\n'
        'def hash_pw(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()\n'
        'def verify_pw(pw, h): return bcrypt.checkpw(pw.encode(), h.encode())\n\n'
        'def create_token(uid, role="user"):\n'
        '    return jwt.encode({{"sub": uid, "role": role, '
        '"exp": datetime.now(timezone.utc) + timedelta(days=30)}}, SECRET, algorithm="HS256")\n\n'
        'async def get_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):\n'
        '    if not creds: raise HTTPException(401, "Not authenticated")\n'
        '    try:\n'
        '        p = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])\n'
        '    except: raise HTTPException(401, "Invalid token")\n'
        '    u = await db.users.find_one({{"id": p["sub"]}}, {{"_id": 0}})\n'
        '    if not u: raise HTTPException(401, "User not found")\n'
        '    return u\n'
    )

    for coll in collections:
        gen = TEMPLATE_FILE_GENERATORS.get(template, {}).get(coll)
        if gen:
            tree[f'backend/models/{coll}.py'] = gen
        else:
            tree[f'backend/models/{coll}.py'] = (
                f'from pydantic import BaseModel\nfrom typing import Optional, List\n\n'
                f'class {coll.title().replace("_", "")}(BaseModel):\n'
                f'    id: str\n    name: str\n    created_at: str\n\n'
                f'class {coll.title().replace("_", "")}Create(BaseModel):\n'
                f'    name: str\n'
            )

        tree[f'backend/routes/{coll}.py'] = (
            f'import uuid\nfrom datetime import datetime, timezone\n'
            f'from fastapi import APIRouter, HTTPException, Depends\n'
            f'from pydantic import BaseModel\n'
            f'from db import db, serialize\n'
            f'from auth import get_user\n\n'
            f'router = APIRouter(prefix="/{coll}", tags=["{coll}"])\n\n'
            f'def _now(): return datetime.now(timezone.utc).isoformat()\n\n'
            f'@router.get("/")\n'
            f'async def list_items(user=Depends(get_user)):\n'
            f'    items = await db.{coll}.find({{"user_id": user["id"]}}, {{"_id": 0}}).sort("created_at", -1).to_list(100)\n'
            f'    return {{"items": [serialize(i) for i in items]}}\n\n'
            f'@router.post("/")\n'
            f'async def create_item(body: dict, user=Depends(get_user)):\n'
            f'    doc = {{"id": str(uuid.uuid4()), "user_id": user["id"], **body, "created_at": _now(), "updated_at": _now()}}\n'
            f'    await db.{coll}.insert_one(doc)\n'
            f'    return serialize(doc)\n\n'
            f'@router.get("/{{item_id}}")\n'
            f'async def get_item(item_id: str, user=Depends(get_user)):\n'
            f'    item = await db.{coll}.find_one({{"id": item_id, "user_id": user["id"]}}, {{"_id": 0}})\n'
            f'    if not item: raise HTTPException(404, "Not found")\n'
            f'    return serialize(item)\n\n'
            f'@router.put("/{{item_id}}")\n'
            f'async def update_item(item_id: str, body: dict, user=Depends(get_user)):\n'
            f'    body["updated_at"] = _now()\n'
            f'    await db.{coll}.update_one({{"id": item_id, "user_id": user["id"]}}, {{"$set": body}})\n'
            f'    item = await db.{coll}.find_one({{"id": item_id}}, {{"_id": 0}})\n'
            f'    return serialize(item)\n\n'
            f'@router.delete("/{{item_id}}")\n'
            f'async def delete_item(item_id: str, user=Depends(get_user)):\n'
            f'    r = await db.{coll}.delete_one({{"id": item_id, "user_id": user["id"]}})\n'
            f'    return {{"deleted": r.deleted_count}}\n'
        )

    tree['backend/routes/__init__.py'] = (
        'from fastapi import APIRouter\n'
        + ''.join([f'from routes.{c} import router as {c}_router\n' for c in collections])
        + '\nrouter = APIRouter()\n'
        + ''.join([f'router.include_router({c}_router)\n' for c in collections])
    )

    tree['backend/models/__init__.py'] = (
        ''.join([f'from models.{c} import *\n' for c in collections])
    )

    frontend_map = {
        'nextjs': 'Next.js 14 with App Router, TailwindCSS, shadcn/ui',
        'react': 'React 18 with Vite, TailwindCSS, React Router',
        'vue': 'Vue 3 with Vite, TailwindCSS, Vue Router, Pinia',
    }
    tree['frontend/README.md'] = f"# Frontend\n\nStack: {frontend_map.get(frontend, frontend)}\n\nRun: `npm install && npm run dev`\n"

    if frontend == 'nextjs':
        tree['frontend/package.json'] = json.dumps({
            "name": f"{template}-frontend",
            "version": "1.0.0",
            "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
            "dependencies": {
                "next": "14.1.0",
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "tailwindcss": "^3.4.0",
                "axios": "^1.6.0",
                "zustand": "^4.4.0",
            },
        }, indent=2)
    elif frontend == 'react':
        tree['frontend/package.json'] = json.dumps({
            "name": f"{template}-frontend",
            "version": "1.0.0",
            "scripts": {"dev": "vite", "build": "vite build"},
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.21.0",
                "tailwindcss": "^3.4.0",
                "axios": "^1.6.0",
            },
            "devDependencies": {"@vitejs/plugin-react": "^4.2.0", "vite": "^5.0.0"},
        }, indent=2)
    else:
        tree['frontend/package.json'] = json.dumps({
            "name": f"{template}-frontend",
            "version": "1.0.0",
            "scripts": {"dev": "vite", "build": "vite build"},
            "dependencies": {
                "vue": "^3.4.0",
                "vue-router": "^4.2.0",
                "pinia": "^2.1.0",
                "tailwindcss": "^3.4.0",
                "axios": "^1.6.0",
            },
            "devDependencies": {"@vitejs/plugin-vue": "^5.0.0", "vite": "^5.0.0"},
        }, indent=2)

    tree['README.md'] = (
        f"# {template.upper()} SaaS Application\n\n"
        f"Generated by Getszy SaaS Builder\n\n"
        f"## Tech Stack\n"
        f"- Frontend: {frontend_map.get(frontend, frontend)}\n"
        f"- Backend: FastAPI + Python 3.11\n"
        f"- Database: {database}\n"
        f"- Auth: {features.get('auth', 'jwt') if isinstance(features, dict) else 'jwt'}\n"
        f"- Deployment: Docker\n\n"
        f"## Quick Start\n"
        f"1. `cp env.example .env`\n"
        f"2. `docker-compose up -d`\n"
        f"3. Visit `http://localhost:3000`\n\n"
        f"## Collections\n{', '.join(collections)}\n"
    )

    tree['README.md'] = (
        f"# {template.upper()} SaaS Application\n\n"
        f"Generated by Getszy SaaS Builder\n\n"
        f"## Tech Stack\n"
        f"- Frontend: {frontend_map.get(frontend, frontend)}\n"
        f"- Backend: FastAPI + Python 3.11\n"
        f"- Database: {database}\n"
        f"- Deployment: Docker\n\n"
        f"## Quick Start\n"
        f"1. `cp env.example .env`\n"
        f"2. `docker-compose up -d`\n"
        f"3. Visit `http://localhost:3000`\n\n"
        f"## Collections\n{', '.join(collections)}\n"
    )

    return tree


@router.post('/generate')
async def generate_project(body: SaaSGenerateIn, admin=Depends(get_current_admin)):
    if body.template not in TEMPLATES:
        raise HTTPException(400, f'Invalid template. Choose from: {", ".join(TEMPLATES.keys())}')
    if body.database not in ('mongodb', 'postgresql'):
        raise HTTPException(400, 'database must be mongodb or postgresql')
    if body.frontend not in ('react', 'nextjs', 'vue'):
        raise HTTPException(400, 'frontend must be react, nextjs, or vue')
    if body.auth_provider not in ('jwt', 'clerk', 'supabase'):
        raise HTTPException(400, 'auth_provider must be jwt, clerk, or supabase')
    if body.payment not in ('razorpay', 'stripe', 'both'):
        raise HTTPException(400, 'payment must be razorpay, stripe, or both')
    if body.deployment not in ('docker', 'vercel', 'vps'):
        raise HTTPException(400, 'deployment must be docker, vercel, or vps')

    project_id = _uid()
    file_tree = _build_file_tree(body.template, body.features, body.frontend, body.database)

    ctx = {
        'name': body.name,
        'template': body.template,
        'features': body.features,
        'database': body.database,
        'frontend': body.frontend,
        'auth_provider': body.auth_provider,
        'payment': body.payment,
        'deployment': body.deployment,
    }

    generated_files = {}
    for fname in list(file_tree.keys()):
        if fname.startswith('backend/models/') or fname.startswith('backend/routes/'):
            generated_files[fname] = await _ollama_generate_file(fname, ctx)
        else:
            generated_files[fname] = file_tree[fname]

    project = {
        'id': project_id,
        'name': body.name,
        'template': body.template,
        'features': body.features,
        'config': ctx,
        'files': generated_files,
        'file_tree': list(generated_files.keys()),
        'status': 'generated',
        'deploy_status': 'none',
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.saas_projects.insert_one(project)

    return {
        'project_id': project_id,
        'file_tree': project['file_tree'],
        'status': 'generated',
        'template': body.template,
        'config': ctx,
    }


@router.get('/projects')
async def list_projects(admin=Depends(get_current_admin)):
    projects = await db.saas_projects.find(
        {}, {'_id': 0, 'files': 0}
    ).sort('created_at', -1).to_list(100)
    return {'projects': projects}


@router.get('/projects/{project_id}')
async def get_project(project_id: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    return project


@router.get('/projects/{project_id}/files')
async def list_files(project_id: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'file_tree': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    return {'files': project.get('file_tree', [])}


@router.get('/projects/{project_id}/files/{file_path:path}')
async def get_file(project_id: str, file_path: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    if file_path not in files:
        raise HTTPException(404, f'File not found: {file_path}')
    return {'path': file_path, 'content': files[file_path]}


@router.put('/projects/{project_id}/files/{file_path:path}')
async def update_file(project_id: str, file_path: str, body: FileUpdateIn, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    if file_path not in files:
        raise HTTPException(404, f'File not found: {file_path}')
    files[file_path] = body.content
    await db.saas_projects.update_one(
        {'id': project_id},
        {'$set': {'files': files, 'updated_at': _now()}}
    )
    return {'status': 'updated', 'path': file_path}


@router.post('/projects/{project_id}/deploy')
async def deploy_project(project_id: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    deploy_id = _uid()
    deploy_record = {
        'id': deploy_id,
        'project_id': project_id,
        'status': 'building',
        'started_at': _now(),
        'completed_at': None,
        'logs': [],
        'url': None,
    }
    await db.saas_deploys.insert_one(deploy_record)
    await db.saas_projects.update_one(
        {'id': project_id},
        {'$set': {'deploy_status': 'building', 'updated_at': _now()}}
    )
    return {'deploy_id': deploy_id, 'status': 'building', 'started_at': deploy_record['started_at']}


@router.get('/projects/{project_id}/deploy-status')
async def deploy_status(project_id: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'deploy_status': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    deploy = await db.saas_deploys.find_one(
        {'project_id': project_id}, {'_id': 0}
    ).sort('started_at', -1)
    return {
        'project_id': project_id,
        'deploy_status': project.get('deploy_status', 'none'),
        'latest_deploy': deploy,
    }


@router.delete('/projects/{project_id}')
async def delete_project(project_id: str, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    await db.saas_projects.delete_one({'id': project_id})
    await db.saas_deploys.delete_many({'project_id': project_id})
    return {'deleted': True, 'project_id': project_id}


@router.post('/projects/{project_id}/clone')
async def clone_project(project_id: str, body: CloneIn, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    new_id = _uid()
    cloned = {
        'id': new_id,
        'name': body.new_name,
        'template': project['template'],
        'features': project['features'],
        'config': project['config'],
        'files': dict(project.get('files', {})),
        'file_tree': list(project.get('file_tree', [])),
        'status': 'generated',
        'deploy_status': 'none',
        'cloned_from': project_id,
        'created_at': _now(),
        'updated_at': _now(),
    }
    cloned['config']['name'] = body.new_name
    await db.saas_projects.insert_one(cloned)
    return {'project_id': new_id, 'name': body.new_name, 'cloned_from': project_id}


@router.get('/templates')
async def list_templates():
    return {'templates': [
        {
            'key': k,
            'name': v['name'],
            'description': v['description'],
            'collections': v['collections'],
            'features': v['features'],
            'preview_image': v['preview_image'],
            'tech_stack': v['tech_stack'],
            'use_cases': v['use_cases'],
        }
        for k, v in TEMPLATES.items()
    ]}


@router.post('/projects/{project_id}/ai-enhance')
async def ai_enhance(project_id: str, body: AIEnhanceIn, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1, 'config': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    if body.file_path not in files:
        raise HTTPException(404, f'File not found: {body.file_path}')
    current_content = files[body.file_path]
    system = (
        "You are a senior software engineer. Refactor and enhance the given code file based on the user's instruction. "
        "Output ONLY the complete enhanced file content. No markdown fences. No explanations."
    )
    user = (
        f"File: {body.file_path}\n"
        f"Instruction: {body.instruction}\n\n"
        f"Current content:\n```\n{current_content}\n```\n\n"
        f"Output the complete enhanced file content."
    )
    enhanced = await chat_completion(system=system, user=user, temperature=0.3)
    enhanced = enhanced.strip()
    files[body.file_path] = enhanced
    await db.saas_projects.update_one(
        {'id': project_id},
        {'$set': {'files': files, 'updated_at': _now()}}
    )
    return {'path': body.file_path, 'content': enhanced, 'status': 'enhanced'}


@router.post('/projects/{project_id}/generate-api')
async def generate_api_endpoints(project_id: str, body: GenerateAPIIn, admin=Depends(get_current_admin)):
    project = await db.saas_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1, 'config': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    config = project.get('config', {})
    generated_routes = {}
    for coll in body.collection_names:
        system = (
            "Generate a complete FastAPI router file with full CRUD operations for a MongoDB collection. "
            "Use motor async driver. Include list, create, get, update, delete endpoints. "
            "Use Pydantic BaseModel for request validation. No markdown fences. Output raw Python code."
        )
        user = (
            f"Generate CRUD routes for collection: {coll}\n"
            f"Database: {config.get('database', 'mongodb')}\n"
            f"Auth: Use get_user dependency from auth module\n"
            f"Pattern: Use db.{coll} for MongoDB access, _now() for timestamps\n"
            f"Return list with pagination, proper error handling, 404s."
        )
        code = await chat_completion(system=system, user=user, temperature=0.2)
        route_file = f'backend/routes/{coll}.py'
        files[route_file] = code.strip()
        generated_routes[coll] = route_file

    routes_init = 'from fastapi import APIRouter\n'
    for coll in body.collection_names:
        routes_init += f'from routes.{coll} import router as {coll}_router\n'
    routes_init += '\nrouter = APIRouter()\n'
    for coll in body.collection_names:
        routes_init += f'router.include_router({coll}_router)\n'
    files['backend/routes/__init__.py'] = routes_init

    await db.saas_projects.update_one(
        {'id': project_id},
        {'$set': {'files': files, 'updated_at': _now()}}
    )
    return {
        'generated_routes': generated_routes,
        'files_updated': list(generated_routes.values()) + ['backend/routes/__init__.py'],
        'status': 'generated',
    }
