import uuid
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/analytics-advanced', tags=['analytics-advanced'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


class FunnelIn(BaseModel):
    name: str
    steps: List[dict]


class FunnelEventIn(BaseModel):
    step_name: str
    user_id: Optional[str] = None
    timestamp: Optional[str] = None


class ExportIn(BaseModel):
    metrics: List[str]
    date_range: Optional[dict] = None
    format: str = 'csv'


@router.get('/funnels')
async def list_funnels(_=Depends(get_current_admin)):
    funnels = await db.analytics_funnels.find({}, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return {'funnels': funnels}


@router.post('/funnels')
async def create_funnel(body: FunnelIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        'name': body.name,
        'steps': body.steps,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.analytics_funnels.insert_one(doc)
    return doc


@router.get('/funnels/{funnel_id}')
async def get_funnel(funnel_id: str, _=Depends(get_current_admin)):
    funnel = await db.analytics_funnels.find_one({'id': funnel_id}, {'_id': 0})
    if not funnel:
        raise HTTPException(404, 'Funnel not found')

    steps = funnel.get('steps', [])
    events = await db.analytics_funnel_events.find({'funnel_id': funnel_id}, {'_id': 0}).to_list(100000)

    step_names = [s.get('name', '') for s in steps]
    step_counts = {}
    for sn in step_names:
        step_counts[sn] = 0
    for ev in events:
        sn = ev.get('step_name', '')
        if sn in step_counts:
            step_counts[sn] += 1

    step_analysis = []
    for i, step in enumerate(steps):
        name = step.get('name', '')
        count = step_counts.get(name, 0)
        prev_count = step_counts.get(step_names[i - 1], count) if i > 0 else count
        conversion_from_prev = (count / prev_count * 100) if prev_count > 0 else 100.0
        dropoff = prev_count - count if i > 0 else 0
        first_count = step_counts.get(step_names[0], 0) if step_names else 0
        overall_rate = (count / first_count * 100) if first_count > 0 else 100.0

        step_analysis.append({
            'step': name,
            'order': i,
            'count': count,
            'conversion_from_previous_step': round(conversion_from_prev, 2),
            'dropoff': dropoff,
            'overall_conversion_rate': round(overall_rate, 2),
        })

    total_entered = step_counts.get(step_names[0], 0) if step_names else 0
    total_completed = step_counts.get(step_names[-1], 0) if step_names else 0
    overall_conversion = (total_completed / total_entered * 100) if total_entered > 0 else 0.0

    return {
        'funnel': funnel,
        'step_analysis': step_analysis,
        'total_events': len(events),
        'overall_conversion_rate': round(overall_conversion, 2),
    }


@router.post('/funnels/{funnel_id}/events')
async def record_funnel_event(funnel_id: str, body: FunnelEventIn, _=Depends(get_current_admin)):
    funnel = await db.analytics_funnels.find_one({'id': funnel_id}, {'_id': 0})
    if not funnel:
        raise HTTPException(404, 'Funnel not found')

    doc = {
        'id': _uid(),
        'funnel_id': funnel_id,
        'step_name': body.step_name,
        'user_id': body.user_id,
        'timestamp': body.timestamp or _now(),
        'created_at': _now(),
    }
    await db.analytics_funnel_events.insert_one(doc)
    return doc


@router.get('/retention')
async def cohort_retention(_=Depends(get_current_admin)):
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)

    activity_map = {}
    for act in activities:
        uid = act.get('user_id', '')
        ts = act.get('timestamp', '')
        if uid not in activity_map:
            activity_map[uid] = []
        activity_map[uid].append(ts)

    cohorts = {}
    for user in users:
        uid = user.get('id', '')
        created = user.get('created_at', '')
        if not created:
            continue
        try:
            signup_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        except Exception:
            continue
        cohort_week = signup_dt.strftime('%Y-W%W')
        if cohort_week not in cohorts:
            cohorts[cohort_week] = []
        cohorts[cohort_week].append({'user_id': uid, 'signup_dt': signup_dt})

    retention_matrix = {}
    now = datetime.now(timezone.utc)

    for cohort_week, cohort_users in sorted(cohorts.items()):
        cohort_size = len(cohort_users)
        retention_matrix[cohort_week] = {
            'cohort_size': cohort_size,
            'weeks': {},
        }

        for week_offset in range(13):
            week_start = min(u['signup_dt'] for u in cohort_users) + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(weeks=1)
            if week_start > now:
                break

            active_count = 0
            for u in cohort_users:
                uid = u['user_id']
                user_acts = activity_map.get(uid, [])
                for ts in user_acts:
                    try:
                        act_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        if week_start <= act_dt < week_end:
                            active_count += 1
                            break
                    except Exception:
                        continue

            retention_pct = (active_count / cohort_size * 100) if cohort_size > 0 else 0.0
            retention_matrix[cohort_week]['weeks'][f'week_{week_offset}'] = {
                'active_users': active_count,
                'retention_pct': round(retention_pct, 2),
            }

    return {'cohorts': retention_matrix, 'total_users': len(users)}


@router.get('/retention/daily')
async def daily_retention(_=Depends(get_current_admin)):
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)

    activity_map = {}
    for act in activities:
        uid = act.get('user_id', '')
        ts = act.get('timestamp', '')
        if uid not in activity_map:
            activity_map[uid] = []
        activity_map[uid].append(ts)

    results = {'d1': 0, 'd7': 0, 'd14': 0, 'd30': 0}
    total_with_activity = 0

    for user in users:
        uid = user.get('id', '')
        created = user.get('created_at', '')
        if not created:
            continue
        try:
            signup_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        except Exception:
            continue

        user_acts = activity_map.get(uid, [])
        if not user_acts:
            continue

        total_with_activity += 1
        for ts in user_acts:
            try:
                act_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                days_diff = (act_dt - signup_dt).total_seconds() / 86400
                if 1 <= days_diff < 2:
                    results['d1'] += 1
                if 7 <= days_diff < 8:
                    results['d7'] += 1
                if 14 <= days_diff < 15:
                    results['d14'] += 1
                if 30 <= days_diff < 31:
                    results['d30'] += 1
            except Exception:
                continue

    total_users = len(users)
    return {
        'd1': {'count': results['d1'], 'rate': round(results['d1'] / total_users * 100, 2) if total_users > 0 else 0},
        'd7': {'count': results['d7'], 'rate': round(results['d7'] / total_users * 100, 2) if total_users > 0 else 0},
        'd14': {'count': results['d14'], 'rate': round(results['d14'] / total_users * 100, 2) if total_users > 0 else 0},
        'd30': {'count': results['d30'], 'rate': round(results['d30'] / total_users * 100, 2) if total_users > 0 else 0},
        'total_users': total_users,
    }


