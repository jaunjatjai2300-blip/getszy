from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId
from db import db
from auth import get_current_admin
import httpx, os, json

router = APIRouter(prefix="/admin/ai-platform", tags=["ai-platform"])

def _id(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

# ─── Prompt Library ──────────────────────────────────────────────────────────

class PromptIn(BaseModel):
    title: str
    category: str = "general"
    prompt: str
    variables: List[str] = []
    tags: List[str] = []
    model: str = "any"
    is_public: bool = False

@router.get("/prompts", dependencies=[Depends(get_current_admin)])
async def list_prompts(category: str = "", search: str = "", limit: int = 50):
    q = {}
    if category:
        q["category"] = category
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"prompt": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}},
        ]
    docs = await db.gs_prompts.find(q).sort("created_at", -1).limit(limit).to_list(limit)
    return [_id(d) for d in docs]

@router.post("/prompts", dependencies=[Depends(get_current_admin)])
async def create_prompt(body: PromptIn):
    doc = {**body.dict(), "created_at": datetime.utcnow().isoformat(), "uses": 0}
    r = await db.gs_prompts.insert_one(doc)
    return {"id": str(r.inserted_id)}

@router.put("/prompts/{pid}", dependencies=[Depends(get_current_admin)])
async def update_prompt(pid: str, body: PromptIn):
    await db.gs_prompts.update_one({"_id": ObjectId(pid)}, {"$set": {**body.dict(), "updated_at": datetime.utcnow().isoformat()}})
    return {"ok": True}

@router.delete("/prompts/{pid}", dependencies=[Depends(get_current_admin)])
async def delete_prompt(pid: str):
    await db.gs_prompts.delete_one({"_id": ObjectId(pid)})
    return {"ok": True}

@router.post("/prompts/{pid}/use", dependencies=[Depends(get_current_admin)])
async def use_prompt(pid: str):
    await db.gs_prompts.update_one({"_id": ObjectId(pid)}, {"$inc": {"uses": 1}})
    return {"ok": True}

# ─── Knowledge Base ───────────────────────────────────────────────────────────

class KBDocIn(BaseModel):
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []
    source_url: str = ""

class KBSearchIn(BaseModel):
    query: str
    limit: int = 5

@router.get("/kb", dependencies=[Depends(get_current_admin)])
async def list_kb(category: str = "", search: str = ""):
    q = {}
    if category:
        q["category"] = category
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]
    docs = await db.gs_kb_docs.find(q).sort("created_at", -1).limit(100).to_list(100)
    return [_id(d) for d in docs]

@router.post("/kb", dependencies=[Depends(get_current_admin)])
async def create_kb_doc(body: KBDocIn):
    word_count = len(body.content.split())
    doc = {
        **body.dict(),
        "word_count": word_count,
        "created_at": datetime.utcnow().isoformat(),
    }
    r = await db.gs_kb_docs.insert_one(doc)
    return {"id": str(r.inserted_id)}

@router.put("/kb/{doc_id}", dependencies=[Depends(get_current_admin)])
async def update_kb_doc(doc_id: str, body: KBDocIn):
    word_count = len(body.content.split())
    await db.gs_kb_docs.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**body.dict(), "word_count": word_count, "updated_at": datetime.utcnow().isoformat()}}
    )
    return {"ok": True}

@router.delete("/kb/{doc_id}", dependencies=[Depends(get_current_admin)])
async def delete_kb_doc(doc_id: str):
    await db.gs_kb_docs.delete_one({"_id": ObjectId(doc_id)})
    return {"ok": True}

@router.post("/kb/search", dependencies=[Depends(get_current_admin)])
async def search_kb(body: KBSearchIn):
    q = {"$or": [
        {"title": {"$regex": body.query, "$options": "i"}},
        {"content": {"$regex": body.query, "$options": "i"}},
        {"tags": {"$in": [body.query]}},
    ]}
    docs = await db.gs_kb_docs.find(q).limit(body.limit).to_list(body.limit)
    return [_id(d) for d in docs]

@router.get("/kb/stats", dependencies=[Depends(get_current_admin)])
async def kb_stats():
    total = await db.gs_kb_docs.count_documents({})
    cats = await db.gs_kb_docs.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]).to_list(20)
    total_words = await db.gs_kb_docs.aggregate([
        {"$group": {"_id": None, "words": {"$sum": "$word_count"}}}
    ]).to_list(1)
    return {
        "total_docs": total,
        "total_words": total_words[0]["words"] if total_words else 0,
        "categories": [{"name": c["_id"] or "general", "count": c["count"]} for c in cats],
    }

# ─── AI Memory ───────────────────────────────────────────────────────────────

class MemoryIn(BaseModel):
    key: str
    value: str
    category: str = "general"
    user_id: str = "system"
    ttl_days: int = 0

