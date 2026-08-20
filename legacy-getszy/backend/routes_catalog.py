from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel, Field
from db import db
from models import Product, ProductIn, Category, Supplier
from auth import get_current_admin
from cache_utils import cache_get, cache_set, cache_key, cache_invalidate
from fastapi.responses import JSONResponse
import re

router = APIRouter(tags=['catalog'])


def _slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


class SupplierIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdateIn(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    contact: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class CategoryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    image: Optional[str] = None
    description: Optional[str] = None


# ===== Categories =====
@router.get('/categories')
async def list_categories():
    key = cache_key('categories')
    cached = cache_get(key)
    if cached is not None:
        return JSONResponse(cached, headers={'Cache-Control': 'public, max-age=300'})
    cats = await db.categories.find({}, {'_id': 0}).to_list(100)
    # add product counts
    for c in cats:
        c['product_count'] = await db.products.count_documents({'category': c['slug'], 'is_active': True})
    cache_set(key, cats, 300)
    return JSONResponse(cats, headers={'Cache-Control': 'public, max-age=300'})


@router.post('/admin/categories', dependencies=[Depends(get_current_admin)])
async def create_category(body: CategoryIn):
    slug = _slug(body.name)
    if await db.categories.find_one({'slug': slug}):
        raise HTTPException(400, 'Category already exists')
    cat = Category(name=body.name, slug=slug, image=body.image, description=body.description)
    await db.categories.insert_one(cat.model_dump())
    cache_invalidate('categories')
    return cat.model_dump()


@router.delete('/admin/categories/{cat_id}', dependencies=[Depends(get_current_admin)])
async def delete_category(cat_id: str):
    res = await db.categories.delete_one({'id': cat_id})
    cache_invalidate('categories')
    return {'deleted': res.deleted_count}


# ===== Products =====
@router.get('/products')
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 60,
):
    q = {'is_active': True}
    if category:
        q['category'] = category
    if search:
        safe_search = re.escape(search)
        q['name'] = {'$regex': safe_search, '$options': 'i'}
    if featured is not None:
        q['is_featured'] = featured
    key = cache_key('products', category, search, featured, limit)
    cached = cache_get(key)
    if cached is not None:
        return JSONResponse(cached, headers={'Cache-Control': 'public, max-age=60'})
    items = await db.products.find(q, {'_id': 0, 'cost_price': 0}).limit(limit).to_list(limit)
    cache_set(key, items, 60)
    return JSONResponse(items, headers={'Cache-Control': 'public, max-age=60'})


@router.get('/products/{pid}')
async def get_product(pid: str):
    p = await db.products.find_one({'$or': [{'id': pid}, {'slug': pid}]}, {'_id': 0, 'cost_price': 0})
    if not p:
        raise HTTPException(404, 'Not found')
    return p


