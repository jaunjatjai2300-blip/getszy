"""Seed demo data if DB is empty."""
from db import db
from models import User, Category, Supplier, Product
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
     'images': ['https://images.unsplash.com/photo-1503551723145-6c040742065b-v2?w=800'], 'description': 'Fun activities, puzzles & learning for ages 4-8.'},
    {'name': 'AI for Beginners — eBook', 'price': 299, 'cost_price': 0, 'stock': 9999, 'category': 'digital-products', 'is_digital': True, 'is_featured': True,
     'images': ['https://images.unsplash.com/photo-1518770660439-4636190af475?w=800'], 'description': 'Comprehensive 120-page guide to start your AI journey.'},
    {'name': 'Notion Templates for Entrepreneurs', 'price': 499, 'cost_price': 0, 'stock': 9999, 'category': 'digital-products', 'is_digital': True,
     'images': ['https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=800'], 'description': 'Curated Notion templates to manage your business like a pro.'},
]


async def seed_if_empty():
    import re
    cnt = await db.users.count_documents({'role': 'admin'})
    if cnt > 0:
        return
    # Admin user
    admin = User(name='Getszy Admin', email='admin@getszy.com',
                 password_hash=hash_password('Admin@123'), role='admin')
    await db.users.insert_one(admin.model_dump())
    # Demo customer
    cust = User(name='Demo Customer', email='customer@getszy.com',
                password_hash=hash_password('Demo@123'), role='customer')
    await db.users.insert_one(cust.model_dump())
    # Categories
    for c in CATEGORIES:
        if not await db.categories.find_one({'slug': c['slug']}):
            await db.categories.insert_one(Category(**c).model_dump())
    # Suppliers
    for s in SUPPLIERS:
        if not await db.suppliers.find_one({'name': s['name']}):
            await db.suppliers.insert_one(Supplier(**s).model_dump())
    # Products
    for pdata in PRODUCTS:
        slug = re.sub(r'[^a-z0-9]+', '-', pdata['name'].lower()).strip('-')
        p = Product(slug=slug, **pdata)
        await db.products.insert_one(p.model_dump())
    print(f'[seed] Seeded: 1 admin, 1 customer, {len(CATEGORIES)} cats, {len(SUPPLIERS)} sups, {len(PRODUCTS)} products')
