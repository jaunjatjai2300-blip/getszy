"""Downloadable starter kit generators for Build Studio.

Generates real, ready-to-run starter zips:
  - mobileapp   -> React Native (Expo) starter with brand colors from prompt
  - fullstack   -> FastAPI + React + Mongo starter with a domain-specific model
  - blog        -> Static multi-post blog (HTML) generated from a niche
"""
import io
import json
import re
import zipfile
from typing import Dict, Any, List
from llm_provider import chat_completion


async def gen_mobileapp_zip(prompt: str, app_name: str) -> bytes:
    system = (
        'You customize a React Native (Expo) starter for an Indian creator. '
        'Given a prompt, output ONLY JSON: {tagline, primary_color (hex), accent_color (hex), '
        'screens: [{name, purpose, sample_content}], features (array), package_name (kebab-case)}.'
    )
    raw = await chat_completion(system, prompt, temperature=0.6)
    spec = _parse_json(raw) or {'tagline': prompt[:80], 'primary_color': '#1e8e8e',
                                 'accent_color': '#e0a458', 'screens': [{'name': 'Home', 'purpose': 'landing', 'sample_content': prompt}],
                                 'features': ['auth', 'profile'], 'package_name': _slug(app_name)}
    files: Dict[str, str] = {}
    pkg = spec.get('package_name') or _slug(app_name)
    files['package.json'] = json.dumps({
        'name': pkg, 'version': '1.0.0', 'main': 'node_modules/expo/AppEntry.js',
        'scripts': {'start': 'expo start', 'android': 'expo start --android', 'ios': 'expo start --ios', 'web': 'expo start --web'},
        'dependencies': {'expo': '~52.0.0', 'expo-status-bar': '~2.0.0',
                         'react': '18.3.1', 'react-native': '0.76.3',
                         '@react-navigation/native': '^7.0.0', '@react-navigation/native-stack': '^7.0.0',
                         'react-native-screens': '~4.4.0', 'react-native-safe-area-context': '4.12.0'},
    }, indent=2)
    files['app.json'] = json.dumps({'expo': {'name': app_name, 'slug': pkg,
        'version': '1.0.0', 'orientation': 'portrait',
        'primaryColor': spec.get('primary_color', '#1e8e8e'),
        'icon': './assets/icon.png', 'splash': {'image': './assets/splash.png', 'resizeMode': 'contain'},
        'ios': {'supportsTablet': True}, 'android': {'adaptiveIcon': {'backgroundColor': spec.get('primary_color', '#1e8e8e')}}}}, indent=2)
    files['babel.config.js'] = 'module.exports = function(api){ api.cache(true); return { presets: ["babel-preset-expo"] }; };\n'
    files['App.js'] = _rn_app_js(spec)
    files['screens/HomeScreen.js'] = _rn_home_screen(spec)
    for i, sc in enumerate(spec.get('screens', [])[1:6], 1):
        name = _clean_screen_name(sc.get('name', f'Screen{i}'))
        files[f'screens/{name}Screen.js'] = _rn_generic_screen(name, sc.get('purpose', ''), sc.get('sample_content', ''), spec)
    files['README.md'] = _mobile_readme(app_name, spec, prompt)
    files['.gitignore'] = 'node_modules/\n.expo/\ndist/\n*.log\n.DS_Store\n'
    return _zip(files)


