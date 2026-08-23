"""Commercially safe starter-template catalogue for Talk-to-Build Studio.

The bundled Jaks templates are MIT licensed. The source licence and attribution are
preserved in ``starter_templates/jaks/LICENSE`` and ``THIRD_PARTY_NOTICES.md``.
Templates are customer-editable starting points; generated copy, claims, images and
legal content must always be reviewed before a customer publishes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from html import escape
import re


_TEMPLATE_ROOT = Path(__file__).parent / "starter_templates" / "jaks"
_GETSZY_TEMPLATE_ROOT = Path(__file__).parent / "starter_templates" / "getszy"


def _template(
    template_id: str,
    filename: str,
    name: str,
    industry: str,
    outcome: str,
    description: str,
    collection: str = "jaks",
    source: str = "JAKS.dev Vault",
    license_name: str = "MIT",
) -> Dict[str, str]:
    return {
        "id": template_id,
        "filename": filename,
        "name": name,
        "industry": industry,
        "outcome": outcome,
        "description": description,
        "source": source,
        "license": license_name,
        "collection": collection,
    }


TEMPLATE_CATALOG: List[Dict[str, str]] = [
    _template("dance-academy", "dance-academy-premium.html", "Dance Academy", "Dance & Performing Arts", "Capture class enquiries", "A Getszy-curated, image-led dance-academy landing-page starter with private-review safeguards.", "getszy", "Getszy curated", "Getszy customer starter"),
    _template("brand-foundation", "brand-foundation-premium.html", "Professional Brand Foundation", "General Business", "Present a confirmed offer professionally", "A Getszy-curated, image-led first professional landing-page foundation for any business category.", "getszy", "Getszy curated", "Getszy customer starter"),
    _template("saas-app", "saas-app-landing.html", "SaaS App Launch", "Technology & SaaS", "Start trials or book demos", "A conversion-focused product landing page with a clear software offer."),
    _template("saas-dashboard", "saas-cloud-dashboard.html", "Cloud Dashboard", "Technology & SaaS", "Explain a platform or portal", "A product-led starter for cloud, analytics and AI platforms."),
    _template("agency-digital", "agency-digital.html", "Digital Agency", "Professional Services", "Generate qualified enquiries", "A services-first agency site with capability and project sections."),
    _template("agency-marketing", "agency-marketing-hub.html", "Marketing Hub", "Professional Services", "Book a discovery call", "A marketing and consulting starter focused on outcomes."),
    _template("business-corporate", "business-corporate-pro.html", "Corporate Business", "Business", "Establish credibility", "A professional company profile for B2B or local services."),
    _template("business-startup", "business-startup-launch.html", "Startup Launch", "Business", "Validate an offer", "A lean launch page for a new business or product."),
    _template("ecommerce-fashion", "ecommerce-fashion-store.html", "Fashion Store", "E-commerce", "Promote a collection", "A retail storefront starter for catalog-led brands."),
    _template("ecommerce-tech", "ecommerce-tech-shop.html", "Tech Shop", "E-commerce", "Sell a hero product", "A product-focused template for electronics and D2C launches."),
    _template("ecommerce-boutique", "ecommerce-boutique-store.html", "Boutique Store", "E-commerce", "Build a premium product story", "A boutique retail starter for curated product ranges."),
    _template("ecommerce-perfume", "ecommerce-perfume-store.html", "Beauty & Fragrance", "Beauty & Lifestyle", "Launch a premium collection", "A refined visual starter for fragrance, beauty and lifestyle brands."),
    _template("education-courses", "education-online-courses.html", "Online Courses", "Education", "Capture course enquiries", "A course catalogue and enrollment landing page."),
    _template("education-university", "education-university.html", "Education Institute", "Education", "Drive applications", "A training, coaching or academic institution starter."),
    _template("fitness-gym", "fitness-gym.html", "Fitness Gym", "Wellness & Fitness", "Drive memberships", "A performance-led gym, studio or coach landing page."),
    _template("fitness-yoga", "fitness-yoga.html", "Yoga & Wellness", "Wellness & Fitness", "Book a class", "A calm, service-led template for yoga and wellness businesses."),
    _template("medical-clinic", "medical-health-clinic.html", "Health Clinic", "Healthcare", "Request appointments", "A healthcare starter; medical claims and privacy content require customer review."),
    _template("medical-dental", "medical-dental-care.html", "Dental Care", "Healthcare", "Request appointments", "A dental practice starter; medical claims and privacy content require customer review."),
    _template("realestate-luxury", "realestate-luxury-homes.html", "Luxury Properties", "Real Estate", "Capture buyer enquiries", "A premium property and real-estate lead generation layout."),
    _template("realestate-listings", "realestate-property-listings.html", "Property Listings", "Real Estate", "Promote available properties", "A property-listing starter for brokers and developers."),
    _template("restaurant-cafe", "restaurant-cafe-bistro.html", "Cafe & Bistro", "Food & Beverage", "Drive bookings or orders", "A hospitality starter for cafes, restaurants and food brands."),
    _template("restaurant-fine", "restaurant-fine-dining.html", "Fine Dining", "Food & Beverage", "Drive table reservations", "A premium hospitality starter for reservation-led restaurants."),
    _template("portfolio-creative", "portfolio-creative-studio.html", "Creative Studio", "Portfolio & Agency", "Showcase work", "A project-focused visual portfolio for studios and creators."),
    _template("portfolio-developer", "portfolio-developer.html", "Developer Portfolio", "Portfolio", "Win project enquiries", "A technical portfolio starter for freelancers and product builders."),
    _template("blog-modern", "blog-modern.html", "Modern Editorial", "Blog & Editorial", "Grow an audience", "A content-first publication starter with modern article hierarchy."),
    _template("blog-journal", "blog-minimal-journal.html", "Minimal Journal", "Blog & Editorial", "Publish a point of view", "A quiet editorial starter for writers and personal brands."),
    _template("finance-venture", "finance-venture-capital.html", "Venture & Finance", "Finance", "Explain a firm or thesis", "A finance layout; all regulated claims require customer and legal review."),
    _template("agriculture", "agriculture-plant-scan.html", "Agriculture Product", "Agriculture", "Explain a product or service", "An agriculture and environmental technology starter."),
    _template("automotive", "automotive-electric-launch.html", "Electric Vehicle Launch", "Automotive", "Launch a product", "A transport or automotive product landing-page starter."),
    _template("photography-gallery", "photography-gallery.html", "Photography Gallery", "Portfolio", "Showcase a visual service", "A photo-led starter for photographers and visual creators."),
    _template("photography-wedding", "photography-wedding.html", "Wedding Photography", "Events & Wedding", "Capture event enquiries", "A wedding and event creative starter."),
]


def public_template_catalog() -> List[Dict[str, Any]]:
    """Return catalogue data safe for customer UI; never expose local paths."""
    return [{key: value for key, value in entry.items() if key != "filename"} for entry in TEMPLATE_CATALOG]


def get_template(template_id: str | None) -> Dict[str, str] | None:
    if not template_id:
        return None
    return next((entry for entry in TEMPLATE_CATALOG if entry["id"] == template_id), None)


def recommend_template_id(prompt: str, brief: Dict[str, Any] | None = None) -> str:
    """Choose a conservative visual starter for a first landing-page draft.

    The recommendation is deterministic and intentionally avoids a generic AI layout as
    the default launch path. Customers can choose a different licensed starter in the
    workspace, but direct API callers receive the same professional baseline.
    """
    brief = brief or {}
    text = " ".join([
        str(prompt or ""), str(brief.get("offer") or ""),
        str(brief.get("audience") or ""), str(brief.get("visual_style") or ""),
    ]).lower()
    rules = [
        (("dance",), "dance-academy"),

    ]
    for keywords, template_id in rules:
        if any(keyword in text for keyword in keywords):
            return template_id
    return "brand-foundation"


def load_template_html(template_id: str) -> str:
    entry = get_template(template_id)
    if not entry:
        raise KeyError(template_id)
    root = _GETSZY_TEMPLATE_ROOT if entry.get("collection") == "getszy" else _TEMPLATE_ROOT
    template_path = (root / entry["filename"]).resolve()
    if template_path.parent != root.resolve() or not template_path.is_file():
        raise FileNotFoundError(entry["filename"])
    return template_path.read_text(encoding="utf-8")


def _safe_brand_name(value: str | None, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    return cleaned[:80] or fallback


def render_customer_template(template_id: str, *, project_name: str | None, prompt: str, brief: Dict[str, Any] | None = None) -> str:
    """Render a customer-safe starter without demo identity or invented facts."""
    brief = brief or {}
    html = load_template_html(template_id)
    if template_id not in {"dance-academy", "brand-foundation"}:
        return html

    fallback_brand = "Your Dance Academy" if template_id == "dance-academy" else "Your Brand"
    brand = _safe_brand_name(brief.get("brand_name") or project_name, fallback_brand)
    offer = _safe_brand_name(brief.get("offer"), "Explore your real dance classes, workshops and studio experience." if template_id == "dance-academy" else "Present your confirmed offer with a considered visual first impression.")
    cta = _safe_brand_name(brief.get("primary_cta"), "Plan your first visit" if template_id == "dance-academy" else "Start a conversation")
    goal = _safe_brand_name(brief.get("primary_goal"), "Professional landing page")
    replacements = {
        "{{BRAND_NAME}}": escape(brand),
        "{{OFFER}}": escape(offer),
        "{{PRIMARY_CTA}}": escape(cta),
        "{{PRIMARY_GOAL}}": escape(goal),
    }
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html
