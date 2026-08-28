"""Proof that the reliability layer is LIVE on the real customer build path.

The paid customer build enters through routes_builder._run_website_operation ->
_safe_compose. These tests drive _safe_compose directly (LLM composition mocked)
and prove the reliability layer actually runs: resource admission is consulted,
a successful compose flows through unchanged, an admission REJECT degrades to the
deterministic template instead of failing a paying customer, and any pipeline
failure still returns a complete page. This is the wiring the earlier suite only
asserted was 'callable'.
"""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test")
os.environ.setdefault("JWT_SECRET", "review-only-secret-32-characters-long!!")

import builder_agents  # noqa: E402
import routes_builder  # noqa: E402
from resource_admission import AdmissionDecision  # noqa: E402

GOOD_HTML = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
             "<meta name='viewport' content='width=device-width, initial-scale=1'>"
             "<title>Acme</title></head><body><header><h1>Acme</h1></header>"
             "<main><section><p>Real composed content.</p>"
             "<a href='#contact'>Get started</a></section></main>"
             "<footer>hello@acme.example</footer></body></html>")


def _admission(decision):
    return types.SimpleNamespace(decision=decision,
                                 to_dict=lambda: {"decision": decision.value}, reason="test")


@pytest.fixture
def reliable(monkeypatch):
    state = {"admit": 0, "compose": 0, "admission": _admission(AdmissionDecision.RUN)}

    async def fake_compose_fast(prompt, brief=None, session_id="builder", style_profile=None):
        state["compose"] += 1
        return GOOD_HTML

    async def fake_admit(*a, **k):
        state["admit"] += 1
        return state["admission"]

    monkeypatch.setattr(builder_agents, "compose_site_fast", fake_compose_fast)
    monkeypatch.setattr(builder_agents, "admit_task", fake_admit)
    return state


async def test_safe_compose_runs_reliability_on_success(reliable):
    html, used_fallback = await routes_builder._safe_compose(
        "Build me a launch page", "sess-1", {"brand_name": "Acme"})
    assert used_fallback is False
    assert html == GOOD_HTML                 # the composed html flows through unchanged
    assert reliable["admit"] == 1            # PROOF the reliability layer actually ran
    assert reliable["compose"] == 1


async def test_admission_degrade_still_delivers_the_real_page(reliable):
    reliable["admission"] = _admission(AdmissionDecision.DEGRADE)
    html, used_fallback = await routes_builder._safe_compose("Build", "sess-2", {})
    assert used_fallback is False and html == GOOD_HTML   # degrade still composes a real page
    assert reliable["admit"] == 1


async def test_admission_reject_degrades_to_template_not_error(reliable, monkeypatch):
    reliable["admission"] = _admission(AdmissionDecision.REJECT)
    seen = {}

    def fake_template(prompt, brief=None):
        seen["template"] = True
        return "<html><body>premium template page</body></html>"

    monkeypatch.setattr(routes_builder, "_premium_template", fake_template)
    html, used_fallback = await routes_builder._safe_compose("Build", "sess-3", {})
    assert used_fallback is True                    # degrade, never a customer-facing error
    assert seen.get("template") is True             # customer still receives a complete page
    assert html and "premium template" in html
    assert reliable["admit"] == 1                   # admission was consulted before falling back


async def test_pipeline_failure_falls_back_to_a_page(reliable, monkeypatch):
    async def boom(prompt, brief=None, session_id="builder", style_profile=None):
        raise RuntimeError("every provider down")

    monkeypatch.setattr(builder_agents, "compose_site_fast", boom)
    monkeypatch.setattr(routes_builder, "_premium_template",
                        lambda p, b=None: "<html><body>fallback</body></html>")
    html, used_fallback = await routes_builder._safe_compose("Build", "sess-4", {})
    assert used_fallback is True and "fallback" in html   # never a blank/error to the customer