@router.get('/cohorts')
async def user_cohorts(
    cohort_by: str = 'signup_date',
    _=Depends(get_current_admin),
):
    users = await db.users.find({}, {'_id': 0}).to_list(100000)
    orders = await db.orders.find({}, {'_id': 0, 'user_id': 1, 'total': 1, 'created_at': 1}).to_list(100000)

    user_orders = {}
    for order in orders:
        uid = order.get('user_id', '')
        if uid not in user_orders:
            user_orders[uid] = {'total_spent': 0, 'order_count': 0, 'first_order': order.get('created_at', '')}
        user_orders[uid]['total_spent'] += order.get('total', 0)
        user_orders[uid]['order_count'] += 1

    cohort_groups = {}
    for user in users:
        uid = user.get('id', '')
        if cohort_by == 'signup_date':
            key = user.get('created_at', '')[:7] if user.get('created_at') else 'unknown'
        elif cohort_by == 'first_purchase':
            uo = user_orders.get(uid, {})
            key = uo.get('first_order', '')[:7] if uo.get('first_order') else 'no_purchase'
        elif cohort_by == 'subscription_plan':
            key = user.get('subscription_plan', user.get('plan', 'free'))
        elif cohort_by == 'acquisition_channel':
            key = user.get('acquisition_channel', user.get('source', 'unknown'))
        else:
            key = user.get('created_at', '')[:7] if user.get('created_at') else 'unknown'

        if key not in cohort_groups:
            cohort_groups[key] = []
        cohort_groups[key].append(uid)

    result = {}
    for key, uids in cohort_groups.items():
        total_spent = sum(user_orders.get(uid, {}).get('total_spent', 0) for uid in uids)
        total_orders = sum(user_orders.get(uid, {}).get('order_count', 0) for uid in uids)
        avg_spent = total_spent / len(uids) if uids else 0

        result[key] = {
            'cohort_size': len(uids),
            'total_revenue': round(total_spent, 2),
            'total_orders': total_orders,
            'avg_revenue_per_user': round(avg_spent, 2),
            'avg_orders_per_user': round(total_orders / len(uids), 2) if uids else 0,
        }

    return {'cohorts': result, 'cohort_by': cohort_by, 'total_users': len(users)}


