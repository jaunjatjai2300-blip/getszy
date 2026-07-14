import uuid
import json
import yaml
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/api-builder', tags=['api-builder'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


MONGO_TYPE_MAP = {
    'str': 'string', 'int': 'integer', 'float': 'number',
    'bool': 'boolean', 'list': 'array', 'dict': 'object',
}


def _infer_schema(collection_name: str, sample_docs: list) -> dict:
    fields = {}
    for doc in sample_docs:
        for key, val in doc.items():
            if key == '_id':
                continue
            t = type(val).__name__
            if key not in fields:
                fields[key] = {'type': MONGO_TYPE_MAP.get(t, 'string'), 'python_type': t, 'nullable': False}
            if val is None:
                fields[key]['nullable'] = True
            if isinstance(val, list) and val and isinstance(val[0], dict):
                fields[key]['type'] = 'array'
                fields[key]['items'] = 'object'
            if isinstance(val, dict):
                fields[key]['type'] = 'object'
                fields[key]['properties'] = list(val.keys())
    return {
        'collection': collection_name,
        'document_count': len(sample_docs),
        'fields': fields,
    }


class RESTGenIn(BaseModel):
    collection_names: List[str]
    prefix: str = 'v1'
    auth: str = 'jwt'
    features: List[str] = ['pagination', 'sorting', 'filtering']


class GraphQLGenIn(BaseModel):
    collection_names: List[str]


class SDKGenIn(BaseModel):
    collection_names: List[str]
    language: str = 'python'


class PreviewIn(BaseModel):
    collection_name: str
    method: str = 'GET'


class TestEndpointIn(BaseModel):
    endpoint_url: str
    method: str = 'GET'
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None


# ── Schema Discovery ──

@router.get('/schemas')
async def list_schemas(_=Depends(get_current_admin)):
    collections = await db.list_collection_names()
    results = []
    for coll_name in sorted(collections):
        if coll_name.startswith('system.'):
            continue
        try:
            sample_docs = await db[coll_name].find({}, {'_id': 0}).limit(5).to_list(5)
            if not sample_docs:
                continue
            schema = _infer_schema(coll_name, sample_docs)
            results.append(schema)
        except Exception:
            continue
    return results


# ── REST Generator ──

