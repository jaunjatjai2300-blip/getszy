from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from pydantic import BaseModel, Field
from db import db
from models import Product, ProductIn, Category, Supplier
from auth import get_current_admin
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
    cats = await db.categories.find({}, {'_id': 0}).to_list(100)
    # add product counts
    for c in cats:
        c['product_count'] = await db.products.count_documents({'category': c['slug'], 'is_active': True})
    return cats


@router.post('/admin/categories', dependencies=[Depends(get_current_admin)])
async def create_category(body: CategoryIn):
    slug = _slug(body.name)
    if await db.categories.find_one({'slug': slug}):
        raise HTTPException(400, 'Category already exists')
    cat = Category(name=body.name, slug=slug, image=body.image, description=body.description)
    await db.categories.insert_one(cat.model_dump())
    return cat.model_dump()


@router.delete('/admin/categories/{cat_id}', dependencies=[Depends(get_current_admin)])
async def delete_category(cat_id: str):
    res = await db.categories.delete_one({'id': cat_id})
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
    items = await db.products.find(q, {'_id': 0, 'cost_price': 0}).limit(limit).to_list(limit)
    return items


@router.get('/products/{pid}')
async def get_product(pid: str):
    p = await db.products.find_one({'$or': [{'id': pid}, {'slug': pid}]}, {'_id': 0, 'cost_price': 0})
    if not p:
        raise HTTPException(404, 'Not found')
    return p


@router.get('/admin/products', dependencies=[Depends(get_current_admin)])
async def admin_list_products():
    items = await db.products.find({}, {'_id': 0}).to_list(500)
    return items


@router.post('/admin/products', dependencies=[Depends(get_current_admin)])
async def admin_create_product(body: ProductIn):
    p = Product(**body.model_dump(), slug=_slug(body.name))
    await db.products.insert_one(p.model_dump())
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
    return p


@router.delete('/admin/products/{pid}', dependencies=[Depends(get_current_admin)])
async def admin_delete_product(pid: str):
    res = await db.products.delete_one({'id': pid})
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