@router.get('/churn')
async def churn_analysis(_=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    users = await db.users.find({}, {'_id': 0}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)

    last_active = {}
    for act in activities:
        uid = act.get('user_id', '')
        ts = act.get('timestamp', '')
        if uid not in last_active or ts > last_active[uid]:
            last_active[uid] = ts

    churn_7d = {'count': 0, 'users': []}
    churn_14d = {'count': 0, 'users': []}
    churn_30d = {'count': 0, 'users': []}

    by_plan = {}
    by_source = {}

    for user in users:
        uid = user.get('id', '')
        plan = user.get('subscription_plan', user.get('plan', 'free'))
        source = user.get('acquisition_channel', user.get('source', 'unknown'))
        la = last_active.get(uid, '')

        if plan not in by_plan:
            by_plan[plan] = {'total': 0, 'churned_7d': 0, 'churned_14d': 0, 'churned_30d': 0}
        by_plan[plan]['total'] += 1

        if source not in by_source:
            by_source[source] = {'total': 0, 'churned_7d': 0, 'churned_14d': 0, 'churned_30d': 0}
        by_source[source]['total'] += 1

        if not la:
            churn_30d['count'] += 1
            churn_30d['users'].append(uid)
            if plan in by_plan:
                by_plan[plan]['churned_30d'] += 1
            if source in by_source:
                by_source[source]['churned_30d'] += 1
            continue

        try:
            last_dt = datetime.fromisoformat(la.replace('Z', '+00:00'))
            days_inactive = (now - last_dt).total_seconds() / 86400
        except Exception:
            continue

        if days_inactive >= 7:
            churn_7d['count'] += 1
            churn_7d['users'].append(uid)
            if plan in by_plan:
                by_plan[plan]['churned_7d'] += 1
            if source in by_source:
                by_source[source]['churned_7d'] += 1
        if days_inactive >= 14:
            churn_14d['count'] += 1
            churn_14d['users'].append(uid)
            if plan in by_plan:
                by_plan[plan]['churned_14d'] += 1
            if source in by_source:
                by_source[source]['churned_14d'] += 1
        if days_inactive >= 30:
            churn_30d['count'] += 1
            churn_30d['users'].append(uid)
            if plan in by_plan:
                by_plan[plan]['churned_30d'] += 1
            if source in by_source:
                by_source[source]['churned_30d'] += 1

    total = len(users)
    for k in by_plan:
        t = by_plan[k]['total']
        by_plan[k]['churn_rate_7d'] = round(by_plan[k]['churned_7d'] / t * 100, 2) if t > 0 else 0
        by_plan[k]['churn_rate_14d'] = round(by_plan[k]['churned_14d'] / t * 100, 2) if t > 0 else 0
        by_plan[k]['churn_rate_30d'] = round(by_plan[k]['churned_30d'] / t * 100, 2) if t > 0 else 0
    for k in by_source:
        t = by_source[k]['total']
        by_source[k]['churn_rate_7d'] = round(by_source[k]['churned_7d'] / t * 100, 2) if t > 0 else 0
        by_source[k]['churn_rate_14d'] = round(by_source[k]['churned_14d'] / t * 100, 2) if t > 0 else 0
        by_source[k]['churn_rate_30d'] = round(by_source[k]['churned_30d'] / t * 100, 2) if t > 0 else 0

    return {
        'total_users': total,
        'churn_7d': {'count': churn_7d['count'], 'rate': round(churn_7d['count'] / total * 100, 2) if total > 0 else 0},
        'churn_14d': {'count': churn_14d['count'], 'rate': round(churn_14d['count'] / total * 100, 2) if total > 0 else 0},
        'churn_30d': {'count': churn_30d['count'], 'rate': round(churn_30d['count'] / total * 100, 2) if total > 0 else 0},
        'by_plan': by_plan,
        'by_source': by_source,
    }


@router.get('/revenue-analytics')
async def revenue_analytics(_=Depends(get_current_admin)):
    orders = await db.orders.find({}, {'_id': 0}).to_list(100000)
    subscriptions = await db.subscriptions.find({}, {'_id': 0}).to_list(100000)
    coupons = await db.coupons.find({}, {'_id': 0}).to_list(10000)
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)

    now = datetime.now(timezone.utc)

    revenue_by_day = {}
    revenue_by_product = {}
    revenue_by_plan = {}
    revenue_by_coupon = {}
    total_revenue = 0

    for order in orders:
        total = order.get('total', 0)
        created = order.get('created_at', '')
        product = order.get('product_name', order.get('product_id', 'unknown'))
        coupon = order.get('coupon_code', order.get('discount_code', ''))
        plan = order.get('plan', order.get('subscription_plan', ''))
        status = order.get('status', 'completed')

        if status in ('cancelled', 'refunded'):
            total = -abs(total)

        total_revenue += total

        if created:
            day = created[:10]
            revenue_by_day[day] = revenue_by_day.get(day, 0) + total

        if product:
            if product not in revenue_by_product:
                revenue_by_product[product] = {'revenue': 0, 'order_count': 0}
            revenue_by_product[product]['revenue'] += total
            revenue_by_product[product]['order_count'] += 1

        if plan:
            if plan not in revenue_by_plan:
                revenue_by_plan[plan] = {'revenue': 0, 'subscriber_count': 0}
            revenue_by_plan[plan]['revenue'] += total

        if coupon:
            if coupon not in revenue_by_coupon:
                revenue_by_coupon[coupon] = {'revenue': 0, 'usage_count': 0, 'discount_total': 0}
            revenue_by_coupon[coupon]['revenue'] += total
            revenue_by_coupon[coupon]['usage_count'] += 1
            revenue_by_coupon[coupon]['discount_total'] += order.get('discount', 0)

    monthly_revenue = {}
    for day, rev in sorted(revenue_by_day.items()):
        month = day[:7]
        monthly_revenue[month] = monthly_revenue.get(month, 0) + rev

    sorted_months = sorted(monthly_revenue.keys())
    mrr_trend = {m: round(monthly_revenue[m], 2) for m in sorted_months[-12:]}
    latest_mrr = monthly_revenue.get(sorted_months[-1], 0) if sorted_months else 0
    prev_mrr = monthly_revenue.get(sorted_months[-2], 0) if len(sorted_months) >= 2 else 0
    mrr_growth = ((latest_mrr - prev_mrr) / prev_mrr * 100) if prev_mrr > 0 else 0
    arr = latest_mrr * 12

    total_customers = len(users)
    ltv = total_revenue / total_customers if total_customers > 0 else 0
    arpu = total_revenue / total_customers if total_customers > 0 else 0

    paid_customers = len([o for o in orders if o.get('status') not in ('cancelled', 'refunded')])
    avg_customer_value = total_revenue / paid_customers if paid_customers > 0 else 0

    return {
        'total_revenue': round(total_revenue, 2),
        'revenue_by_day': {k: round(v, 2) for k, v in sorted(revenue_by_day.items())[-30:]},
        'revenue_by_product': {k: {**v, 'revenue': round(v['revenue'], 2)} for k, v in revenue_by_product.items()},
        'revenue_by_plan': {k: {**v, 'revenue': round(v['revenue'], 2)} for k, v in revenue_by_plan.items()},
        'revenue_by_coupon': {k: {**v, 'revenue': round(v['revenue'], 2)} for k, v in revenue_by_coupon.items()},
        'mrr_trend': mrr_trend,
        'current_mrr': round(latest_mrr, 2),
        'arr': round(arr, 2),
        'mrr_growth_pct': round(mrr_growth, 2),
        'ltv': round(ltv, 2),
        'arpu': round(arpu, 2),
        'avg_customer_value': round(avg_customer_value, 2),
    }