def _generate_rest_router(collections: list, prefix: str, auth: str, features: list) -> str:
    has_pagination = 'pagination' in features
    has_sorting = 'sorting' in features
    has_filtering = 'filtering' in features
    has_search = 'search' in features

    auth_import = 'from auth import get_current_admin' if auth == 'jwt' else ''
    auth_dep = ', dependencies=[Depends(get_current_admin)]' if auth == 'jwt' else ''

    lines = [
        'from fastapi import APIRouter, Depends, HTTPException, Query',
        'from typing import Optional, List, Dict, Any',
        'from pydantic import BaseModel, Field',
        'from db import db',
        'import uuid',
        'from datetime import datetime, timezone',
        '',
        auth_import,
        '',
        f'router = APIRouter(prefix=\'/api/{prefix}\')',
        '',
        'def _now(): return datetime.now(timezone.utc).isoformat()',
        'def _uid(): return str(uuid.uuid4())',
        '',
    ]

    for coll in collections:
        name = coll['collection']
        name_singular = name.rstrip('s') if name.endswith('s') else name
        model_name = ''.join(w.capitalize() for w in name_singular.split('_'))
        fields = coll.get('fields', {})

        lines.append(f'class {model_name}(BaseModel):')
        lines.append(f'    id: str = Field(default_factory=_uid)')
        for fname, finfo in fields.items():
            ptype = finfo.get('python_type', 'str')
            nullable = finfo.get('nullable', False)
            if nullable:
                lines.append(f'    {fname}: Optional[{ptype}] = None')
            else:
                lines.append(f'    {fname}: {ptype}')
        lines.append(f'    created_at: str = Field(default_factory=_now)')
        lines.append('')
        lines.append(f'class {model_name}Create(BaseModel):')
        for fname, finfo in fields.items():
            if fname in ('id', 'created_at', 'updated_at'):
                continue
            ptype = finfo.get('python_type', 'str')
            nullable = finfo.get('nullable', False)
            if nullable:
                lines.append(f'    {fname}: Optional[{ptype}] = None')
            else:
                lines.append(f'    {fname}: {ptype}')
        lines.append('')
        lines.append(f'class {model_name}Update(BaseModel):')
        for fname, finfo in fields.items():
            if fname in ('id', 'created_at'):
                continue
            ptype = finfo.get('python_type', 'str')
            lines.append(f'    {fname}: Optional[{ptype}] = None')
        lines.append('')
        lines.append('')

        pag_params = ''
        if has_pagination:
            pag_params = 'skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)'
        sort_params = ''
        if has_sorting:
            sort_params = 'sort_by: Optional[str] = Query(None), sort_order: int = Query(1)'
        filter_params = ''
        if has_filtering:
            filter_params = 'search: Optional[str] = Query(None)'

        all_params = [p for p in [pag_params, sort_params, filter_params] if p]
        param_str = ', '.join(all_params)
        if param_str:
            param_str = ', ' + param_str

        lines.append(f'@router.get(\'/{name}{param_str}\')')
        if auth == 'jwt':
            lines.append(f'async def list_{name}(_=Depends(get_current_admin){param_str}):')
        else:
            lines.append(f'async def list_{name}({param_str}):')
        lines.append(f'    q: Dict[str, Any] = {{}}')
        if has_filtering:
            lines.append(f'    if search:')
            lines.append(f'        q["$or"] = [{{k: {{\"$regex\": search, \"$options\": \"i\"}}}} for k in {json.dumps([f for f in fields.keys() if fields[f].get("python_type") == "str"])}]')
        if has_sorting:
            lines.append(f'    sort_dir = sort_by if sort_by else "created_at"')
            lines.append(f'    cursor = db.{name}.find(q, {{"_id": 0}}).sort(sort_dir, sort_order)')
        else:
            lines.append(f'    cursor = db.{name}.find(q, {{"_id": 0}})')
        if has_pagination:
            lines.append(f'    total = await db.{name}.count_documents(q)')
            lines.append(f'    items = await cursor.skip(skip).limit(limit).to_list(limit)')
            lines.append(f'    return {{"items": items, "total": total, "skip": skip, "limit": limit}}')
        else:
            lines.append(f'    items = await cursor.to_list(100)')
            lines.append(f'    return items')
        lines.append('')

        lines.append(f'@router.get(\'/{name}/{{item_id}}\')')
        if auth == 'jwt':
            lines.append(f'async def get_{name_singular}(item_id: str, _=Depends(get_current_admin)):')
        else:
            lines.append(f'async def get_{name_singular}(item_id: str):')
        lines.append(f'    doc = await db.{name}.find_one({{"id": item_id}}, {{"_id": 0}})')
        lines.append(f'    if not doc: raise HTTPException(404, "Not found")')
        lines.append(f'    return doc')
        lines.append('')

        lines.append(f'@router.post(\'/{name}\')')
        if auth == 'jwt':
            lines.append(f'async def create_{name_singular}(body: {model_name}Create, _=Depends(get_current_admin)):')
        else:
            lines.append(f'async def create_{name_singular}(body: {model_name}Create):')
        lines.append(f'    doc = body.model_dump()')
        lines.append(f'    doc["id"] = _uid()')
        lines.append(f'    doc["created_at"] = _now()')
        lines.append(f'    await db.{name}.insert_one(doc)')
        lines.append(f'    return doc')
        lines.append('')

        lines.append(f'@router.put(\'/{name}/{{item_id}}\')')
        if auth == 'jwt':
            lines.append(f'async def update_{name_singular}(item_id: str, body: {model_name}Update, _=Depends(get_current_admin)):')
        else:
            lines.append(f'async def update_{name_singular}(item_id: str, body: {model_name}Update):')
        lines.append(f'    existing = await db.{name}.find_one({{"id": item_id}})')
        lines.append(f'    if not existing: raise HTTPException(404, "Not found")')
        lines.append(f'    updates = {{k: v for k, v in body.model_dump().items() if v is not None}}')
        lines.append(f'    updates["updated_at"] = _now()')
        lines.append(f'    await db.{name}.update_one({{"id": item_id}}, {{"$set": updates}})')
        lines.append(f'    return await db.{name}.find_one({{"id": item_id}}, {{"_id": 0}})')
        lines.append('')

        lines.append(f'@router.patch(\'/{name}/{{item_id}}\')')
        if auth == 'jwt':
            lines.append(f'async def patch_{name_singular}(item_id: str, body: {model_name}Update, _=Depends(get_current_admin)):')
        else:
            lines.append(f'async def patch_{name_singular}(item_id: str, body: {model_name}Update):')
        lines.append(f'    existing = await db.{name}.find_one({{"id": item_id}})')
        lines.append(f'    if not existing: raise HTTPException(404, "Not found")')
        lines.append(f'    updates = {{k: v for k, v in body.model_dump(exclude_unset=True).items()}}')
        lines.append(f'    updates["updated_at"] = _now()')
        lines.append(f'    await db.{name}.update_one({{"id": item_id}}, {{"$set": updates}})')
        lines.append(f'    return await db.{name}.find_one({{"id": item_id}}, {{"_id": 0}})')
        lines.append('')

        lines.append(f'@router.delete(\'/{name}/{{item_id}}\')')
        if auth == 'jwt':
            lines.append(f'async def delete_{name_singular}(item_id: str, _=Depends(get_current_admin)):')
        else:
            lines.append(f'async def delete_{name_singular}(item_id: str):')
        lines.append(f'    res = await db.{name}.delete_one({{"id": item_id}})')
        lines.append(f'    if res.deleted_count == 0: raise HTTPException(404, "Not found")')
        lines.append(f'    return {{"deleted": True}}')
        lines.append('')

    return '\n'.join(lines)


