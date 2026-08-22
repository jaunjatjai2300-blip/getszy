import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from template_catalog import TEMPLATE_CATALOG, get_template, load_template_html, public_template_catalog, recommend_template_id, render_customer_template


def test_catalogue_contains_licensed_industry_starters():
    public = public_template_catalog()

    assert len(public) >= 25
    assert all(item["license"] == "MIT" for item in public if item["source"] == "JAKS.dev Vault")
    assert any(item["id"] == "dance-academy" and item["source"] == "Getszy curated" for item in public)
    assert all("filename" not in item for item in public)
    assert {"Technology & SaaS", "E-commerce", "Healthcare", "Real Estate", "Food & Beverage"} <= {item["industry"] for item in public}


def test_template_source_is_loaded_only_from_catalogue_root():
    entry = get_template("saas-app")
    html = load_template_html("saas-app")

    assert entry is not None
    assert entry["filename"] == "saas-app-landing.html"
    assert "<!DOCTYPE html>" in html


def test_professional_starter_recommendations_are_deterministic():
    assert recommend_template_id("Build a landing page for Solaour Dance Academy") == "dance-academy"
    assert recommend_template_id("Launch a premium skincare collection") == "brand-foundation"
    assert recommend_template_id("Build a local company introduction page") == "brand-foundation"


def test_dance_template_renders_customer_safe_brand_details():
    html = render_customer_template(
        "dance-academy",
        project_name="Solaour Dance Academy",
        prompt="Build a premium dance academy landing page",
        brief={"primary_cta": "Plan a visit", "offer": "Contemporary dance classes in Jaipur"},
    )
    assert "Solaour Dance Academy" in html
    assert "Plan a visit" in html
    assert "Contemporary dance classes in Jaipur" in html
    assert "{{BRAND_NAME}}" not in html
    assert "/api/builder/template-assets/dance-academy-hero.jpg" in html


def test_unknown_template_is_not_accepted():
    assert get_template("does-not-exist") is None
    try:
        load_template_html("does-not-exist")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown template ID must not resolve to a local file")
