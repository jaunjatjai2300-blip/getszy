import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from builder_controls import mission_control_state


def _ready_quality():
    return {
        'status': 'ready_for_human_review',
        'score': 94,
        'required_checks_passed': 6,
        'required_checks_total': 6,
    }


def _complete_brief():
    return {
        'audience': 'Indian shoppers',
        'primary_goal': 'Collect qualified leads',
        'primary_cta': 'Get the edit',
        'offer': 'A curated beauty collection',
    }


def test_controls_require_complete_brief_and_observable_quality():
    state = mission_control_state({
        'brief': _complete_brief(),
        'html_content': '<!doctype html><html></html>',
        'quality_report': _ready_quality(),
        'evidence_items': [{'status': 'approved'}],
        'version_count': 1,
    })

    assert state['eligible_for_customer_review'] is True
    assert state['production_ready'] is False
    assert state['current_step'] == 'release'
    assert state['quality']['is_ready_for_human_review'] is True


def test_controls_block_review_when_evidence_is_blocked():
    state = mission_control_state({
        'brief': _complete_brief(),
        'html_content': '<!doctype html><html></html>',
        'quality_report': _ready_quality(),
        'evidence_items': [{'status': 'blocked', 'claim': 'Best in India'}],
    })

    evidence_step = next(step for step in state['steps'] if step['key'] == 'evidence')
    assert evidence_step['status'] == 'blocked'
    assert state['eligible_for_customer_review'] is False


def test_controls_never_treat_unrun_quality_as_release_ready():
    state = mission_control_state({
        'brief': _complete_brief(),
        'html_content': '<!doctype html><html></html>',
        'quality_report': None,
        'evidence_items': [{'status': 'approved'}],
    })

    quality_step = next(step for step in state['steps'] if step['key'] == 'quality')
    assert quality_step['status'] == 'not_started'
    assert state['eligible_for_customer_review'] is False
    assert state['production_ready'] is False