@router.post('/generate/rest')
async def generate_rest(body: RESTGenIn, _=Depends(get_current_admin)):
    collections = []
    for coll_name in body.collection_names:
        sample_docs = await db[coll_name].find({}, {'_id': 0}).limit(5).to_list(5)
        if not sample_docs:
            continue
        collections.append(_infer_schema(coll_name, sample_docs))

    code = _generate_rest_router(collections, body.prefix, body.auth, body.features)

    schema_id = _uid()
    await db.api_schemas.insert_one({
        'id': schema_id, 'type': 'rest', 'code': code,
        'collections': body.collection_names, 'prefix': body.prefix,
        'auth': body.auth, 'features': body.features,
        'created_at': _now(),
    })
    return {'schema_id': schema_id, 'code': code, 'collections': [c['collection'] for c in collections]}


# ── GraphQL Generator ──

def _generate_graphql(collections: list) -> str:
    lines = [
        'import strawberry',
        'from strawberry.scalars import JSON',
        'from typing import Optional, List, Any',
        'from db import db',
        'import uuid',
        'from datetime import datetime, timezone',
        '',
        'def _now(): return datetime.now(timezone.utc).isoformat()',
        'def _uid(): return str(uuid.uuid4())',
        '',
    ]

    for coll in collections:
        name = coll['collection']
        type_name = ''.join(w.capitalize() for w in name.split('_'))
        fields = coll.get('fields', {})

        lines.append(f'@strawberry.type')
        lines.append(f'class {type_name}:')
        lines.append(f'    id: str')
        for fname, finfo in fields.items():
            stype = finfo.get('python_type', 'str')
            if stype == 'dict':
                stype = 'JSON'
            elif stype == 'list':
                stype = 'JSON'
            lines.append(f'    {fname}: Optional[{stype}] = None')
        lines.append(f'    created_at: Optional[str] = None')
        lines.append('')

        lines.append(f'@strawberry.input')
        lines.append(f'class {type_name}Input:')
        for fname, finfo in fields.items():
            if fname in ('id', 'created_at', 'updated_at'):
                continue
            stype = finfo.get('python_type', 'str')
            nullable = finfo.get('nullable', False)
            if stype == 'dict':
                stype = 'JSON'
            elif stype == 'list':
                stype = 'JSON'
            if nullable:
                lines.append(f'    {fname}: Optional[{stype}] = None')
            else:
                lines.append(f'    {fname}: {stype}')
        lines.append('')

    lines.append('@strawberry.type')
    lines.append('class Query:')
    for coll in collections:
        name = coll['collection']
        type_name = ''.join(w.capitalize() for w in name.split('_'))
        lines.append(f'    @strawberry.field')
        lines.append(f'    async def {name}(self, skip: int = 0, limit: int = 20) -> List[{type_name}]:')
        lines.append(f'        docs = await db.{name}.find({{}}, {{"_id": 0}}).skip(skip).limit(limit).to_list(limit)')
        lines.append(f'        return [{type_name}(**{{k: v for k, v in d.items() if k != "_id"}}) for d in docs]')
        lines.append('')
        lines.append(f'    @strawberry.field')
        lines.append(f'    async def {name.rstrip("s")}_by_id(self, item_id: str) -> Optional[{type_name}]:')
        lines.append(f'        doc = await db.{name}.find_one({{"id": item_id}}, {{"_id": 0}})')
        lines.append(f'        if not doc: return None')
        lines.append(f'        return {type_name}(**{{k: v for k, v in doc.items() if k != "_id"}})')
        lines.append('')

    lines.append('@strawberry.type')
    lines.append('class Mutation:')
    for coll in collections:
        name = coll['collection']
        type_name = ''.join(w.capitalize() for w in name.split('_'))
        lines.append(f'    @strawberry.mutation')
        lines.append(f'    async def create_{name.rstrip("s")}(self, input: {type_name}Input) -> {type_name}:')
        lines.append(f'        doc = input.__dict__ if hasattr(input, "__dict__") else {{}}')
        lines.append(f'        doc["id"] = _uid()')
        lines.append(f'        doc["created_at"] = _now()')
        lines.append(f'        await db.{name}.insert_one(doc)')
        lines.append(f'        return {type_name}(**doc)')
        lines.append('')
        lines.append(f'    @strawberry.mutation')
        lines.append(f'    async def update_{name.rstrip("s")}(self, item_id: str, input: {type_name}Input) -> Optional[{type_name}]:')
        lines.append(f'        existing = await db.{name}.find_one({{"id": item_id}})')
        lines.append(f'        if not existing: return None')
        lines.append(f'        updates = {{k: v for k, v in (input.__dict__ if hasattr(input, "__dict__") else {{}}).items() if v is not None}}')
        lines.append(f'        updates["updated_at"] = _now()')
        lines.append(f'        await db.{name}.update_one({{"id": item_id}}, {{"$set": updates}})')
        lines.append(f'        doc = await db.{name}.find_one({{"id": item_id}}, {{"_id": 0}})')
        lines.append(f'        return {type_name}(**doc)')
        lines.append('')
        lines.append(f'    @strawberry.mutation')
        lines.append(f'    async def delete_{name.rstrip("s")}(self, item_id: str) -> bool:')
        lines.append(f'        res = await db.{name}.delete_one({{"id": item_id}})')
        lines.append(f'        return res.deleted_count > 0')
        lines.append('')

    lines.append('schema = strawberry.Schema(query=Query, mutation=Mutation)')
    return '\n'.join(lines)


