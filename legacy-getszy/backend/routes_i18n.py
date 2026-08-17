"""Multi-language / i18n service (Tier 3 — universal reach).

Stores UI string translations and can auto-translate batches via the LLM.
Frontend language switcher consumes GET /admin/i18n/keys.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/i18n', tags=['i18n'])

LANGUAGES = [
    {'code': 'en', 'name': 'English'},
    {'code': 'hi', 'name': 'Hindi'},
    {'code': 'hinglish', 'name': 'Hinglish'},
    {'code': 'ta', 'name': 'Tamil'},
    {'code': 'te', 'name': 'Telugu'},
    {'code': 'bn', 'name': 'Bengali'},
    {'code': 'gu', 'name': 'Gujarati'},
    {'code': 'mr', 'name': 'Marathi'},
]

# Built-in fallbacks so the UI works even before translations are added.
DEFAULTS = {
    'hi': {'dashboard': 'डैशबोर्ड', 'orders': 'ऑर्डर', 'products': 'उत्पाद', 'customers': 'ग्राहक', 'settings': 'सेटिंग्स', 'analytics': 'विश्लेषण'},
    'hinglish': {'dashboard': 'Dashboard', 'orders': 'Orders', 'products': 'Products', 'customers': 'Customers', 'settings': 'Settings', 'analytics': 'Analytics'},
    'ta': {'dashboard': 'டாஷ்போர்டு', 'orders': 'ஆர்டர்கள்', 'products': 'பொருட்கள்', 'customers': 'வாடிக்கையாளர்கள்', 'settings': 'அமைப்புகள்', 'analytics': 'பகுப்பாய்வு'},
    'te': {'dashboard': 'డాష్‌బోర్డు', 'orders': 'ఆర్డర్లు', 'products': 'ఉత్పత్తులు', 'customers': 'వినియోగదారులు', 'settings': 'సెట్టింగ్‌లు', 'analytics': 'విశ్లేషణ'},
    'bn': {'dashboard': 'ড্যাশবোর্ড', 'orders': 'অর্ডার', 'products': 'পণ্য', 'customers': 'গ্রাহক', 'settings': 'সেটিংস', 'analytics': 'বিশ্লেষণ'},
    'gu': {'dashboard': 'ડેશબોર્ડ', 'orders': 'ઓર્ડર', 'products': 'પ્રોડક્ટ્સ', 'customers': 'ગ્રાહકો', 'settings': 'સેટિંગ્સ', 'analytics': 'એનાલિટિક્સ'},
    'mr': {'dashboard': 'डॅशबोर्ड', 'orders': 'ऑर्डर्स', 'products': 'प्रोडक्ट्स', 'customers': 'ग्राहक', 'settings': 'सेटिंग्स', 'analytics': 'अॅनालिटिक्स'},
}


class KeyIn(BaseModel):
    lang: str
    key: str
    value: str


class AutoIn(BaseModel):
    lang: str
    keys: list[str]


@router.get('/languages')
async def languages(_=Depends(get_current_admin)):
    return {'languages': LANGUAGES}


@router.get('/keys')
async def get_keys(lang: str = 'hi', _=Depends(get_current_admin)):
    if lang == 'en':
        return {'lang': lang, 'keys': {}}
    stored = {}
    cur = db.translations.find({'lang': lang}, {'_id': 0})
    async for t in cur:
        stored[t['key']] = t['value']
    merged = {**DEFAULTS.get(lang, {}), **stored}
    return {'lang': lang, 'keys': merged}


@router.put('/keys')
async def set_key(body: KeyIn, _=Depends(get_current_admin)):
    if body.lang not in [l['code'] for l in LANGUAGES]:
        raise HTTPException(400, f"Unknown language '{body.lang}'")
    await db.translations.update_one(
        {'lang': body.lang, 'key': body.key},
        {'$set': {'lang': body.lang, 'key': body.key, 'value': body.value}},
        upsert=True,
    )
    return {'ok': True}


@router.post('/auto')
async def auto_translate(body: AutoIn, _=Depends(get_current_admin)):
    if body.lang not in [l['code'] for l in LANGUAGES]:
        raise HTTPException(400, f"Unknown language '{body.lang}'")
    out = {}
    for key in body.keys:
        text = key.replace('_', ' ').capitalize()
        try:
            res = chat_completion(
                "You are a professional translator. Translate the given English UI string into the target language. Return only the translation.",
                f"Target language: {body.lang}\nString: {text}",
                session_id='i18n', temperature=0.2,
            )
            out[key] = res.strip() if res and res.strip() else text
        except Exception:
            out[key] = text
        # persist
        try:
            await db.translations.update_one(
                {'lang': body.lang, 'key': key},
                {'$set': {'lang': body.lang, 'key': key, 'value': out[key]}},
                upsert=True,
            )
        except Exception:
            pass
    return {'ok': True, 'lang': body.lang, 'keys': out}
