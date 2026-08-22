import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from template_catalog import TEMPLATE_CATALOG, get_template, load_template_html, public_template_catalog


def test_catalogue_contains_licensed_industry_starters():
    public = public_template_catalog()

    assert len(public) >= 25
    assert all(item["license"] == "MIT" for item in public)
    assert all("filename" not in item for item in public)
    assert {"Technology & SaaS", "E-commerce", "Healthcare", "Real Estate", "Food & Beverage"} <= {item["industry"] for item in public}


def test_template_source_is_loaded_only_from_catalogue_root():
    entry = get_template("saas-app")
    html = load_template_html("saas-app")

    assert entry is not None
    assert entry["filename"] == "saas-app-landing.html"
    assert "<!DOCTYPE html>" in html


def test_unknown_template_is_not_accepted():
    assert get_template("does-not-exist") is None
    try:
        load_template_html("does-not-exist")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown template ID must not resolve to a local file")