@router.post('/generate/graphql')
async def generate_graphql(body: GraphQLGenIn, _=Depends(get_current_admin)):
    collections = []
    for coll_name in body.collection_names:
        sample_docs = await db[coll_name].find({}, {'_id': 0}).limit(5).to_list(5)
        if not sample_docs:
            continue
        collections.append(_infer_schema(coll_name, sample_docs))

    code = _generate_graphql(collections)

    schema_id = _uid()
    await db.api_schemas.insert_one({
        'id': schema_id, 'type': 'graphql', 'code': code,
        'collections': body.collection_names, 'created_at': _now(),
    })
    return {'schema_id': schema_id, 'code': code}


# ── OpenAPI Generator ──

@router.post('/generate/openapi')
async def generate_openapi(body: GraphQLGenIn, _=Depends(get_current_admin)):
    paths = {}
    schemas = {}

    for coll_name in body.collection_names:
        sample_docs = await db[coll_name].find({}, {'_id': 0}).limit(5).to_list(5)
        if not sample_docs:
            continue

        schema = _infer_schema(coll_name, sample_docs)
        fields = schema.get('fields', {})

        prop_defs = {'id': {'type': 'string'}, 'created_at': {'type': 'string', 'format': 'date-time'}}
        for fname, finfo in fields.items():
            prop_defs[fname] = {'type': finfo.get('type', 'string')}
            if finfo.get('nullable'):
                prop_defs[fname]['nullable'] = True

        schemas[coll_name.title()] = {
            'type': 'object',
            'properties': prop_defs,
        }
        schemas[f'{coll_name.title()}Create'] = {
            'type': 'object',
            'properties': {k: v for k, v in prop_defs.items() if k not in ('id', 'created_at')},
            'required': [k for k, v in prop_defs.items() if k not in ('id', 'created_at') and not v.get('nullable')],
        }

        paths[f'/{coll_name}'] = {
            'get': {
                'summary': f'List {coll_name}',
                'tags': [coll_name],
                'parameters': [
                    {'name': 'skip', 'in': 'query', 'schema': {'type': 'integer', 'default': 0}},
                    {'name': 'limit', 'in': 'query', 'schema': {'type': 'integer', 'default': 20}},
                ],
                'responses': {'200': {'description': 'OK'}},
            },
            'post': {
                'summary': f'Create {coll_name.rstrip("s")}',
                'tags': [coll_name],
                'requestBody': {'content': {'application/json': {'schema': {'$ref': f'#/components/schemas/{coll_name.title()}Create'}}}},
                'responses': {'201': {'description': 'Created'}},
            },
        }
        paths[f'/{coll_name}/{{item_id}}'] = {
            'get': {'summary': f'Get {coll_name.rstrip("s")}', 'tags': [coll_name], 'responses': {'200': {'description': 'OK'}}},
            'put': {'summary': f'Update {coll_name.rstrip("s")}', 'tags': [coll_name], 'responses': {'200': {'description': 'OK'}}},
            'delete': {'summary': f'Delete {coll_name.rstrip("s")}', 'tags': [coll_name], 'responses': {'200': {'description': 'OK'}}},
        }

    spec = {
        'openapi': '3.0.0',
        'info': {'title': 'Getszy Generated API', 'version': '1.0.0'},
        'paths': paths,
        'components': {'schemas': schemas},
    }

    spec_yaml = yaml.dump(spec, default_flow_style=False, sort_keys=False)

    schema_id = _uid()
    await db.api_schemas.insert_one({
        'id': schema_id, 'type': 'openapi', 'code': spec_yaml, 'spec': spec,
        'collections': body.collection_names, 'created_at': _now(),
    })
    return {'schema_id': schema_id, 'spec': spec, 'yaml': spec_yaml}