async def gen_fullstack_zip(prompt: str, app_name: str) -> bytes:
    system = (
        'You customize a FastAPI + React + MongoDB starter for an Indian founder. '
        'Given a prompt, output ONLY JSON: {tagline, primary_entity (singular kebab, e.g. "task"), '
        'entity_fields: [{name, type (str|int|float|bool|datetime), sample}], '
        'brand_color (hex), features (array), package_name (kebab-case)}.'
    )
    raw = await chat_completion(system, prompt, temperature=0.6)
    spec = _parse_json(raw) or {'tagline': prompt[:80], 'primary_entity': 'item',
                                 'entity_fields': [{'name': 'title', 'type': 'str', 'sample': 'Sample'},
                                                    {'name': 'notes', 'type': 'str', 'sample': ''}],
                                 'brand_color': '#1e8e8e', 'features': ['crud'], 'package_name': _slug(app_name)}
    ent = _slug(spec.get('primary_entity') or 'item')
    files: Dict[str, str] = {}
    files['README.md'] = _fullstack_readme(app_name, spec, prompt)
    files['docker-compose.yml'] = _fs_docker_compose(spec)
    files['backend/requirements.txt'] = 'fastapi==0.115.0\nuvicorn[standard]==0.32.0\nmotor==3.6.0\npydantic==2.9.2\npython-dotenv==1.0.1\n'
    files['backend/server.py'] = _fs_backend(spec, ent)
    files['backend/.env.example'] = 'MONGO_URL=mongodb://localhost:27017\nDB_NAME=' + _slug(app_name) + '\n'
    files['backend/Dockerfile'] = 'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8001\nCMD ["uvicorn","server:app","--host","0.0.0.0","--port","8001"]\n'
    files['frontend/package.json'] = json.dumps({
        'name': _slug(app_name) + '-frontend', 'version': '1.0.0',
        'scripts': {'dev': 'vite', 'build': 'vite build', 'preview': 'vite preview'},
        'dependencies': {'react': '^18.3.1', 'react-dom': '^18.3.1', 'axios': '^1.7.7'},
        'devDependencies': {'@vitejs/plugin-react': '^4.3.3', 'vite': '^5.4.10'}}, indent=2)
    files['frontend/index.html'] = _fs_index_html(app_name, spec)
    files['frontend/vite.config.js'] = "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({ plugins: [react()], server: { proxy: { '/api': 'http://localhost:8001' } } });\n"
    files['frontend/src/main.jsx'] = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\nReactDOM.createRoot(document.getElementById('root')).render(<App/>);\n"
    files['frontend/src/App.jsx'] = _fs_frontend_app(app_name, spec, ent)
    files['frontend/src/index.css'] = _fs_frontend_css(spec)
    files['.gitignore'] = 'node_modules/\n__pycache__/\n*.pyc\n.env\ndist/\n.DS_Store\n'
    return _zip(files)


async def gen_blog_zip(prompt: str, site_name: str) -> bytes:
    system = (
        'You are a content director creating a starter blog for an Indian audience. '
        'Given a niche prompt, output ONLY JSON: {tagline, brand_color (hex), '
        'posts: [4 posts each with {slug, title, excerpt, body_markdown (300-500 words with subheadings), hero_image_prompt}]}.'
    )
    raw = await chat_completion(system, prompt, temperature=0.7)
    spec = _parse_json(raw)
    if not spec or not spec.get('posts'):
        spec = {'tagline': prompt[:80], 'brand_color': '#1e8e8e', 'posts': [
            {'slug': 'welcome', 'title': 'Welcome to ' + site_name, 'excerpt': prompt[:120],
             'body_markdown': '## Getting started\n\n' + prompt, 'hero_image_prompt': prompt}
        ]}
    files: Dict[str, str] = {}
    files['index.html'] = _blog_index_html(site_name, spec)
    for post in spec.get('posts', []):
        slug = _slug(post.get('slug') or post.get('title', 'post'))
        files[f'posts/{slug}.html'] = _blog_post_html(site_name, spec, post)
    files['README.md'] = f'# {site_name}\n\nStatic blog scaffold generated by Getszy Build Studio.\n\nOpen `index.html` in browser or deploy anywhere (Netlify, Vercel, GitHub Pages).\n\n## Prompt\n{prompt}\n'
    return _zip(files)


# ----------------------- helpers -----------------------

