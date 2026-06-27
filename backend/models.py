from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid


def _id():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc).isoformat()


class User(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str = Field(default_factory=_id)
    name: str
    email: EmailStr
    password_hash: str
    role: str = 'customer'
    phone: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    phone: Optional[str] = None


class Category(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    slug: str
    image: Optional[str] = None
    description: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class Supplier(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class Product(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    slug: Optional[str] = None
    description: Optional[str] = ''
    images: List[str] = []
    price: float
    cost_price: float = 0.0
    stock: int = 0
    category: str
    supplier: Optional[str] = None
    is_digital: bool = False
    is_featured: bool = False
    is_active: bool = True
    created_at: str = Field(default_factory=_now)


class ProductIn(BaseModel):
    name: str
    description: Optional[str] = ''
    images: List[str] = []
    price: float
    cost_price: float = 0.0
    stock: int = 0
    category: str
    supplier: Optional[str] = None
    is_digital: bool = False
    is_featured: bool = False


class CartItem(BaseModel):
    product_id: str
    quantity: int = 1


class Cart(BaseModel):
    user_id: str
    items: List[CartItem] = []
    updated_at: str = Field(default_factory=_now)


class Address(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = ''
    city: str
    state: str
    pincode: str
    country: str = 'India'


class OrderItem(BaseModel):
    product_id: str
    name: str
    image: Optional[str] = None
    price: float
    cost_price: float = 0.0
    quantity: int
    supplier: Optional[str] = None


class Order(BaseModel):
    id: str = Field(default_factory=_id)
    order_number: str
    user_id: str
    customer_name: str
    customer_email: str
    items: List[OrderItem]
    subtotal: float
    shipping_fee: float = 0.0
    total: float
    cost_total: float = 0.0
    profit: float = 0.0
    address: Address
    status: str = 'pending'
    tracking_number: Optional[str] = None
    payment_status: str = 'pending'
    notes: Optional[str] = ''
    created_at: str = Field(default_factory=_now)


class CheckoutIn(BaseModel):
    address: Address
    notes: Optional[str] = ''


class OrderStatusUpdate(BaseModel):
    status: str
    tracking_number: Optional[str] = None


class AdminChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None


class AdminChatMessage(BaseModel):
    id: str = Field(default_factory=_id)
    session_id: str
    role: str
    text: str
    intent: Optional[str] = None
    params: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=_now)


# ===== Learning Academy =====
class Lesson(BaseModel):
    id: str = Field(default_factory=_id)
    course_slug: str
    module_id: Optional[str] = None
    title: str
    description: str = ''
    video_url: str = ''  # YouTube embed URL or video link
    duration_min: int = 10
    order: int = 0
    resources: List[Dict[str, str]] = []  # [{title, url}]
    created_at: str = Field(default_factory=_now)


class Module(BaseModel):
    id: str = Field(default_factory=_id)
    course_slug: str
    title: str
    order: int = 0


class Course(BaseModel):
    id: str = Field(default_factory=_id)
    slug: str
    title: str
    subtitle: str = ''
    description: str = ''
    level: str = 'Beginner'  # Beginner | Intermediate | Advanced
    duration_hours: float = 2.0
    thumbnail: str = ''
    outcomes: List[str] = []
    prerequisites: List[str] = []
    instructor: str = 'Getszy AI Team'
    is_published: bool = True
    is_featured: bool = False
    enrollments_count: int = 0
    created_at: str = Field(default_factory=_now)


class Enrollment(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    course_slug: str
    progress: float = 0.0  # 0.0 - 1.0
    completed_lessons: List[str] = []
    completed_at: Optional[str] = None
    enrolled_at: str = Field(default_factory=_now)


class TutorChatIn(BaseModel):
    message: str
    lesson_id: Optional[str] = None
    session_id: Optional[str] = None


class CourseIn(BaseModel):
    title: str
    subtitle: Optional[str] = ''
    description: Optional[str] = ''
    level: str = 'Beginner'
    duration_hours: float = 2.0
    thumbnail: Optional[str] = ''
    outcomes: List[str] = []
    prerequisites: List[str] = []
    is_featured: bool = False


class ModuleIn(BaseModel):
    course_slug: str
    title: str
    order: int = 0


class LessonIn(BaseModel):
    course_slug: str
    module_id: Optional[str] = None
    title: str
    description: Optional[str] = ''
    video_url: Optional[str] = ''
    duration_min: int = 10
    order: int = 0
    resources: List[Dict[str, str]] = []