# ── SDK Generator ──

def _generate_sdk_python(collections: list) -> str:
    lines = [
        'import httpx',
        'from typing import Optional, List, Dict, Any',
        'import time',
        '',
        '',
        'class GetszySDK:',
        '    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):',
        '        self.base_url = base_url.rstrip("/")',
        '        self.headers = {"Content-Type": "application/json"}',
        '        if api_key:',
        '            self.headers["Authorization"] = f"Bearer {api_key}"',
        '        self.timeout = timeout',
        '',
        '    def _request(self, method: str, path: str, retries: int = 3, **kwargs) -> dict:',
        '        for attempt in range(retries):',
        '            try:',
        '                with httpx.AsyncClient(timeout=self.timeout) as client:',
        '                    resp = client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)',
        '                    resp.raise_for_status()',
        '                    return resp.json()',
        '            except httpx.HTTPStatusError as e:',
        '                if e.response.status_code >= 500 and attempt < retries - 1:',
        '                    time.sleep(2 ** attempt)',
        '                    continue',
        '                raise',
        '            except Exception:',
        '                if attempt < retries - 1:',
        '                    time.sleep(2 ** attempt)',
        '                    continue',
        '                raise',
    ]

    for coll in collections:
        name = coll['collection']
        name_singular = name.rstrip('s') if name.endswith('s') else name

        lines.append(f'')
        lines.append(f'    # ── {name.title()} ──')
        lines.append(f'')
        lines.append(f'    async def list_{name}(self, skip: int = 0, limit: int = 20, **filters) -> List[dict]:')
        lines.append(f'        params = {{"skip": skip, "limit": limit, **filters}}')
        lines.append(f'        return await self._request("GET", "/{name}", params=params)')
        lines.append(f'')
        lines.append(f'    async def get_{name_singular}(self, item_id: str) -> dict:')
        lines.append(f'        return await self._request("GET", f"/{name}/{{item_id}}")')
        lines.append(f'')
        lines.append(f'    async def create_{name_singular}(self, data: dict) -> dict:')
        lines.append(f'        return await self._request("POST", "/{name}", json=data)')
        lines.append(f'')
        lines.append(f'    async def update_{name_singular}(self, item_id: str, data: dict) -> dict:')
        lines.append(f'        return await self._request("PUT", f"/{name}/{{item_id}}", json=data)')
        lines.append(f'')
        lines.append(f'    async def patch_{name_singular}(self, item_id: str, data: dict) -> dict:')
        lines.append(f'        return await self._request("PATCH", f"/{name}/{{item_id}}", json=data)')
        lines.append(f'')
        lines.append(f'    async def delete_{name_singular}(self, item_id: str) -> dict:')
        lines.append(f'        return await self._request("DELETE", f"/{name}/{{item_id}}")')
        lines.append(f'')

    return '\n'.join(lines)