@router.get('/user-analytics')
async def user_analytics(_=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    users = await db.users.find({}, {'_id': 0}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1, 'duration': 1, 'pages': 1}).to_list(500000)

    signups_by_day = {}
    for user in users:
        created = user.get('created_at', '')[:10]
        if created:
            signups_by_day[created] = signups_by_day.get(created, 0) + 1

    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    daily_active_users = set()
    weekly_active_users = set()
    monthly_active_users = set()

    for act in activities:
        ts = act.get('timestamp', '')
        uid = act.get('user_id', '')
        if not ts or not uid:
            continue
        try:
            act_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if act_dt >= one_day_ago:
                daily_active_users.add(uid)
            if act_dt >= seven_days_ago:
                weekly_active_users.add(uid)
            if act_dt >= thirty_days_ago:
                monthly_active_users.add(uid)
        except Exception:
            continue

    durations = [act.get('duration', 0) for act in activities if act.get('duration', 0) > 0]
    pages_list = [act.get('pages', 0) for act in activities if act.get('pages', 0) > 0]
    bounces = len([act for act in activities if act.get('pages', 0) == 1])
    total_sessions = len(activities) if activities else 1

    return {
        'signups_per_day': dict(sorted(signups_by_day.items())[-30:]),
        'total_signups': len(users),
        'dau': len(daily_active_users),
        'wau': len(weekly_active_users),
        'mau': len(monthly_active_users),
        'avg_session_duration': round(sum(durations) / len(durations), 2) if durations else 0,
        'avg_pages_per_session': round(sum(pages_list) / len(pages_list), 2) if pages_list else 0,
        'bounce_rate': round(bounces / total_sessions * 100, 2),
    }