@router.get('/products/{pid}/preview', response_class=HTMLResponse)
async def preview_product(pid: str):
    """Public, SEO-friendly product preview. No auth required (embeddable in iframes)."""
    p = await db.products.find_one(
        {'$or': [{'id': pid}, {'slug': pid}], 'is_active': True},
        {'_id': 0, 'cost_price': 0},
    )
    if not p:
        return HTMLResponse(
            content='<html><body style="font-family:system-ui;padding:2rem;text-align:center">'
                    '<h1>Product Not Found</h1>'
                    '<p>This product is unavailable or no longer listed.</p></body></html>',
            status_code=404,
        )

    name = p.get('name', 'Product')
    price = p.get('price', 0)
    desc = p.get('description', '')
    category = p.get('category', '').replace('-', ' ').title()
    supplier = p.get('supplier', '')
    stock = p.get('stock', 0)
    slug = p.get('slug', p.get('id', ''))
    images = p.get('images', [])
    NO_IMG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='400'>"
              "<rect width='100%' height='100%' fill='%23e5e7eb'/>"
              "<text x='50%' y='50%' font-family='Arial' font-size='28' fill='%236b7280' "
              "text-anchor='middle' dominant-baseline='middle'>No Image</text></svg>")
    main_img = images[0] if images else NO_IMG
    in_stock = stock > 0
    stock_text = 'In Stock' if in_stock else 'Out of Stock'
    stock_class = 'in' if in_stock else 'out'
    stock_icon = '✅' if in_stock else '❌'
    availability = 'InStock' if in_stock else 'OutOfStock'

    thumbs = ''
    if len(images) > 1:
        items = []
        for i, img in enumerate(images):
            active = ' active' if i == 0 else ''
            items.append(
                '<img class="thumb%s" src="%s" alt="%s %d" '
                "onclick=\"document.getElementById('mainImg').src='%s'\">" % (active, img, name, i + 1, img)
            )
        thumbs = '<div class="thumbnails">%s</div>' % ''.join(items)

    desc_html = '<div class="description">%s</div>' % desc if desc else ''
    supplier_html = '<span>🏷️ Supplier: %s</span>' % supplier if supplier else ''

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NAME - Getszy</title>
<meta name="description" content="DESC">
<meta property="og:title" content="NAME">
<meta property="og:description" content="DESC">
<meta property="og:image" content="MAINIMG">
<meta property="og:type" content="product">
<meta property="product:price:amount" content="PRICE">
<meta property="product:price:currency" content="INR">
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "NAME",
    "description": "DESC",
    "image": "MAINIMG",
    "offers": {
        "@type": "Offer",
        "price": "PRICE",
        "priceCurrency": "INR",
        "availability": "https://schema.org/AVAIL"
    }
}
</script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; background: #f9fafb; }
.container { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }
.product-card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
.image-gallery { position: relative; }
.main-image { width: 100%; height: 400px; object-fit: cover; background: #f3f4f6; }
.thumbnails { display: flex; gap: 8px; padding: 1rem; overflow-x: auto; }
.thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer; border: 2px solid transparent; }
.thumb.active, .thumb:hover { border-color: #0d9488; }
.content { padding: 1.5rem; }
.category { font-size: 0.875rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
h1 { font-size: 1.875rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem; }
.price { font-size: 2rem; font-weight: 700; color: #0d9488; margin-bottom: 1rem; }
.description { color: #4b5563; margin-bottom: 1.5rem; white-space: pre-wrap; }
.meta { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; font-size: 0.875rem; color: #6b7280; }
.meta span { display: flex; align-items: center; gap: 0.375rem; }
.stock { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border-radius: 9999px; font-size: 0.875rem; font-weight: 500; }
.stock.in { background: #dcfce7; color: #166534; }
.stock.out { background: #fee2e2; color: #991b1b; }
.cta { display: block; width: 100%; padding: 1rem; background: #0d9488; color: white; text-align: center; font-weight: 600; font-size: 1.125rem; border-radius: 8px; text-decoration: none; margin-top: 1rem; transition: background 0.2s; }
.cta:hover { background: #0f766e; }
@media (max-width: 640px) { .main-image { height: 300px; } }
</style>
</head>
<body>
<div class="container">
<div class="product-card">
<div class="image-gallery">
<img id="mainImg" class="main-image" src="MAINIMG" alt="NAME">
THUMBS
</div>
<div class="content">
<div class="category">CATEGORY</div>
<h1>NAME</h1>
<div class="price">₹PRICE</div>
DESCHTML
<div class="meta">
<span>📦 Category: CATEGORY</span>
SUPPLIERHTML
</div>
<div class="stock STOCKCLASS">
STOCKICON STOCKTEXT (STOCKCOUNT available)
</div>
<a href="https://getszy.com/product/SLUG" class="cta" target="_blank">View on Getszy Store</a>
</div>
</div>
</div>
</body>
</html>"""

    html = (html
            .replace('NAME', name)
            .replace('PRICE', '{:,.0f}'.format(price))
            .replace('DESC', desc[:160])
            .replace('MAINIMG', main_img)
            .replace('CATEGORY', category)
            .replace('SUPPLIERHTML', supplier_html)
            .replace('THUMBS', thumbs)
            .replace('DESCHTML', desc_html)
            .replace('STOCKCLASS', stock_class)
            .replace('STOCKICON', stock_icon)
            .replace('STOCKTEXT', stock_text)
            .replace('STOCKCOUNT', str(stock))
            .replace('SLUG', str(slug))
            .replace('AVAIL', availability))
    return HTMLResponse(content=html)


@router.get('/admin/products', dependencies=[Depends(get_current_admin)])
async def admin_list_products():
    items = await db.products.find({}, {'_id': 0}).to_list(500)
    return items


@router.post('/admin/products', dependencies=[Depends(get_current_admin)])
async def admin_create_product(body: ProductIn):
    p = Product(**body.model_dump(), slug=_slug(body.name))
    await db.products.insert_one(p.model_dump())
    cache_invalidate('products')
    return p.model_dump()


@router.put('/admin/products/{pid}', dependencies=[Depends(get_current_admin)])
async def admin_update_product(pid: str, body: ProductIn):
    existing = await db.products.find_one({'id': pid})
    if not existing:
        raise HTTPException(404, 'Not found')
    updates = body.model_dump(exclude_unset=True)
    updates.pop('id', None)
    res = await db.products.update_one({'id': pid}, {'$set': updates})
    p = await db.products.find_one({'id': pid}, {'_id': 0})
    cache_invalidate('products')
    return p


@router.delete('/admin/products/{pid}', dependencies=[Depends(get_current_admin)])
async def admin_delete_product(pid: str):
    res = await db.products.delete_one({'id': pid})
    cache_invalidate('products')
    return {'deleted': res.deleted_count}


# ===== Suppliers =====
@router.get('/admin/suppliers', dependencies=[Depends(get_current_admin)])
async def list_suppliers():
    return await db.suppliers.find({}, {'_id': 0}).to_list(200)


@router.post('/admin/suppliers', dependencies=[Depends(get_current_admin)])
async def create_supplier(body: SupplierIn):
    s = Supplier(name=body.name, contact=body.contact, email=body.email, notes=body.notes)
    await db.suppliers.insert_one(s.model_dump())
    return s.model_dump()


@router.put('/admin/suppliers/{sid}', dependencies=[Depends(get_current_admin)])
async def update_supplier(sid: str, body: SupplierUpdateIn):
    existing = await db.suppliers.find_one({'id': sid})
    if not existing:
        raise HTTPException(404, 'Supplier not found')
    updates = body.model_dump(exclude_unset=True)
    updates.pop('id', None)
    await db.suppliers.update_one({'id': sid}, {'$set': updates})
    return await db.suppliers.find_one({'id': sid}, {'_id': 0})


@router.delete('/admin/suppliers/{sid}', dependencies=[Depends(get_current_admin)])
async def delete_supplier(sid: str):
    res = await db.suppliers.delete_one({'id': sid})
    return {'deleted': res.deleted_count}