def _zip(files: Dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for path, content in files.items():
            z.writestr(path, content)
    buf.seek(0)
    return buf.getvalue()


def _parse_json(raw: str) -> Dict[str, Any] | None:
    if not raw: return None
    s = raw.find('{'); e = raw.rfind('}')
    if s == -1: return None
    try: return json.loads(raw[s:e+1])
    except Exception: return None


def _slug(s: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', (s or '').lower()).strip('-')
    return s or 'app'


def _clean_screen_name(s: str) -> str:
    return re.sub(r'[^A-Za-z]', '', s.title()) or 'Extra'


# --- React Native templates ---

def _rn_app_js(spec: Dict[str, Any]) -> str:
    screens = spec.get('screens', [])
    imports = []
    stack_screens = []
    for i, sc in enumerate(screens[:6]):
        name = _clean_screen_name(sc.get('name', f'Screen{i}')) if i > 0 else 'Home'
        imports.append(f"import {name}Screen from './screens/{name}Screen';")
        stack_screens.append(f'          <Stack.Screen name="{name}" component={{{name}Screen}} />')
    if not stack_screens:
        imports.append("import HomeScreen from './screens/HomeScreen';")
        stack_screens.append('          <Stack.Screen name="Home" component={HomeScreen} />')
    return (
        "import { NavigationContainer } from '@react-navigation/native';\n"
        "import { createNativeStackNavigator } from '@react-navigation/native-stack';\n"
        + '\n'.join(imports) + "\n\n"
        "const Stack = createNativeStackNavigator();\n\n"
        "export default function App() {\n"
        "  return (\n"
        "    <NavigationContainer>\n"
        f"      <Stack.Navigator screenOptions={{{{ headerStyle: {{{{ backgroundColor: '{spec.get('primary_color', '#1e8e8e')}' }}}}, headerTintColor: '#fff' }}}}>\n"
        + '\n'.join(stack_screens) + '\n'
        "      </Stack.Navigator>\n    </NavigationContainer>\n  );\n}\n"
    )


def _rn_home_screen(spec: Dict[str, Any]) -> str:
    tagline = (spec.get('tagline') or 'Welcome').replace('`', "'")
    features = spec.get('features', [])
    feature_items = ''.join([f"        <Text style={{styles.feature}}>* {str(f)[:80]}</Text>\n" for f in features[:8]])
    primary = spec.get('primary_color', '#1e8e8e')
    accent = spec.get('accent_color', '#e0a458')
    return (
        "import { StyleSheet, Text, View, ScrollView, TouchableOpacity } from 'react-native';\n"
        "export default function HomeScreen({ navigation }) {\n"
        "  return (\n"
        "    <ScrollView contentContainerStyle={styles.container}>\n"
        f"      <Text style={{styles.tagline}}>{tagline}</Text>\n"
        f"{feature_items}"
        f"      <TouchableOpacity style={{styles.cta}} onPress={{() => navigation.navigate('Home')}}><Text style={{styles.ctaText}}>Get Started</Text></TouchableOpacity>\n"
        "    </ScrollView>\n  );\n}\n"
        "const styles = StyleSheet.create({\n"
        "  container: { padding: 24, backgroundColor: '#fff' },\n"
        f"  tagline: {{ fontSize: 22, fontWeight: '700', marginBottom: 16, color: '{primary}' }},\n"
        "  feature: { fontSize: 16, marginVertical: 4, color: '#333' },\n"
        f"  cta: {{ marginTop: 24, backgroundColor: '{accent}', padding: 14, borderRadius: 12, alignItems: 'center' }},\n"
        "  ctaText: { color: '#fff', fontWeight: '700', fontSize: 16 },\n"
        "});\n"
    )


def _rn_generic_screen(name: str, purpose: str, sample: str, spec: Dict[str, Any]) -> str:
    return (
        "import { StyleSheet, Text, View, ScrollView } from 'react-native';\n"
        f"export default function {name}Screen() {{\n"
        "  return (\n"
        "    <ScrollView contentContainerStyle={{ padding: 24 }}>\n"
        f"      <Text style={{{{ fontSize: 22, fontWeight: '700', color: '{spec.get('primary_color', '#1e8e8e')}' }}}}>{name}</Text>\n"
        f"      <Text style={{{{ marginTop: 8, color: '#666' }}}}>{purpose[:120]}</Text>\n"
        f"      <Text style={{{{ marginTop: 16, lineHeight: 22 }}}}>{sample[:400]}</Text>\n"
        "    </ScrollView>\n"
        "  );\n}\n"
    )


def _mobile_readme(app_name: str, spec: Dict[str, Any], prompt: str) -> str:
    return (
        f"# {app_name}\n\n{spec.get('tagline', '')}\n\n"
        "Generated by **Getszy Build Studio** (Mobile App track).\n\n"
        "## Quick start\n\n"
        "```bash\nnpm install -g expo-cli\nnpm install\nnpx expo start\n```\n\n"
        "Then scan the QR code with **Expo Go** on your Android/iPhone.\n\n"
        "## Screens\n\n" + '\n'.join([f"- **{s.get('name')}** \u2014 {s.get('purpose', '')}" for s in spec.get('screens', [])]) +
        f"\n\n## Original prompt\n\n> {prompt}\n"
    )


# --- Full-stack templates ---

def _fs_backend(spec: Dict[str, Any], entity: str) -> str:
    fields = spec.get('entity_fields', [])
    py_types = {'str': 'str', 'int': 'int', 'float': 'float', 'bool': 'bool', 'datetime': 'str'}
    field_lines = '\n'.join([f"    {f['name']}: {py_types.get(f['type'], 'str')} = ''" for f in fields])
    Entity = entity.title()
    return (
        "import os, uuid\nfrom datetime import datetime, timezone\n"
        "from fastapi import FastAPI, HTTPException\nfrom fastapi.middleware.cors import CORSMiddleware\n"
        "from pydantic import BaseModel\nfrom motor.motor_asyncio import AsyncIOMotorClient\n"
        "from typing import List\n\n"
        "MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')\n"
        "DB_NAME = os.environ.get('DB_NAME', 'app')\n"
        "client = AsyncIOMotorClient(MONGO_URL)\ndb = client[DB_NAME]\n\n"
        f"class {Entity}(BaseModel):\n    id: str = ''\n{field_lines}\n    created_at: str = ''\n\n"
        f"class {Entity}In(BaseModel):\n{field_lines}\n\n"
        "app = FastAPI()\napp.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])\n\n"
        f"@app.get('/api/{entity}s', response_model=List[{Entity}])\nasync def list_items():\n"
        f"    docs = await db.{entity}s.find({{}}, {{'_id': 0}}).to_list(200)\n    return docs\n\n"
        f"@app.post('/api/{entity}s', response_model={Entity})\nasync def create_item(body: {Entity}In):\n"
        f"    doc = body.model_dump()\n    doc['id'] = str(uuid.uuid4())\n"
        "    doc['created_at'] = datetime.now(timezone.utc).isoformat()\n"
        f"    await db.{entity}s.insert_one(doc)\n    doc.pop('_id', None)\n    return doc\n\n"
        f"@app.delete('/api/{entity}s/{{item_id}}')\nasync def delete_item(item_id: str):\n"
        f"    res = await db.{entity}s.delete_one({{'id': item_id}})\n    return {{'deleted': res.deleted_count}}\n"
    )


def _fs_docker_compose(spec: Dict[str, Any]) -> str:
    return (
        "services:\n  mongo:\n    image: mongo:7\n    ports: ['27017:27017']\n"
        "  backend:\n    build: ./backend\n    ports: ['8001:8001']\n    environment:\n      MONGO_URL: mongodb://mongo:27017\n      DB_NAME: app\n    depends_on: [mongo]\n"
    )


def _fs_frontend_app(app_name: str, spec: Dict[str, Any], entity: str) -> str:
    fields = spec.get('entity_fields', [])
    inputs = '\n'.join([f"        <input placeholder='{f['name']}' value={{form.{f['name']} || ''}} onChange={{(e) => setForm({{ ...form, {f['name']}: e.target.value }})}} />" for f in fields])
    row_cells = ' \u00b7 '.join([f"{{item.{f['name']}}}" for f in fields])
    return (
        "import { useEffect, useState } from 'react';\nimport axios from 'axios';\n"
        f"const API = '/api/{entity}s';\n\n"
        "export default function App() {\n"
        "  const [items, setItems] = useState([]);\n  const [form, setForm] = useState({});\n"
        "  const load = async () => { const r = await axios.get(API); setItems(r.data); };\n"
        "  useEffect(() => { load(); }, []);\n"
        "  const add = async () => { await axios.post(API, form); setForm({}); load(); };\n"
        "  const del = async (id) => { await axios.delete(`${API}/${id}`); load(); };\n"
        "  return (\n    <div className='app'>\n"
        f"      <h1>{app_name}</h1>\n"
        f"      <p>{spec.get('tagline', '')}</p>\n"
        "      <div className='form'>\n" + inputs + "\n"
        "        <button onClick={add}>Add</button>\n"
        "      </div>\n"
        "      <ul>{items.map(item => (\n"
        f"        <li key={{item.id}}>{row_cells} <button onClick={{() => del(item.id)}}>x</button></li>\n"
        "      ))}</ul>\n"
        "    </div>\n  );\n}\n"
    )


def _fs_frontend_css(spec: Dict[str, Any]) -> str:
    return (
        f":root {{ --brand: {spec.get('brand_color', '#1e8e8e')}; }}\n"
        "* { box-sizing: border-box; }\nbody { font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f7f7f9; }\n"
        ".app { max-width: 720px; margin: 40px auto; padding: 24px; background: white; border-radius: 16px; }\n"
        "h1 { color: var(--brand); margin-top: 0; }\n"
        ".form { display: grid; gap: 8px; margin: 16px 0; }\n"
        ".form input { padding: 10px; border: 1px solid #ddd; border-radius: 8px; }\n"
        ".form button, li button { padding: 10px 18px; background: var(--brand); color: white; border: 0; border-radius: 8px; cursor: pointer; }\n"
        "li { list-style: none; padding: 12px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; }\n"
    )


def _fs_index_html(app_name: str, spec: Dict[str, Any]) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{app_name}</title><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "</head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>\n"
    )


def _fullstack_readme(app_name: str, spec: Dict[str, Any], prompt: str) -> str:
    return (
        f"# {app_name}\n\n{spec.get('tagline', '')}\n\n"
        "Generated by **Getszy Build Studio** (Full-Stack track). Uses FastAPI + React + MongoDB.\n\n"
        "## Quick start\n\n"
        "```bash\ndocker compose up --build\n```\n\n"
        f"- Backend: http://localhost:8001 (API prefix: /api/{spec.get('primary_entity','item')}s)\n"
        "- Frontend: `cd frontend && npm install && npm run dev` \u2192 http://localhost:5173\n\n"
        f"## Primary entity: `{spec.get('primary_entity','item')}`\n\nFields:\n\n" +
        '\n'.join([f"- **{f['name']}** ({f['type']})" for f in spec.get('entity_fields', [])]) +
        f"\n\n## Original prompt\n\n> {prompt}\n"
    )


# --- Blog templates ---

def _blog_index_html(site_name: str, spec: Dict[str, Any]) -> str:
    color = spec.get('brand_color', '#1e8e8e')
    posts = spec.get('posts', [])
    cards = ''.join([
        f'<a href="posts/{_slug(p.get("slug") or p.get("title", "post"))}.html" class="card">'
        f'<h3>{p.get("title", "Post")}</h3><p>{p.get("excerpt", "")[:200]}</p><span>Read more \u2192</span></a>'
        for p in posts])
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{site_name}</title><meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>:root{{--brand:{color}}}*{{box-sizing:border-box}}body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#faf9f7;color:#222}}"
        "header{background:var(--brand);color:white;padding:56px 24px;text-align:center}h1{margin:0;font-size:44px}"
        ".grid{max-width:1000px;margin:40px auto;padding:0 24px;display:grid;gap:20px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}"
        ".card{display:block;padding:24px;background:white;border-radius:16px;text-decoration:none;color:inherit;box-shadow:0 6px 20px rgba(0,0,0,.06);transition:transform .2s}"
        ".card:hover{transform:translateY(-4px)}.card h3{margin-top:0;color:var(--brand)}.card span{color:var(--brand);font-weight:600}"
        "footer{text-align:center;padding:32px;color:#888;font-size:14px}</style></head>"
        f"<body><header><h1>{site_name}</h1><p>{spec.get('tagline', '')}</p></header>"
        f"<main class='grid'>{cards}</main>"
        "<footer>Generated by Getszy Build Studio</footer></body></html>\n"
    )


def _blog_post_html(site_name: str, spec: Dict[str, Any], post: Dict[str, Any]) -> str:
    color = spec.get('brand_color', '#1e8e8e')
    body_html = _md_to_html(post.get('body_markdown', ''))
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{post.get('title','Post')} \u00b7 {site_name}</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>:root{{--brand:{color}}}body{{font-family:system-ui,-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:40px 24px;line-height:1.7;color:#222}}"
        "h1{color:var(--brand)}h2{color:var(--brand);margin-top:32px}a{color:var(--brand)}"
        "img{max-width:100%;border-radius:12px}</style></head>"
        f"<body><p><a href='../index.html'>\u2190 Back to {site_name}</a></p>"
        f"<h1>{post.get('title','Post')}</h1>"
        f"<p><em>{post.get('excerpt','')}</em></p>{body_html}</body></html>\n"
    )


def _md_to_html(md: str) -> str:
    lines = (md or '').split('\n')
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('## '): out.append(f'<h2>{s[3:]}</h2>')
        elif s.startswith('# '): out.append(f'<h1>{s[2:]}</h1>')
        elif s.startswith('- '): out.append(f'<li>{s[2:]}</li>')
        elif s: out.append(f'<p>{s}</p>')
    return '\n'.join(out)