def _generate_sdk_javascript(collections: list, lang: str = 'javascript') -> str:
    lines = [
        'class GetszySDK {',
        '  constructor(baseUrl, apiKey = null, timeout = 30000) {',
        '    this.baseUrl = baseUrl.replace(/\\/$/, "");',
        '    this.headers = { "Content-Type": "application/json" };',
        '    if (apiKey) this.headers["Authorization"] = `Bearer ${apiKey}`;',
        '    this.timeout = timeout;',
        '  }',
        '',
        '  async _request(method, path, retries = 3, body = null) {',
        '    for (let i = 0; i < retries; i++) {',
        '      try {',
        '        const opts = { method, headers: this.headers };',
        '        if (body) opts.body = JSON.stringify(body);',
        '        const resp = await fetch(`${this.baseUrl}${path}`, opts);',
        '        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);',
        '        return await resp.json();',
        '      } catch (e) {',
        '        if (i < retries - 1) await new Promise(r => setTimeout(r, 1000 * 2 ** i));',
        '        else throw e;',
        '      }',
        '    }',
        '  }',
        '',
    ]

    for coll in collections:
        name = coll['collection']
        name_singular = name.rstrip('s') if name.endswith('s') else name

        lines.append(f'  // {name.title()}')
        lines.append(f'  async list_{name}(skip = 0, limit = 20, filters = {{}}) {{')
        lines.append(f'    const params = new URLSearchParams({{ skip, limit, ...filters }});')
        lines.append(f'    return this._request("GET", `/{name}?${{params}}`);')
        lines.append(f'  }}')
        lines.append(f'')
        lines.append(f'  async get_{name_singular}(itemId) {{')
        lines.append(f'    return this._request("GET", `/{name}/${{itemId}}`);')
        lines.append(f'  }}')
        lines.append(f'')
        lines.append(f'  async create_{name_singular}(data) {{')
        lines.append(f'    return this._request("POST", "/{name}", data);')
        lines.append(f'  }}')
        lines.append(f'')
        lines.append(f'  async update_{name_singular}(itemId, data) {{')
        lines.append(f'    return this._request("PUT", `/{name}/${{itemId}}`, data);')
        lines.append(f'  }}')
        lines.append(f'')
        lines.append(f'  async delete_{name_singular}(itemId) {{')
        lines.append(f'    return this._request("DELETE", `/{name}/${{itemId}}`);')
        lines.append(f'  }}')
        lines.append(f'')

    if lang == 'typescript':
        lines.append('}')
        lines.append('')
        lines.append('export default GetszySDK;')
    else:
        lines.append('}')
        lines.append('')
        lines.append('module.exports = { GetszySDK };')

    return '\n'.join(lines)


@router.post('/generate/sdk')
async def generate_sdk(body: SDKGenIn, _=Depends(get_current_admin)):
    collections = []
    for coll_name in body.collection_names:
        sample_docs = await db[coll_name].find({}, {'_id': 0}).limit(5).to_list(5)
        if not sample_docs:
            continue
        collections.append(_infer_schema(coll_name, sample_docs))

    if body.language == 'python':
        code = _generate_sdk_python(collections)
    else:
        code = _generate_sdk_javascript(collections, body.language)

    schema_id = _uid()
    await db.api_schemas.insert_one({
        'id': schema_id, 'type': f'sdk_{body.language}', 'code': code,
        'collections': body.collection_names, 'language': body.language,
        'created_at': _now(),
    })
    return {'schema_id': schema_id, 'code': code, 'language': body.language}


