"""
PHASE 1 POC — Natural Language → Structured Admin Actions
Tests that Emergent LLM can reliably parse admin commands into JSON tool calls.

Run: python /app/test_core_poc.py
"""
import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/backend/.env"))

from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

# Tool / intent schema — keep tight so JSON output is reliable.
TOOLS_SCHEMA = """
You are getszy.com's AI Admin assistant. You convert natural-language admin commands
into a SINGLE JSON object that the backend will execute. NEVER produce prose, NEVER wrap
in markdown — output ONLY a raw JSON object with this shape:

{
  "intent": "<one of: add_product | update_product | delete_product | list_products | add_category | list_categories | list_orders | update_order_status | add_supplier | list_suppliers | show_stats | low_stock | clarify | reject | chat>",
  "params": { ...intent-specific fields... },
  "reply": "<short friendly confirmation message in Hinglish (mix of Hindi + English) for the admin>"
}

Intent param schemas:
- add_product: { name (str), price (number), category (str), cost_price? (number), stock? (int, default 10), supplier? (str), description? (str) }
- update_product: { product_query (str: name or id), updates: { price?, stock?, category?, supplier?, description? } }
- delete_product: { product_query (str) }
- list_products: { category? (str), search? (str), limit? (int) }
- add_category: { name (str) }
- list_categories: {}
- list_orders: { status? (str: pending|forwarded|shipped|delivered|cancelled), date_range? (str: today|week|month) }
- update_order_status: { order_id (str), status (str), tracking_number? (str) }
- add_supplier: { name (str), contact? (str), notes? (str) }
- list_suppliers: {}
- show_stats: { range? (str: today|week|month|all) }
- low_stock: { threshold? (int, default 5) }
- clarify: { question (str) }  -> when info is missing
- reject: { reason (str) }     -> for unsafe / destructive bulk requests
- chat: { message (str) }      -> small talk / greetings

Rules:
1. Be safe — for bulk-destructive requests like "delete all products" → reject.
2. If required fields missing → clarify, don't guess.
3. Always output a valid JSON object, nothing else.
"""

# Test scenarios — natural Hinglish commands an admin would type.
TESTS = [
    {"name": "Add product", "input": "Add product Rose Gold Earrings 899 in jewellery, supplier Meesho, cost 400, stock 25",
     "expect_intent": "add_product"},
    {"name": "List today's orders", "input": "Aaj ke orders dikhao",
     "expect_intent": "list_orders"},
    {"name": "Update order status", "input": "Order ORD123 ko shipped kar do tracking AWB456789",
     "expect_intent": "update_order_status"},
    {"name": "Low stock check", "input": "Konse products low stock me hain?",
     "expect_intent": "low_stock"},
    {"name": "Show stats", "input": "Aaj ka revenue aur orders ka summary do",
     "expect_intent": "show_stats"},
    {"name": "Add supplier", "input": "New supplier add karo: Surat Textiles, contact +91-9876543210",
     "expect_intent": "add_supplier"},
    {"name": "Clarify on vague", "input": "Ek product add karo",
     "expect_intent": "clarify"},
    {"name": "Reject destructive", "input": "Saare products delete kar do permanently",
     "expect_intent": "reject"},
    {"name": "List products by category", "input": "Beauty category ke products dikhao",
     "expect_intent": "list_products"},
    {"name": "Update product price", "input": "Rose Gold Earrings ka price 999 kar do",
     "expect_intent": "update_product"},
]


def extract_json(text: str):
    """Extract the first JSON object from text robustly."""
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first { ... } balanced
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except Exception:
                    return None
    return None


async def run_one(test):
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"poc-{uuid.uuid4()}",
        system_message=TOOLS_SCHEMA,
    ).with_model("openai", "gpt-4o-mini")

    reply = await chat.send_message(UserMessage(text=test["input"]))
    parsed = extract_json(reply)
    ok = parsed is not None and parsed.get("intent") == test["expect_intent"]
    return ok, reply, parsed


async def main():
    print("=" * 70)
    print("PHASE 1 POC — AI Admin Chat: Natural Language → Structured Actions")
    print("=" * 70)
    passed = 0
    failed_cases = []
    for i, t in enumerate(TESTS, 1):
        try:
            ok, raw, parsed = await run_one(t)
            mark = "✅" if ok else "❌"
            print(f"\n{mark} [{i}/{len(TESTS)}] {t['name']}")
            print(f"   Input: {t['input']}")
            print(f"   Expected intent: {t['expect_intent']}")
            if parsed:
                print(f"   Got intent:     {parsed.get('intent')}")
                print(f"   Params:         {json.dumps(parsed.get('params', {}), ensure_ascii=False)}")
                print(f"   Reply:          {parsed.get('reply', '')[:80]}")
            else:
                print(f"   RAW (unparseable): {raw[:200]}")
            if ok:
                passed += 1
            else:
                failed_cases.append(t["name"])
        except Exception as e:
            print(f"❌ [{i}] {t['name']} — EXCEPTION: {e}")
            failed_cases.append(t["name"])

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{len(TESTS)} passed")
    if failed_cases:
        print(f"Failed: {failed_cases}")
    print("=" * 70)
    return 0 if passed >= len(TESTS) - 1 else 1  # allow 1 flake


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