@router.get('/conversion-funnel')
async def conversion_funnel(_=Depends(get_current_admin)):
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)
    orders = await db.orders.find({}, {'_id': 0, 'user_id': 1, 'status': 1}).to_list(100000)
    subscriptions = await db.subscriptions.find({}, {'_id': 0, 'user_id': 1, 'plan': 1}).to_list(100000)

    page_views = await db.page_views.count_documents({}) if 'page_views' in await db.list_collection_names() else 0
    if page_views == 0:
        page_views = await db.user_activities.count_documents({})

    total_visitors = page_views
    total_signups = len(users)
    trial_users = len([u for u in users if u.get('is_trial', False) or u.get('trial', False)])
    paid_users = len([s for s in subscriptions if s.get('plan', '') not in ('free', 'trial', '')])
    enterprise_users = len([s for s in subscriptions if s.get('plan', '') in ('enterprise', 'business', 'premium')])

    visitor_to_signup = (total_signups / total_visitors * 100) if total_visitors > 0 else 0
    signup_to_trial = (trial_users / total_signups * 100) if total_signups > 0 else 0
    trial_to_paid = (paid_users / trial_users * 100) if trial_users > 0 else 0
    paid_to_enterprise = (enterprise_users / paid_users * 100) if paid_users > 0 else 0

    return {
        'visitors': total_visitors,
        'signups': total_signups,
        'trial': trial_users,
        'paid': paid_users,
        'enterprise': enterprise_users,
        'conversion_rates': {
            'visitor_to_signup': round(visitor_to_signup, 2),
            'signup_to_trial': round(signup_to_trial, 2),
            'trial_to_paid': round(trial_to_paid, 2),
            'paid_to_enterprise': round(paid_to_enterprise, 2),
        },
    }


