import os
import sys
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brief_intelligence import (
    BriefIntelligenceV3,
    merge_latest_explicit_brief,
    validate_and_sanitize_brief,
)


def payload(**overrides):
    base = {
        'request_type': 'create',
        'business_name': None,
        'business_type': None,
        'location': None,
        'target_audience': [],
        'services_or_products': [],
        'design_direction': {'style': None, 'colors': []},
        'primary_goal': None,
        'cta': None,
        'languages': [],
        'contact': {'phone': None, 'email': None, 'whatsapp': None, 'website': None},
        'social_links': {'instagram': None, 'facebook': None, 'youtube': None},
        'requested_pages': [],
        'functional_requirements': [],
        'specific_features': [],
        'approved_facts': [],
    }
    base.update(overrides)
    return base


def test_schema_rejects_unknown_keys():
    bad = payload(unapproved_claim='India\'s best salon')
    with pytest.raises(Exception):
        validate_and_sanitize_brief(bad, 'Build a salon website')


def test_beauty_salon_does_not_infer_target_audience_or_goal():
    raw = 'Build a premium website for my beauty salon.'
    result = validate_and_sanitize_brief(payload(
        business_type='Beauty salon',
        target_audience=['Women'],
        primary_goal='Branding',
        cta='Book now',
    ), raw)

    assert result.business_type == 'Beauty salon'
    assert result.target_audience == []
    assert result.primary_goal is None
    assert result.cta is None


def test_explicit_audience_and_admission_goal_are_retained():
    raw = 'Our dance academy has classes for kids and adults. Admission ke liye website banao.'
    result = validate_and_sanitize_brief(payload(
        business_type='Dance Academy',
        target_audience=['Kids', 'Adults'],
        primary_goal='Admissions',
        services_or_products=['classes'],
    ), raw)

    assert result.business_type == 'Dance Academy'
    assert result.target_audience == ['Kids', 'Adults']
    assert result.primary_goal == 'Admissions'


def test_phone_is_not_copied_into_whatsapp():
    raw = 'Phone number is +91 98765 43210. Create my salon website.'
    result = validate_and_sanitize_brief(payload(
        contact={'phone': '+91 98765 43210', 'email': None, 'whatsapp': '+91 98765 43210', 'website': None},
    ), raw)

    assert result.contact.phone == '+91 98765 43210'
    assert result.contact.whatsapp is None


def test_explicit_contact_and_facts_are_preserved_without_strengthening():
    raw = 'Dr Hadsange eye specialist hain. 1000 patients ka experience hai. WhatsApp +91-9988776655.'
    result = validate_and_sanitize_brief(payload(
        contact={'phone': None, 'email': None, 'whatsapp': '+91-9988776655', 'website': None},
        approved_facts=['Dr Hadsange is an eye specialist', '1000 patients experience', '1000+ happy patients'],
    ), raw)

    assert result.contact.whatsapp == '+91-9988776655'
    assert '1000+ happy patients' not in result.approved_facts
    assert 'Dr Hadsange is an eye specialist' in result.approved_facts


def test_latest_explicit_value_wins_without_empty_erasure():
    prior = BriefIntelligenceV3(business_name='Glow Salon', location='Jaipur')
    latest = BriefIntelligenceV3(business_name='Glow & Grace')
    merged = merge_latest_explicit_brief(prior, latest)

    assert merged.business_name == 'Glow & Grace'
    assert merged.location == 'Jaipur'