# ── Generated Schema Management ──

@router.get('/generated')
async def list_generated(_=Depends(get_current_admin)):
    schemas = await db.api_schemas.find({}, {'_id': 0, 'code': 0}).sort('created_at', -1).to_list(100)
    return schemas


@router.get('/generated/{schema_id}')
async def get_generated(schema_id: str, _=Depends(get_current_admin)):
    schema = await db.api_schemas.find_one({'id': schema_id}, {'_id': 0})
    if not schema:
        raise HTTPException(404, 'Schema not found')
    return schema


@router.delete('/generated/{schema_id}')
async def delete_generated(schema_id: str, _=Depends(get_current_admin)):
    res = await db.api_schemas.delete_one({'id': schema_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Schema not found')
    return {'deleted': True}


# ── Preview ──

@router.post('/preview')
async def preview_endpoint(body: PreviewIn, _=Depends(get_current_admin)):
    sample_docs = await db[body.collection_name].find({}, {'_id': 0}).limit(5).to_list(5)
    if not sample_docs:
        raise HTTPException(404, f'Collection {body.collection_name} not found or empty')
    schema = _infer_schema(body.collection_name, sample_docs)
    fields = schema.get('fields', {})
    name = body.collection_name
    name_singular = name.rstrip('s') if name.endswith('s') else name

    method = body.method.upper()
    if method == 'GET':
        if '{id}' in name:
            endpoint = f'GET /api/{name}/{{item_id}}'
            description = f'Retrieve a single {name_singular} by ID'
        else:
            endpoint = f'GET /api/{name}?skip=0&limit=20'
            description = f'List all {name} with pagination'
    elif method == 'POST':
        endpoint = f'POST /api/{name}'
        description = f'Create a new {name_singular}'
    elif method in ('PUT', 'PATCH'):
        endpoint = f'{method} /api/{name}/{{item_id}}'
        description = f'{"Replace" if method == "PUT" else "Partially update"} a {name_singular}'
    elif method == 'DELETE':
        endpoint = f'DELETE /api/{name}/{{item_id}}'
        description = f'Delete a {name_singular}'
    else:
        raise HTTPException(400, f'Invalid method: {method}')

    field_defs = []
    for fname, finfo in fields.items():
        field_defs.append({
            'name': fname,
            'type': finfo.get('python_type', 'str'),
            'nullable': finfo.get('nullable', False),
        })

    return {
        'endpoint': endpoint,
        'method': method,
        'description': description,
        'collection': name,
        'fields': field_defs,
        'sample_doc': sample_docs[0] if sample_docs else {},
    }


# ── Test ──

@router.post('/test')
async def test_endpoint(body: TestEndpointIn, _=Depends(get_current_admin)):
    import httpx as _httpx
    try:
        async with _httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=body.method.upper(),
                url=body.endpoint_url,
                headers=body.headers or {},
                json=body.body if body.body else None,
            )
            return {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'body': resp.json() if 'application/json' in resp.headers.get('content-type', '') else resp.text,
            }
    except Exception as e:
        return {'error': str(e)}


# ── Deploy ──

@router.post('/deploy/{schema_id}')
async def deploy_schema(schema_id: str, _=Depends(get_current_admin)):
    schema = await db.api_schemas.find_one({'id': schema_id}, {'_id': 0})
    if not schema:
        raise HTTPException(404, 'Schema not found')
    import os
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_apis')
    os.makedirs(out_dir, exist_ok=True)
    filename = f'{schema_id}.py'
    filepath = os.path.join(out_dir, filename)
    with open(filepath, 'w') as f:
        f.write(schema.get('code', ''))
    await db.api_schemas.update_one({'id': schema_id}, {'$set': {
        'deployed': True, 'deployed_path': filepath, 'deployed_at': _now(),
    }})
    return {'deployed': True, 'path': filepath, 'schema_id': schema_id}