@router.get('/ab-test-results')
async def ab_test_results(_=Depends(get_current_admin)):
    tests = await db.ab_tests.find({}, {'_id': 0}).to_list(1000)
    results = []

    for test in tests:
        variants = test.get('variants', [])
        variant_results = []
        total_participants = sum(v.get('participants', 0) for v in variants)
        total_conversions = sum(v.get('conversions', 0) for v in variants)

        for variant in variants:
            participants = variant.get('participants', 0)
            conversions = variant.get('conversions', 0)
            conversion_rate = (conversions / participants * 100) if participants > 0 else 0

            if total_participants > 0 and total_conversions > 0:
                expected = (participants / total_participants) * total_conversions
                if expected > 0 and participants > 0:
                    chi_sq = ((conversions - expected) ** 2) / expected
                    significance = 'significant' if chi_sq > 3.841 and participants >= 30 else 'not_significant'
                else:
                    chi_sq = 0
                    significance = 'insufficient_data'
            else:
                chi_sq = 0
                significance = 'insufficient_data'

            variant_results.append({
                'name': variant.get('name', 'unknown'),
                'participants': participants,
                'conversions': conversions,
                'conversion_rate': round(conversion_rate, 2),
                'chi_squared': round(chi_sq, 4),
                'statistical_significance': significance,
            })

        winner = max(variant_results, key=lambda v: v['conversion_rate']) if variant_results else None

        results.append({
            'test_id': test.get('id', ''),
            'name': test.get('name', ''),
            'status': test.get('status', 'running'),
            'variants': variant_results,
            'winner': winner['name'] if winner and winner['statistical_significance'] == 'significant' else None,
            'total_participants': total_participants,
            'created_at': test.get('created_at', ''),
        })

    return {'tests': results, 'total_tests': len(results)}


@router.get('/cohort-revenue')
async def cohort_revenue(_=Depends(get_current_admin)):
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)
    orders = await db.orders.find({}, {'_id': 0, 'user_id': 1, 'total': 1, 'created_at': 1, 'status': 1}).to_list(100000)

    user_signup = {}
    for user in users:
        uid = user.get('id', '')
        created = user.get('created_at', '')
        if uid and created:
            user_signup[uid] = created[:7]

    cohort_revenue = {}
    for order in orders:
        uid = order.get('user_id', '')
        total = order.get('total', 0)
        created = order.get('created_at', '')[:7]
        status = order.get('status', 'completed')

        if status in ('cancelled', 'refunded'):
            total = -abs(total)

        signup_cohort = user_signup.get(uid, 'unknown')

        if signup_cohort not in cohort_revenue:
            cohort_revenue[signup_cohort] = {'total_revenue': 0, 'order_count': 0, 'months': {}}
        cohort_revenue[signup_cohort]['total_revenue'] += total
        cohort_revenue[signup_cohort]['order_count'] += 1

        if created not in cohort_revenue[signup_cohort]['months']:
            cohort_revenue[signup_cohort]['months'][created] = 0
        cohort_revenue[signup_cohort]['months'][created] += total

    result = {}
    for cohort, data in cohort_revenue.items():
        result[cohort] = {
            'total_revenue': round(data['total_revenue'], 2),
            'order_count': data['order_count'],
            'monthly_breakdown': {k: round(v, 2) for k, v in sorted(data['months'].items())},
        }

    return {'cohorts': result, 'total_users': len(users)}


