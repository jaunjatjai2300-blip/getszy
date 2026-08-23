import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from prompt_architect import BriefIntel, detect_intent


def test_brief_intel_valid():
    b = BriefIntel.validate_raw({
        'intent': 'website',
        'name': 'Glow Salon',
        'category': 'beauty',
        'audience': 'women 18-35',
        'tone': 'premium',
        'style': 'modern',
        'language': 'hinglish',
        'goal': 'increase bookings',
        'key_points': ['organic products', 'certified stylists'],
        'cta': 'Book Now',
        'visual_style': 'soft pastels, clean layouts',
        'structured_prompt': 'Build a premium salon website...',
    })
    assert b.intent == 'website'
    assert b.name == 'Glow Salon'
    assert len(b.key_points) == 2


def test_brief_intel_minimal():
    b = BriefIntel.validate_raw({'intent': 'copy'})
    assert b.intent == 'copy'
    assert b.name is None
    assert b.key_points == []
    assert b.cta == 'Learn more'


def test_brief_intel_extra_fields_ignored():
    b = BriefIntel.validate_raw({
        'intent': 'video',
        'custom_field': 'should be ignored',
        'another': 123,
    })
    assert b.intent == 'video'
    assert not hasattr(b, 'custom_field')


def test_brief_intel_invalid_type():
    with pytest.raises(Exception):
        BriefIntel.validate_raw({'key_points': 'not a list'})


def test_brief_intel_missing_intent():
    with pytest.raises(Exception):
        BriefIntel.validate_raw({'name': 'no intent field'})


def test_detect_intent_website():
    assert detect_intent('make me a website for my business') == 'website'


def test_detect_intent_video():
    assert detect_intent('create a youtube video about fitness') == 'video'


def test_detect_intent_saree():
    assert detect_intent('I sell sarees') == 'copy'


def test_detect_intent_dance_academy():
    assert detect_intent('dance academy ke liye website banao') == 'website'
