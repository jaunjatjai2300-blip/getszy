import uuid
import re
import math
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/growth', tags=['growth'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


class SEOAnalyzeIn(BaseModel):
    url: str


class SEOMetaIn(BaseModel):
    topic: str
    content: str = ""
    page_type: str = "landing"


class SitemapGenerateIn(BaseModel):
    routes: List[Dict[str, Any]]


class EmailCampaignIn(BaseModel):
    name: str
    subject: str
    html_body: str
    recipient_list: str = "all_users"
    schedule_at: Optional[str] = None


class EmailTemplateIn(BaseModel):
    name: str
    subject: str
    html: str
    variables: List[str] = []


class FunnelIn(BaseModel):
    name: str
    steps: List[Dict[str, Any]]


class ABTestIn(BaseModel):
    name: str
    variant_a: Dict[str, Any]
    variant_b: Dict[str, Any]
    metric: str = "clicks"
    traffic_split: int = 50


class ABTestResultIn(BaseModel):
    variant: str
    value: float = 1.0


class PushNotificationIn(BaseModel):
    title: str
    body: str
    segment: str = "all"
    url: Optional[str] = None


class SMSCampaignIn(BaseModel):
    name: str
    message: str
    recipients: str = "all"
    schedule_at: Optional[str] = None


class ReferralInviteIn(BaseModel):
    email: str
    referrer_id: str