@router.get('/segmentation')
async def user_segmentation(_=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    users = await db.users.find({}, {'_id': 0, 'id': 1}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)

    last_active = {}
    for act in activities:
        uid = act.get('user_id', '')
        ts = act.get('timestamp', '')
        if uid not in last_active or ts > last_active[uid]:
            last_active[uid] = ts

    activity_frequency = {}
    for act in activities:
        uid = act.get('user_id', '')
        ts = act.get('timestamp', '')
        if uid not in activity_frequency:
            activity_frequency[uid] = 0
        activity_frequency[uid] += 1

    segments = {
        'power_users': {'description': 'Active daily', 'count': 0, 'sample_users': []},
        'regular': {'description': 'Active weekly', 'count': 0, 'sample_users': []},
        'casual': {'description': 'Active monthly', 'count': 0, 'sample_users': []},
        'dormant': {'description': 'Inactive 30-90 days', 'count': 0, 'sample_users': []},
        'churned': {'description': 'Inactive 90+ days', 'count': 0, 'sample_users': []},
    }

    for user in users:
        uid = user.get('id', '')
        la = last_active.get(uid, '')

        if not la:
            segments['churned']['count'] += 1
            if len(segments['churned']['sample_users']) < 5:
                segments['churned']['sample_users'].append(uid)
            continue

        try:
            last_dt = datetime.fromisoformat(la.replace('Z', '+00:00'))
            days_inactive = (now - last_dt).total_seconds() / 86400
        except Exception:
            segments['churned']['count'] += 1
            continue

        freq = activity_frequency.get(uid, 0)

        if days_inactive <= 1 and freq >= 7:
            seg = 'power_users'
        elif days_inactive <= 7:
            seg = 'regular'
        elif days_inactive <= 30:
            seg = 'casual'
        elif days_inactive <= 90:
            seg = 'dormant'
        else:
            seg = 'churned'

        segments[seg]['count'] += 1
        if len(segments[seg]['sample_users']) < 5:
            segments[seg]['sample_users'].append(uid)

    total = len(users)
    for seg in segments:
        count = segments[seg]['count']
        segments[seg]['percentage'] = round(count / total * 100, 2) if total > 0 else 0

    return {'segments': segments, 'total_users': total}


@router.get('/predictions')
async def predictive_analytics(_=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    orders = await db.orders.find({}, {'_id': 0, 'total': 1, 'created_at': 1, 'status': 1}).to_list(100000)
    users = await db.users.find({}, {'_id': 0, 'id': 1, 'created_at': 1}).to_list(100000)
    activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)

    monthly_revenue = {}
    for order in orders:
        total = order.get('total', 0)
        created = order.get('created_at', '')
        status = order.get('status', 'completed')
        if status in ('cancelled', 'refunded'):
            total = -abs(total)
        if created:
            month = created[:7]
            monthly_revenue[month] = monthly_revenue.get(month, 0) + total

    sorted_months = sorted(monthly_revenue.keys())
    mrr_values = [monthly_revenue[m] for m in sorted_months[-6:]]

    if len(mrr_values) >= 2:
        growth_rates = [(mrr_values[i] - mrr_values[i - 1]) / mrr_values[i - 1] for i in range(1, len(mrr_values)) if mrr_values[i - 1] > 0]
        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
    else:
        avg_growth = 0

    current_mrr = mrr_values[-1] if mrr_values else 0
    projected_mrr = current_mrr * (1 + avg_growth)

    monthly_signups = {}
    for user in users:
        created = user.get('created_at', '')[:7]
        if created:
            monthly_signups[created] = monthly_signups.get(created, 0) + 1

    signup_values = [monthly_signups.get(m, 0) for m in sorted_months[-6:]]
    if len(signup_values) >= 2:
        signup_growth = [(signup_values[i] - signup_values[i - 1]) / signup_values[i - 1] for i in range(1, len(signup_values)) if signup_values[i - 1] > 0]
        avg_signup_growth = sum(signup_growth) / len(signup_growth) if signup_growth else 0
    else:
        avg_signup_growth = 0

    current_signups = signup_values[-1] if signup_values else 0
    projected_signups = int(current_signups * (1 + avg_signup_growth))

    now_ts = now.timestamp()
    thirty_days_ago_ts = now_ts - (30 * 86400)
    sixty_days_ago_ts = now_ts - (60 * 86400)
    ninety_days_ago_ts = now_ts - (90 * 86400)

    recent_active = set()
    mid_active = set()
    old_active = set()

    for act in activities:
        uid = act.get('user_id', '')
        ts_str = act.get('timestamp', '')
        try:
            act_ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp()
        except Exception:
            continue
        if act_ts >= thirty_days_ago_ts:
            recent_active.add(uid)
        elif act_ts >= sixty_days_ago_ts:
            mid_active.add(uid)
        elif act_ts >= ninety_days_ago_ts:
            old_active.add(uid)

    total_users = len(users)
    churned_30d = total_users - len(recent_active)
    at_risk = len(recent_active.symmetric_difference(mid_active))

    projected_churn_rate = (churned_30d / total_users * 100) if total_users > 0 else 0

    return {
        'current_mrr': round(current_mrr, 2),
        'projected_mrr_next_month': round(projected_mrr, 2),
        'mrr_growth_rate': round(avg_growth * 100, 2),
        'current_signups_this_month': current_signups,
        'projected_signups_next_month': projected_signups,
        'signup_growth_rate': round(avg_signup_growth * 100, 2),
        'churned_30d': churned_30d,
        'at_risk_users': at_risk,
        'projected_churn_rate': round(projected_churn_rate, 2),
        'mrr_trend': {m: round(monthly_revenue[m], 2) for m in sorted_months[-6:]},
    }


@router.get('/export')
async def export_analytics(
    metrics: str = 'revenue,users',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = 'csv',
    _=Depends(get_current_admin),
):
    metric_list = [m.strip() for m in metrics.split(',')]
    export_data = {}

    if 'revenue' in metric_list:
        orders = await db.orders.find({}, {'_id': 0}).to_list(100000)
        revenue_rows = []
        for order in orders:
            created = order.get('created_at', '')[:10]
            if start_date and created < start_date:
                continue
            if end_date and created > end_date:
                continue
            revenue_rows.append({
                'date': created,
                'order_id': order.get('id', ''),
                'user_id': order.get('user_id', ''),
                'total': order.get('total', 0),
                'status': order.get('status', ''),
            })
        export_data['revenue'] = revenue_rows

    if 'users' in metric_list:
        users = await db.users.find({}, {'_id': 0}).to_list(100000)
        user_rows = []
        for user in users:
            created = user.get('created_at', '')[:10]
            if start_date and created < start_date:
                continue
            if end_date and created > end_date:
                continue
            user_rows.append({
                'user_id': user.get('id', ''),
                'email': user.get('email', ''),
                'created_at': user.get('created_at', ''),
                'plan': user.get('subscription_plan', user.get('plan', '')),
                'source': user.get('acquisition_channel', user.get('source', '')),
            })
        export_data['users'] = user_rows

    if 'signups' in metric_list:
        users = await db.users.find({}, {'_id': 0}).to_list(100000)
        signups_by_day = {}
        for user in users:
            day = user.get('created_at', '')[:10]
            if day:
                signups_by_day[day] = signups_by_day.get(day, 0) + 1
        export_data['signups'] = [{'date': k, 'count': v} for k, v in sorted(signups_by_day.items())]

    if 'churn' in metric_list:
        now = datetime.now(timezone.utc)
        users = await db.users.find({}, {'_id': 0}).to_list(100000)
        activities = await db.user_activities.find({}, {'_id': 0, 'user_id': 1, 'timestamp': 1}).to_list(500000)
        last_active = {}
        for act in activities:
            uid = act.get('user_id', '')
            ts = act.get('timestamp', '')
            if uid not in last_active or ts > last_active[uid]:
                last_active[uid] = ts
        churn_rows = []
        for user in users:
            uid = user.get('id', '')
            la = last_active.get(uid, '')
            days_inactive = 0
            if la:
                try:
                    last_dt = datetime.fromisoformat(la.replace('Z', '+00:00'))
                    days_inactive = (now - last_dt).total_seconds() / 86400
                except Exception:
                    days_inactive = 999
            else:
                days_inactive = 999
            churn_rows.append({
                'user_id': uid,
                'email': user.get('email', ''),
                'days_inactive': round(days_inactive, 1),
                'plan': user.get('subscription_plan', user.get('plan', '')),
                'is_churned': days_inactive > 30,
            })
        export_data['churn'] = churn_rows

    if format == 'csv':
        output = io.StringIO()
        first_metric = metric_list[0] if metric_list else 'data'
        rows = export_data.get(first_metric, [])
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=analytics_export.csv'},
        )

    return {'data': export_data, 'metrics': metric_list, 'format': format}