@router.get("/memory", dependencies=[Depends(get_current_admin)])
async def list_memory(user_id: str = "", category: str = "", limit: int = 100):
    q = {}
    if user_id:
        q["user_id"] = user_id
    if category:
        q["category"] = category
    docs = await db.gs_ai_memory.find(q).sort("created_at", -1).limit(limit).to_list(limit)
    return [_id(d) for d in docs]

@router.post("/memory", dependencies=[Depends(get_current_admin)])
async def create_memory(body: MemoryIn):
    doc = {**body.dict(), "created_at": datetime.utcnow().isoformat(), "access_count": 0}
    r = await db.gs_ai_memory.insert_one(doc)
    return {"id": str(r.inserted_id)}

@router.delete("/memory/{mem_id}", dependencies=[Depends(get_current_admin)])
async def delete_memory(mem_id: str):
    await db.gs_ai_memory.delete_one({"_id": ObjectId(mem_id)})
    return {"ok": True}

@router.delete("/memory", dependencies=[Depends(get_current_admin)])
async def clear_memory(user_id: str = "", category: str = ""):
    q = {}
    if user_id:
        q["user_id"] = user_id
    if category:
        q["category"] = category
    r = await db.gs_ai_memory.delete_many(q)
    return {"deleted": r.deleted_count}

@router.get("/memory/stats", dependencies=[Depends(get_current_admin)])
async def memory_stats():
    total = await db.gs_ai_memory.count_documents({})
    by_user = await db.gs_ai_memory.aggregate([
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
    ]).to_list(20)
    by_cat = await db.gs_ai_memory.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]).to_list(20)
    return {
        "total": total,
        "by_user": [{"user": u["_id"], "count": u["count"]} for u in by_user],
        "by_category": [{"cat": c["_id"], "count": c["count"]} for c in by_cat],
    }

# ─── AI Playground ────────────────────────────────────────────────────────────

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

class PlaygroundIn(BaseModel):
    model: str
    messages: List[Any]
    temperature: float = 0.7
    max_tokens: int = 1024
    system_prompt: str = ""

@router.get("/playground/models", dependencies=[Depends(get_current_admin)])
async def playground_models():
    free_models = [
        {"id": "meta-llama/llama-3.3-70b-instruct:free",    "name": "Llama 3.3 70B",         "provider": "openrouter", "ctx": 131072},
        {"id": "google/gemma-3-27b-it:free",                 "name": "Gemma 3 27B",            "provider": "openrouter", "ctx": 8192},
        {"id": "mistralai/mistral-7b-instruct:free",         "name": "Mistral 7B",             "provider": "openrouter", "ctx": 32768},
        {"id": "microsoft/phi-4-reasoning:free",             "name": "Phi-4 Reasoning",        "provider": "openrouter", "ctx": 16384},
        {"id": "deepseek/deepseek-r1:free",                  "name": "DeepSeek R1",            "provider": "openrouter", "ctx": 163840},
        {"id": "qwen/qwen3-14b:free",                        "name": "Qwen3 14B",              "provider": "openrouter", "ctx": 40960},
        {"id": "llama-3.3-70b-versatile",                   "name": "Llama 3.3 70B (Groq)",   "provider": "groq",       "ctx": 128000},
        {"id": "llama-3.1-8b-instant",                      "name": "Llama 3.1 8B (Groq)",    "provider": "groq",       "ctx": 128000},
        {"id": "mixtral-8x7b-32768",                        "name": "Mixtral 8x7B (Groq)",    "provider": "groq",       "ctx": 32768},
        {"id": "gemma2-9b-it",                              "name": "Gemma2 9B (Groq)",       "provider": "groq",       "ctx": 8192},
    ]
    return {"models": free_models, "openrouter_set": bool(OPENROUTER_KEY), "groq_set": bool(GROQ_KEY)}

@router.post("/playground/run", dependencies=[Depends(get_current_admin)])
async def playground_run(body: PlaygroundIn):
    msgs = list(body.messages)
    if body.system_prompt:
        msgs = [{"role": "system", "content": body.system_prompt}] + msgs

    is_groq = body.model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it", "llama-guard-3-8b"]

    if is_groq:
        if not GROQ_KEY:
            raise HTTPException(400, "GROQ_API_KEY not set")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    else:
        if not OPENROUTER_KEY:
            raise HTTPException(400, "OPENROUTER_API_KEY not set")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}

    payload = {"model": body.model, "messages": msgs, "temperature": body.temperature, "max_tokens": body.max_tokens}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            await db.gs_playground_history.insert_one({
                "model": body.model,
                "messages_count": len(msgs),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "created_at": datetime.utcnow().isoformat(),
            })
            return {"content": content, "usage": usage, "model": body.model}
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, f"AI API error: {e.response.text[:300]}")

@router.get("/playground/history", dependencies=[Depends(get_current_admin)])
async def playground_history(limit: int = 20):
    docs = await db.gs_playground_history.find().sort("created_at", -1).limit(limit).to_list(limit)
    return [_id(d) for d in docs]