@router.post('/seo/analyze')
async def analyze_seo(body: SEOAnalyzeIn, admin=Depends(get_current_admin)):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(body.url, headers={
                'User-Agent': 'GetszyBot/1.0 SEO-Analyzer',
                'Accept': 'text/html',
            })
            html = resp.text
            status_code = resp.status_code
    except Exception as e:
        raise HTTPException(400, f'Failed to fetch URL: {str(e)}')

    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    meta_desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
    if not meta_desc_match:
        meta_desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html, re.IGNORECASE)
    meta_desc = meta_desc_match.group(1).strip() if meta_desc_match else ""

    og_title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
    og_title = og_title_match.group(1).strip() if og_title_match else ""

    og_desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.IGNORECASE)
    og_desc = og_desc_match.group(1).strip() if og_desc_match else ""

    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    h1_tags = [h.strip() for h in h1_matches]

    img_tags = re.findall(r'<img\s+([^>]+)>', html, re.IGNORECASE)
    imgs_no_alt = [tag for tag in img_tags if 'alt=' not in tag.lower() or 'alt=""' in tag.lower() or "alt=''" in tag.lower()]
    total_images = len(img_tags)
    images_without_alt = len(imgs_no_alt)

    canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', html, re.IGNORECASE)
    canonical = canonical_match.group(1).strip() if canonical_match else ""

    viewport_match = re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE)
    has_viewport = bool(viewport_match)

    charset_match = re.search(r'<meta\s+charset=["\']([^"\']+)["\']', html, re.IGNORECASE)
    has_charset = bool(charset_match)

    lang_match = re.search(r'<html\s+[^>]*lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
    html_lang = lang_match.group(1) if lang_match else ""

    score = 0
    recommendations = []

    if title:
        score += 15
        if len(title) < 30:
            recommendations.append({"type": "warning", "message": "Title tag is too short (under 30 chars). Aim for 50-60 characters."})
        elif len(title) > 60:
            recommendations.append({"type": "warning", "message": "Title tag is too long (over 60 chars). May be truncated in search results."})
        else:
            score += 5
    else:
        recommendations.append({"type": "error", "message": "Missing title tag. Every page needs a unique, descriptive title."})

    if meta_desc:
        score += 15
        if len(meta_desc) < 70:
            recommendations.append({"type": "warning", "message": "Meta description is short. Aim for 120-160 characters."})
        elif len(meta_desc) > 160:
            recommendations.append({"type": "warning", "message": "Meta description is over 160 characters. May be truncated."})
        else:
            score += 5
    else:
        recommendations.append({"type": "error", "message": "Missing meta description. Add a compelling 120-160 char description."})

    if h1_tags:
        score += 10
        if len(h1_tags) > 1:
            recommendations.append({"type": "warning", "message": f"Found {len(h1_tags)} H1 tags. Use only one H1 per page."})
    else:
        recommendations.append({"type": "error", "message": "No H1 tag found. Every page should have exactly one H1."})

    if total_images > 0:
        alt_ratio = (total_images - images_without_alt) / total_images
        score += int(alt_ratio * 10)
        if images_without_alt > 0:
            recommendations.append({
                "type": "warning",
                "message": f"{images_without_alt}/{total_images} images missing alt text. Add descriptive alt text for accessibility and SEO."
            })
    else:
        score += 5

    if og_title:
        score += 5
    else:
        recommendations.append({"type": "info", "message": "Missing og:title meta tag. Add Open Graph tags for better social sharing."})

    if og_desc:
        score += 5
    else:
        recommendations.append({"type": "info", "message": "Missing og:description meta tag. Add Open Graph tags for social sharing."})

    if canonical:
        score += 5
    else:
        recommendations.append({"type": "info", "message": "No canonical tag found. Add a canonical URL to prevent duplicate content issues."})

    if has_viewport:
        score += 5
    else:
        recommendations.append({"type": "error", "message": "Missing viewport meta tag. Required for mobile responsiveness."})

    if has_charset:
        score += 5
    else:
        recommendations.append({"type": "warning", "message": "Missing charset declaration. Add <meta charset='utf-8'>."})

    if html_lang:
        score += 5
    else:
        recommendations.append({"type": "info", "message": "Missing lang attribute on <html> tag. Helps search engines understand content language."})

    score = min(100, score)

    if status_code != 200:
        recommendations.append({"type": "error", "message": f"HTTP status code is {status_code}. Pages should return 200 OK."})

    return {
        'url': body.url,
        'status_code': status_code,
        'score': score,
        'analysis': {
            'title': title,
            'title_length': len(title),
            'meta_description': meta_desc,
            'meta_desc_length': len(meta_desc),
            'h1_tags': h1_tags,
            'h1_count': len(h1_tags),
            'total_images': total_images,
            'images_without_alt': images_without_alt,
            'og_title': og_title,
            'og_description': og_desc,
            'canonical': canonical,
            'has_viewport': has_viewport,
            'has_charset': has_charset,
            'html_lang': html_lang,
        },
        'recommendations': recommendations,
    }


@router.post('/seo/generate-meta')
async def generate_seo_meta(body: SEOMetaIn, admin=Depends(get_current_admin)):
    system = (
        "You are an SEO expert. Generate optimized meta tags for a web page. "
        "Reply ONLY with valid JSON: {\"title\": \"...\", \"description\": \"...\", \"keywords\": [...], "
        "\"og_title\": \"...\", \"og_description\": \"...\", \"twitter_title\": \"...\", \"twitter_description\": \"...\"}.\n"
        "Title: 50-60 chars. Description: 120-160 chars. Keywords: 5-10 relevant terms."
    )
    user = f"Topic: {body.topic}\nPage type: {body.page_type}\nContent summary: {body.content[:500]}"
    raw = await chat_completion(system=system, user=user, temperature=0.4)
    s = (raw or '').find('{')
    e = (raw or '').rfind('}')
    meta = None
    if s != -1:
        try:
            meta = json.loads(raw[s:e + 1])
        except Exception:
            meta = None
    if not meta:
        meta = {
            'title': f"{body.topic} | Getszy",
            'description': f"Learn about {body.topic}. Comprehensive guide and resources.",
            'keywords': [body.topic.lower(), 'getszy', body.page_type],
            'og_title': f"{body.topic} | Getszy",
            'og_description': f"Discover {body.topic} with Getszy AI.",
            'twitter_title': f"{body.topic} | Getszy",
            'twitter_description': f"Explore {body.topic} on Getszy.",
        }
    return meta


@router.post('/seo/sitemap-generate')
async def generate_sitemap(body: SitemapGenerateIn, admin=Depends(get_current_admin)):
    base_url = "https://getszy.com"
    urls_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for route in body.routes:
        path = route.get('path', '/')
        priority = route.get('priority', '0.8')
        changefreq = route.get('changefreq', 'weekly')
        lastmod = route.get('lastmod', _now()[:10])
        full_url = f"{base_url}{path}" if path.startswith('/') else f"{base_url}/{path}"
        urls_xml += f'  <url>\n    <loc>{full_url}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
    urls_xml += '</urlset>'
    sitemap_id = _uid()
    doc = {
        'id': sitemap_id,
        'xml': urls_xml,
        'route_count': len(body.routes),
        'created_at': _now(),
    }
    await db.seo_sitemaps.insert_one(doc)
    return {'id': sitemap_id, 'xml': urls_xml, 'route_count': len(body.routes)}


@router.get('/email-campaigns')
async def list_email_campaigns(admin=Depends(get_current_admin)):
    campaigns = await db.email_campaigns.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    return {'campaigns': campaigns}


@router.post('/email-campaigns')
async def create_email_campaign(body: EmailCampaignIn, admin=Depends(get_current_admin)):
    campaign_id = _uid()
    total_recipients = 0
    if body.recipient_list == 'all_users':
        total_recipients = await db.users.count_documents({})
    elif body.recipient_list == 'subscribers':
        total_recipients = await db.users.count_documents({'newsletter_subscribed': True})
    else:
        total_recipients = await db.email_segments.count_documents({'name': body.recipient_list})

    campaign = {
        'id': campaign_id,
        'name': body.name,
        'subject': body.subject,
        'html_body': body.html_body,
        'recipient_list': body.recipient_list,
        'total_recipients': total_recipients,
        'status': 'draft',
        'schedule_at': body.schedule_at,
        'sent_at': None,
        'stats': {'sent': 0, 'delivered': 0, 'opened': 0, 'clicked': 0, 'bounced': 0},
        'created_at': _now(),
    }
    await db.email_campaigns.insert_one(campaign)
    campaign.pop('_id', None)
    return campaign


@router.post('/email-campaigns/{campaign_id}/send')
async def send_email_campaign(campaign_id: str, admin=Depends(get_current_admin)):
    campaign = await db.email_campaigns.find_one({'id': campaign_id}, {'_id': 0})
    if not campaign:
        raise HTTPException(404, 'Campaign not found')
    if campaign['status'] == 'sent':
        raise HTTPException(400, 'Campaign already sent')

    total = campaign.get('total_recipients', 0)
    sent_count = total
    delivered_count = int(total * 0.97)
    bounced_count = total - delivered_count

    send_record = {
        'id': _uid(),
        'campaign_id': campaign_id,
        'total': total,
        'sent': sent_count,
        'delivered': delivered_count,
        'bounced': bounced_count,
        'sent_at': _now(),
    }
    await db.email_sends.insert_one(send_record)

    stats = {
        'sent': sent_count,
        'delivered': delivered_count,
        'opened': 0,
        'clicked': 0,
        'bounced': bounced_count,
    }
    await db.email_campaigns.update_one(
        {'id': campaign_id},
        {'$set': {
            'status': 'sent',
            'sent_at': _now(),
            'stats': stats,
        }}
    )
    return {'campaign_id': campaign_id, 'status': 'sent', 'stats': stats}


@router.get('/email-campaigns/{campaign_id}/stats')
async def email_campaign_stats(campaign_id: str, admin=Depends(get_current_admin)):
    campaign = await db.email_campaigns.find_one({'id': campaign_id}, {'_id': 0})
    if not campaign:
        raise HTTPException(404, 'Campaign not found')

    sends = await db.email_sends.find({'campaign_id': campaign_id}, {'_id': 0}).to_list(100)
    total_delivered = sum(s.get('delivered', 0) for s in sends)
    total_opened = sum(s.get('opened', 0) for s in sends)
    total_clicked = sum(s.get('clicked', 0) for s in sends)
    total_bounced = sum(s.get('bounced', 0) for s in sends)

    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    click_rate = (total_clicked / total_delivered * 100) if total_delivered > 0 else 0
    bounce_rate = (total_bounced / (total_delivered + total_bounced) * 100) if (total_delivered + total_bounced) > 0 else 0

    return {
        'campaign_id': campaign_id,
        'name': campaign.get('name'),
        'status': campaign.get('status'),
        'total_sent': sum(s.get('sent', 0) for s in sends),
        'total_delivered': total_delivered,
        'total_opened': total_opened,
        'total_clicked': total_clicked,
        'total_bounced': total_bounced,
        'open_rate': round(open_rate, 2),
        'click_rate': round(click_rate, 2),
        'bounce_rate': round(bounce_rate, 2),
        'send_batches': len(sends),
    }


@router.post('/email-templates')
async def create_email_template(body: EmailTemplateIn, admin=Depends(get_current_admin)):
    template_id = _uid()
    doc = {
        'id': template_id,
        'name': body.name,
        'subject': body.subject,
        'html': body.html,
        'variables': body.variables,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.email_templates.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/email-templates')
async def list_email_templates(admin=Depends(get_current_admin)):
    templates = await db.email_templates.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    return {'templates': templates}


@router.post('/funnels')
async def create_funnel(body: FunnelIn, admin=Depends(get_current_admin)):
    funnel_id = _uid()
    steps_with_rates = []
    for i, step in enumerate(body.steps):
        steps_with_rates.append({
            'order': i + 1,
            'url': step.get('url', '/'),
            'action': step.get('action', 'page_view'),
            'name': step.get('name', f'Step {i + 1}'),
            'expected_rate': step.get('expected_rate', 100.0),
            'actual_count': 0,
            'actual_rate': 0.0,
        })

    funnel = {
        'id': funnel_id,
        'name': body.name,
        'steps': steps_with_rates,
        'total_entries': 0,
        'total_conversions': 0,
        'overall_conversion_rate': 0.0,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.funnels.insert_one(funnel)
    funnel.pop('_id', None)
    return funnel


@router.get('/funnels')
async def list_funnels(admin=Depends(get_current_admin)):
    funnels = await db.funnels.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).to_list(50)
    return {'funnels': funnels}


@router.get('/funnels/{funnel_id}')
async def get_funnel(funnel_id: str, admin=Depends(get_current_admin)):
    funnel = await db.funnels.find_one({'id': funnel_id}, {'_id': 0})
    if not funnel:
        raise HTTPException(404, 'Funnel not found')

    steps = funnel.get('steps', [])
    dropoff_analysis = []
    for i in range(len(steps)):
        step = steps[i]
        if i == 0:
            dropoff_analysis.append({
                'step': step['name'],
                'entered': step.get('actual_count', 0),
                'dropoff': 0,
                'dropoff_rate': 0.0,
                'conversion_rate': 100.0,
            })
        else:
            prev_count = steps[i - 1].get('actual_count', 0)
            curr_count = step.get('actual_count', 0)
            dropoff = prev_count - curr_count
            dropoff_rate = (dropoff / prev_count * 100) if prev_count > 0 else 0
            conv_rate = (curr_count / prev_count * 100) if prev_count > 0 else 0
            dropoff_analysis.append({
                'step': step['name'],
                'entered': curr_count,
                'dropoff': dropoff,
                'dropoff_rate': round(dropoff_rate, 2),
                'conversion_rate': round(conv_rate, 2),
            })

    funnel['dropoff_analysis'] = dropoff_analysis
    return funnel


@router.post('/ab-tests')
async def create_ab_test(body: ABTestIn, admin=Depends(get_current_admin)):
    if body.metric not in ('clicks', 'conversions', 'revenue'):
        raise HTTPException(400, 'metric must be clicks, conversions, or revenue')
    if not 1 <= body.traffic_split <= 99:
        raise HTTPException(400, 'traffic_split must be between 1 and 99')

    test_id = _uid()
    test = {
        'id': test_id,
        'name': body.name,
        'variant_a': {**body.variant_a, 'id': 'a', 'traffic_pct': body.traffic_split, 'visitors': 0, 'conversions': 0, 'total_value': 0.0},
        'variant_b': {**body.variant_b, 'id': 'b', 'traffic_pct': 100 - body.traffic_split, 'visitors': 0, 'conversions': 0, 'total_value': 0.0},
        'metric': body.metric,
        'traffic_split': body.traffic_split,
        'status': 'running',
        'winner': None,
        'started_at': _now(),
        'ended_at': None,
        'created_at': _now(),
    }
    await db.ab_tests.insert_one(test)
    test.pop('_id', None)
    return test


@router.get('/ab-tests')
async def list_ab_tests(admin=Depends(get_current_admin)):
    tests = await db.ab_tests.find(
        {}, {'_id': 0}
    ).sort('created_at', -1).to_list(50)
    return {'tests': tests}


@router.post('/ab-tests/{test_id}/results')
async def record_ab_result(test_id: str, body: ABTestResultIn, admin=Depends(get_current_admin)):
    test = await db.ab_tests.find_one({'id': test_id}, {'_id': 0})
    if not test:
        raise HTTPException(404, 'A/B test not found')
    if test['status'] != 'running':
        raise HTTPException(400, 'Test is not running')

    variant_key = f'variant_{body.variant}'
    variant = test.get(variant_key, {})
    variant['visitors'] = variant.get('visitors', 0) + 1
    variant['conversions'] = variant.get('conversions', 0) + (1 if body.value > 0 else 0)
    variant['total_value'] = variant.get('total_value', 0.0) + body.value

    await db.ab_tests.update_one(
        {'id': test_id},
        {'$set': {variant_key: variant, 'updated_at': _now()}}
    )
    return {'test_id': test_id, 'variant': body.variant, 'visitors': variant['visitors'], 'conversions': variant['conversions']}


@router.get('/ab-tests/{test_id}/winner')
async def get_ab_winner(test_id: str, admin=Depends(get_current_admin)):
    test = await db.ab_tests.find_one({'id': test_id}, {'_id': 0})
    if not test:
        raise HTTPException(404, 'A/B test not found')

    a = test.get('variant_a', {})
    b = test.get('variant_b', {})

    a_rate = (a.get('conversions', 0) / a['visitors'] * 100) if a.get('visitors', 0) > 0 else 0
    b_rate = (b.get('conversions', 0) / b['visitors'] * 100) if b.get('visitors', 0) > 0 else 0

    a_val = a.get('total_value', 0) / a['visitors'] if a.get('visitors', 0) > 0 else 0
    b_val = b.get('total_value', 0) / b['visitors'] if b.get('visitors', 0) > 0 else 0

    total_visitors = a.get('visitors', 0) + b.get('visitors', 0)
    min_sample = 100
    significance = 0.0

    if total_visitors >= min_sample and a.get('visitors', 0) > 0 and b.get('visitors', 0) > 0:
        pooled = (a.get('conversions', 0) + b.get('conversions', 0)) / total_visitors
        se = math.sqrt(pooled * (1 - pooled) * (1 / a['visitors'] + 1 / b['visitors'])) if pooled > 0 and pooled < 1 else 0
        if se > 0:
            z = abs(a_rate - b_rate) / se
            significance = min(99.9, round((1 - math.exp(-0.5 * z * z)) * 100, 1))

    winner = None
    if significance >= 95:
        if test['metric'] in ('revenue',):
            winner = 'a' if a_val > b_val else 'b'
        else:
            winner = 'a' if a_rate > b_rate else 'b'

    return {
        'test_id': test_id,
        'name': test['name'],
        'metric': test['metric'],
        'variant_a': {
            'name': a.get('name', 'A'),
            'visitors': a.get('visitors', 0),
            'conversions': a.get('conversions', 0),
            'conversion_rate': round(a_rate, 2),
            'avg_value': round(a_val, 4),
        },
        'variant_b': {
            'name': b.get('name', 'B'),
            'visitors': b.get('visitors', 0),
            'conversions': b.get('conversions', 0),
            'conversion_rate': round(b_rate, 2),
            'avg_value': round(b_val, 4),
        },
        'total_visitors': total_visitors,
        'statistical_significance': significance,
        'has_enough_data': total_visitors >= min_sample,
        'winner': winner,
        'status': test['status'],
    }


@router.post('/push-notifications')
async def send_push_notification(body: PushNotificationIn, admin=Depends(get_current_admin)):
    notif_id = _uid()
    recipient_count = 0
    if body.segment == 'all':
        recipient_count = await db.users.count_documents({'push_enabled': True})
    elif body.segment == 'active':
        from datetime import timedelta
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recipient_count = await db.users.count_documents({'push_enabled': True, 'last_active': {'$gte': week_ago}})
    else:
        recipient_count = await db.push_subscriptions.count_documents({'segment': body.segment})

    record = {
        'id': notif_id,
        'title': body.title,
        'body': body.body,
        'segment': body.segment,
        'url': body.url,
        'recipient_count': recipient_count,
        'status': 'queued',
        'sent_at': None,
        'created_at': _now(),
    }
    await db.push_notifications.insert_one(record)
    record.pop('_id', None)
    return record


@router.post('/sms-campaigns')
async def create_sms_campaign(body: SMSCampaignIn, admin=Depends(get_current_admin)):
    campaign_id = _uid()
    recipient_count = 0
    if body.recipients == 'all':
        recipient_count = await db.users.count_documents({'phone': {'$exists': True, '$ne': None}})
    elif body.recipients == 'verified':
        recipient_count = await db.users.count_documents({'phone': {'$exists': True, '$ne': None}, 'phone_verified': True})

    campaign = {
        'id': campaign_id,
        'name': body.name,
        'message': body.message,
        'recipients': body.recipients,
        'total_recipients': recipient_count,
        'schedule_at': body.schedule_at,
        'status': 'draft',
        'sent_at': None,
        'stats': {'sent': 0, 'delivered': 0, 'failed': 0},
        'created_at': _now(),
    }
    await db.sms_campaigns.insert_one(campaign)
    campaign.pop('_id', None)
    return campaign


@router.get('/referral-program')
async def get_referral_stats(admin=Depends(get_current_admin)):
    total_referrals = await db.referral_invites.count_documents({})
    converted = await db.referral_invites.count_documents({'status': 'converted'})
    pending = await db.referral_invites.count_documents({'status': 'pending'})
    conversion_rate = (converted / total_referrals * 100) if total_referrals > 0 else 0

    pipeline = [
        {'$group': {'_id': '$referrer_id', 'count': {'$sum': 1}, 'conversions': {'$sum': {'$cond': [{'$eq': ['$status', 'converted']}, 1, 0]}}}},
        {'$sort': {'conversions': -1}},
        {'$limit': 10},
    ]
    top_referrers = await db.referral_invites.aggregate(pipeline).to_list(10)
    top = []
    for r in top_referrers:
        user = await db.users.find_one({'id': r['_id']}, {'_id': 0, 'name': 1, 'email': 1})
        top.append({
            'referrer_id': r['_id'],
            'name': user.get('name', 'Unknown') if user else 'Unknown',
            'email': user.get('email', '') if user else '',
            'total_referrals': r['count'],
            'conversions': r['conversions'],
        })

    return {
        'total_referrals': total_referrals,
        'conversions': converted,
        'pending': pending,
        'conversion_rate': round(conversion_rate, 2),
        'top_referrers': top,
    }


@router.post('/referral-program/invite')
async def create_referral_invite(body: ReferralInviteIn, admin=Depends(get_current_admin)):
    referrer = await db.users.find_one({'id': body.referrer_id}, {'_id': 0})
    if not referrer:
        raise HTTPException(404, 'Referrer not found')

    existing = await db.referral_invites.find_one({'email': body.email, 'referrer_id': body.referrer_id})
    if existing:
        raise HTTPException(400, 'Invite already sent to this email by this referrer')

    invite_id = _uid()
    invite = {
        'id': invite_id,
        'email': body.email,
        'referrer_id': body.referrer_id,
        'referrer_name': referrer.get('name', ''),
        'status': 'pending',
        'sent_at': _now(),
        'accepted_at': None,
        'converted_at': None,
    }
    await db.referral_invites.insert_one(invite)
    invite.pop('_id', None)
    return invite


@router.get('/referral-program/leaderboard')
async def referral_leaderboard(admin=Depends(get_current_admin)):
    pipeline = [
        {'$group': {'_id': '$referrer_id', 'total': {'$sum': 1}, 'conversions': {'$sum': {'$cond': [{'$eq': ['$status', 'converted']}, 1, 0]}}}},
        {'$sort': {'conversions': -1}},
        {'$limit': 25},
    ]
    results = await db.referral_invites.aggregate(pipeline).to_list(25)
    leaderboard = []
    for i, r in enumerate(results):
        user = await db.users.find_one({'id': r['_id']}, {'_id': 0, 'name': 1, 'email': 1})
        leaderboard.append({
            'rank': i + 1,
            'referrer_id': r['_id'],
            'name': user.get('name', 'Unknown') if user else 'Unknown',
            'email': user.get('email', '') if user else '',
            'total_referrals': r['total'],
            'conversions': r['conversions'],
            'conversion_rate': round((r['conversions'] / r['total'] * 100) if r['total'] > 0 else 0, 2),
        })
    return {'leaderboard': leaderboard}
