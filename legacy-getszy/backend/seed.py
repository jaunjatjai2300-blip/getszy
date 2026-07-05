"""Seed demo data if DB is empty."""
import re
from db import db
from models import User, Category, Supplier, Product, Course, Module, Lesson
from auth import hash_password

CATEGORIES = [
    {'name': 'Fashion', 'slug': 'fashion', 'image': 'https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800'},
    {'name': 'Jewellery', 'slug': 'jewellery', 'image': 'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=800'},
    {'name': 'Beauty', 'slug': 'beauty', 'image': 'https://images.unsplash.com/photo-1522335789203-aaa2f6ed9b51?w=800'},
    {'name': 'Home Decor', 'slug': 'home-decor', 'image': 'https://images.unsplash.com/photo-1598082862596-821983eb115e?w=800'},
    {'name': 'Gadgets', 'slug': 'gadgets', 'image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800'},
    {'name': 'Kids', 'slug': 'kids', 'image': 'https://images.unsplash.com/photo-1613536491198-a0afa1916b3b?w=800'},
    {'name': 'Digital Products', 'slug': 'digital-products', 'image': 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800'},
]
SUPPLIERS = [
    {'name': 'Surat Textiles', 'contact': '+91-9876543210', 'notes': 'Fast fashion supplier'},
    {'name': 'Meesho Wholesale', 'contact': '+91-9876500001', 'notes': 'Jewellery & accessories'},
    {'name': 'Mumbai Beauty Co', 'contact': '+91-9876500002', 'notes': 'Cosmetics supplier'},
]
PRODUCTS = [
    {'name': 'Floral Maxi Dress', 'price': 1299, 'cost_price': 550, 'stock': 25, 'category': 'fashion', 'supplier': 'Surat Textiles', 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=800'], 'description': 'Breezy floral maxi dress, perfect for summer outings.'},
    {'name': 'Elegant Silk Saree', 'price': 2499, 'cost_price': 1100, 'stock': 12, 'category': 'fashion', 'supplier': 'Surat Textiles',
     'images': ['https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=800'], 'description': 'Traditional silk saree with intricate border work.'},
    {'name': 'Rose Gold Hoop Earrings', 'price': 899, 'cost_price': 320, 'stock': 40, 'category': 'jewellery', 'supplier': 'Meesho Wholesale', 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=800'], 'description': 'Delicate rose-gold plated hoops for everyday elegance.'},
    {'name': 'Pearl Pendant Necklace', 'price': 1499, 'cost_price': 600, 'stock': 18, 'category': 'jewellery', 'supplier': 'Meesho Wholesale',
     'images': ['https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=800'], 'description': 'Classic pearl pendant on a 18k gold-plated chain.'},
    {'name': 'Vitamin C Glow Serum', 'price': 799, 'cost_price': 280, 'stock': 60, 'category': 'beauty', 'supplier': 'Mumbai Beauty Co', 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1556228720-195a672e8a03?w=800'], 'description': 'Brightening serum with 15% Vitamin C for radiant skin.'},
    {'name': 'Matte Lipstick Set (5)', 'price': 999, 'cost_price': 350, 'stock': 35, 'category': 'beauty', 'supplier': 'Mumbai Beauty Co',
     'images': ['https://images.unsplash.com/photo-1522335789203-aaa2f6ed9b51?w=800'], 'description': 'Long-lasting matte lipsticks in 5 must-have shades.'},
    {'name': 'Ceramic Vase Set', 'price': 1199, 'cost_price': 480, 'stock': 22, 'category': 'home-decor', 'supplier': 'Surat Textiles',
     'images': ['https://images.unsplash.com/photo-1602874801006-7a64a2a4fe9b?w=800'], 'description': 'Hand-crafted ceramic vases — a trio of elegance.'},
    {'name': 'Cozy Throw Blanket', 'price': 1599, 'cost_price': 650, 'stock': 15, 'category': 'home-decor', 'supplier': 'Surat Textiles', 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=800'], 'description': 'Soft, warm throw blanket in neutral tones.'},
    {'name': 'Wireless Earbuds Pro', 'price': 2299, 'cost_price': 1100, 'stock': 30, 'category': 'gadgets', 'supplier': 'Meesho Wholesale',
     'images': ['https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=800'], 'description': 'Crisp sound, all-day comfort, 24-hour battery.'},
    {'name': 'Smart Beauty Mirror', 'price': 3499, 'cost_price': 1500, 'stock': 10, 'category': 'gadgets', 'supplier': 'Mumbai Beauty Co',
     'images': ['https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=800'], 'description': 'LED smart mirror with adjustable brightness & magnification.'},
    {'name': 'Kids Soft Toy Bundle', 'price': 799, 'cost_price': 300, 'stock': 28, 'category': 'kids', 'supplier': 'Surat Textiles',
     'images': ['https://images.unsplash.com/photo-1613536491198-a0afa1916b3b?w=800'], 'description': 'A delightful bundle of three soft plush toys.'},
    {'name': 'Educational Activity Book', 'price': 449, 'cost_price': 150, 'stock': 50, 'category': 'kids', 'supplier': 'Meesho Wholesale',
     'images': ['https://images.unsplash.com/photo-1503551723145-6c040742065b?w=800'], 'description': 'Fun activities, puzzles & learning for ages 4-8.'},
    {'name': 'AI for Beginners — eBook', 'price': 299, 'cost_price': 0, 'stock': 9999, 'category': 'digital-products', 'is_digital': True, 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1518770660439-4636190af475?w=800'], 'description': 'Comprehensive 120-page guide to start your AI journey.'},
    {'name': 'Notion Templates for Entrepreneurs', 'price': 499, 'cost_price': 0, 'stock': 9999, 'category': 'digital-products', 'is_digital': True,
     'images': ['https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=800'], 'description': 'Curated Notion templates to manage your business like a pro.'},
]

COURSES = [
    {
        'slug': 'ai-foundations-for-women',
        'title': 'AI Foundations for Women',
        'subtitle': 'Start your AI journey with zero jargon',
        'description': 'A warm, beginner-friendly course covering what AI is, how it works, and where it fits in everyday life and careers.',
        'level': 'Beginner', 'duration_hours': 3.5, 'is_featured': True,
        'thumbnail': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800',
        'outcomes': ['Understand AI fundamentals', 'Use AI tools confidently', 'Identify AI opportunities in daily life', 'Build your first AI workflow'],
        'prerequisites': ['Just curiosity'],
        'lessons': [
            {'title': 'Welcome — Why AI matters for women', 'video_url': 'https://www.youtube.com/embed/2ePf9rue1Ao', 'duration_min': 8, 'description': 'A warm welcome and roadmap for your AI journey.'},
            {'title': 'What is AI? In simple terms', 'video_url': 'https://www.youtube.com/embed/ad79nYk2keg', 'duration_min': 12, 'description': 'AI explained with real-world analogies.'},
            {'title': 'Machine Learning vs Deep Learning', 'video_url': 'https://www.youtube.com/embed/zjkBMFhNj_g', 'duration_min': 15, 'description': 'Demystifying ML and DL with examples.'},
            {'title': 'How ChatGPT actually works', 'video_url': 'https://www.youtube.com/embed/w65p_IIp6JY', 'duration_min': 18, 'description': 'Behind the scenes of large language models.'},
            {'title': 'Your first AI-powered task', 'video_url': 'https://www.youtube.com/embed/Yq0QkCxoTHM', 'duration_min': 20, 'description': 'Hands-on — try AI to automate one task today.'},
        ],
    },
    {
        'slug': 'chatgpt-and-prompting-mastery',
        'title': 'ChatGPT & Prompting Mastery',
        'subtitle': 'Talk to AI like a pro and 10x your output',
        'description': 'Master prompt engineering, advanced techniques, and use ChatGPT for writing, research, content creation, and business workflows.',
        'level': 'Intermediate', 'duration_hours': 4.5, 'is_featured': True,
        'thumbnail': 'https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=800',
        'outcomes': ['Write powerful prompts', 'Use ChatGPT for content + research', 'Automate writing workflows', 'Build a personal AI assistant'],
        'prerequisites': ['AI Foundations or basic ChatGPT usage'],
        'lessons': [
            {'title': 'Anatomy of a great prompt', 'video_url': 'https://www.youtube.com/embed/jC4v5AS4RIM', 'duration_min': 14, 'description': 'The 5 building blocks of effective prompts.'},
            {'title': 'Role + Context + Task framework', 'video_url': 'https://www.youtube.com/embed/dOxUroR57xs', 'duration_min': 18, 'description': 'The RCT method that beats 90% of prompts.'},
            {'title': 'Chain-of-thought prompting', 'video_url': 'https://www.youtube.com/embed/H4olM_mExl8', 'duration_min': 16, 'description': 'Teach AI to reason step-by-step.'},
            {'title': 'Writing content that converts', 'video_url': 'https://www.youtube.com/embed/aircAruvnKk', 'duration_min': 22, 'description': 'Use AI for blog posts, ads, and social.'},
            {'title': 'Building a research assistant', 'video_url': 'https://www.youtube.com/embed/IHZwWFHWa-w', 'duration_min': 24, 'description': 'Save 10 hours/week on research tasks.'},
            {'title': 'Custom GPTs and personas', 'video_url': 'https://www.youtube.com/embed/J0Aq44Pze-w', 'duration_min': 20, 'description': 'Build your own specialized AI assistant.'},
        ],
    },
    {
        'slug': 'build-income-with-ai-no-code',
        'title': 'Build Income with AI — No Code',
        'subtitle': 'Earn from home using AI tools, zero coding',
        'description': 'Practical course on building real income streams using AI tools — freelancing, content creation, services, and digital products.',
        'level': 'Intermediate', 'duration_hours': 5.5, 'is_featured': True,
        'thumbnail': 'https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800',
        'outcomes': ['Set up an AI-powered service business', 'Create + sell digital products', 'Land freelance clients', 'Build passive income with AI'],
        'prerequisites': ['ChatGPT basics'],
        'lessons': [
            {'title': 'The AI income landscape in 2026', 'video_url': 'https://www.youtube.com/embed/m_d3kI23wlw', 'duration_min': 15, 'description': 'Where the real money is being made with AI.'},
            {'title': 'Niche selection — your unfair advantage', 'video_url': 'https://www.youtube.com/embed/H9M3n90gqdQ', 'duration_min': 18, 'description': 'Pick a niche that fits you + pays well.'},
            {'title': 'AI content creation as a service', 'video_url': 'https://www.youtube.com/embed/JTxsNm9IdYU', 'duration_min': 22, 'description': 'Offer blog/social content using AI.'},
            {'title': 'Designing digital products with AI', 'video_url': 'https://www.youtube.com/embed/8jLOx1hD3_o', 'duration_min': 24, 'description': 'eBooks, templates, prompts, courses.'},
            {'title': 'AI virtual assistant business', 'video_url': 'https://www.youtube.com/embed/iAyJG-pYS9I', 'duration_min': 20, 'description': 'Offer VA services 10x faster with AI.'},
            {'title': 'Marketing yourself online', 'video_url': 'https://www.youtube.com/embed/1aA1WGON49E', 'duration_min': 18, 'description': 'Get clients through Instagram, LinkedIn.'},
            {'title': 'Pricing, payments, and scaling', 'video_url': 'https://www.youtube.com/embed/u3rqe6jbAQc', 'duration_min': 22, 'description': 'From your first ₹1000 to ₹1 lakh/month.'},
        ],
    },
    {
        'slug': 'become-ai-independent-career-path',
        'title': 'Become AI Independent — Career Path',
        'subtitle': 'From learner to AI professional in 6 months',
        'description': 'The advanced track for women who want to become AI-fluent professionals — prompt engineers, AI product managers, AI-augmented marketers.',
        'level': 'Advanced', 'duration_hours': 8.0,
        'thumbnail': 'https://images.unsplash.com/photo-1573164713988-8665fc963095?w=800',
        'outcomes': ['Master 10+ AI tools deeply', 'Build a portfolio', 'Crack AI job interviews', 'Start your own AI consultancy'],
        'prerequisites': ['Build Income with AI or equivalent experience'],
        'lessons': [
            {'title': 'AI career paths for women in 2026', 'video_url': 'https://www.youtube.com/embed/3yPBVii7Ct0', 'duration_min': 18, 'description': 'Map your career to the AI economy.'},
            {'title': 'Deep dive: prompt engineering', 'video_url': 'https://www.youtube.com/embed/p09yRj47kNM', 'duration_min': 30, 'description': 'Professional-level prompt techniques.'},
            {'title': 'AI tools every pro must know', 'video_url': 'https://www.youtube.com/embed/eyTtAheVm9w', 'duration_min': 25, 'description': 'ChatGPT, Claude, Midjourney, n8n, more.'},
            {'title': 'Building an AI portfolio', 'video_url': 'https://www.youtube.com/embed/dPq7DDjBfnE', 'duration_min': 22, 'description': 'Showcase work that gets you hired.'},
            {'title': 'Networking + Personal branding', 'video_url': 'https://www.youtube.com/embed/wOdmiOAYjQ4', 'duration_min': 20, 'description': 'Build your AI personal brand.'},
            {'title': 'AI consultancy — charge ₹50k+/project', 'video_url': 'https://www.youtube.com/embed/JBoT_pEwiP0', 'duration_min': 25, 'description': 'Productize your AI expertise.'},
            {'title': 'Interview prep for AI roles', 'video_url': 'https://www.youtube.com/embed/o42Cb1pTNVk', 'duration_min': 24, 'description': 'Crack interviews at AI-first companies.'},
            {'title': 'Your 90-day action plan', 'video_url': 'https://www.youtube.com/embed/qXcUkN2x8KM', 'duration_min': 18, 'description': 'Concrete weekly plan to AI independence.'},
        ],
    },
]


async def seed_if_empty():
    cnt = await db.users.count_documents({'role': 'admin'})
    if cnt > 0:
        return
    admin = User(name='Getszy Admin', email='admin@getszy.com',
                 password_hash=hash_password('Admin@123'), role='admin')
    await db.users.insert_one(admin.model_dump())
    cust = User(name='Demo Customer', email='customer@getszy.com',
                password_hash=hash_password('Demo@123'), role='customer')
    await db.users.insert_one(cust.model_dump())
    for c in CATEGORIES:
        if not await db.categories.find_one({'slug': c['slug']}):
            await db.categories.insert_one(Category(**c).model_dump())
    for s in SUPPLIERS:
        if not await db.suppliers.find_one({'name': s['name']}):
            await db.suppliers.insert_one(Supplier(**s).model_dump())
    for pdata in PRODUCTS:
        slug = re.sub(r'[^a-z0-9]+', '-', pdata['name'].lower()).strip('-')
        p = Product(slug=slug, **pdata)
        await db.products.insert_one(p.model_dump())
    print(f'[seed] Seeded base data')


async def seed_courses_if_empty():
    if await db.courses.count_documents({}) > 0:
        return
    for cdata in COURSES:
        lessons_data = cdata.pop('lessons', [])
        course = Course(**cdata)
        await db.courses.insert_one(course.model_dump())
        # Single default module
        default_mod = Module(course_slug=course.slug, title='Curriculum', order=1)
        await db.modules.insert_one(default_mod.model_dump())
        for i, l in enumerate(lessons_data):
            lesson = Lesson(course_slug=course.slug, module_id=default_mod.id, order=i + 1, **l)
            await db.lessons.insert_one(lesson.model_dump())
    print(f'[seed] Seeded {len(COURSES)} courses with lessons')
