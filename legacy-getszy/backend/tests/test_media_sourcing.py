"""Media sourcing: real photography, but only where provenance holds up.

These tests pin the rules that keep the builder legally and operationally safe:
provider licence claims are classified, never rubber-stamped; incompatible or
incomplete metadata cannot reach a customer page; downloads are constrained at
the transport and byte level; and every failure degrades gracefully so website
generation is never blocked by an image provider.
"""
import hashlib

import pytest

import media_sourcing as ms

C = ms.MediaCandidate


def _c(**kw):
    base = dict(provider="openverse", provider_asset_id="x1",
                url="https://images.example.org/a.jpg", width=1600, height=900)
    base.update(kw)
    return C(**base)


# ── licence classification ───────────────────────────────────────────────────
def test_incompatible_licences_are_rejected_outright():
    for code, _reason in ms.REFUSED_LICENCES.items():
        state, why = ms.validate_license(_c(license_code=code))
        assert state == ms.REJECTED, code
        assert why
        assert not ms.is_acceptable(state)


def test_missing_or_unknown_licence_is_refused_never_assumed_permissive():
    assert ms.validate_license(_c(license_code=""))[0] == ms.REJECTED
    assert ms.validate_license(_c(license_code="mystery-licence"))[0] == ms.REJECTED


def test_provider_claim_is_never_auto_promoted_to_verified():
    """An aggregator's licence field is a DECLARATION. Automatic acceptance may
    reach 'provider_declared' at most; 'verified' requires a human/records check
    and must never be a side effect of a successful HTTP call."""
    good = _c(license_code="cc0", source_url="https://openverse.org/image/x1")
    state, reason = ms.validate_license(good)
    assert state == ms.PROVIDER_DECLARED
    assert state != ms.VERIFIED
    assert "not independently verified" in reason.lower()


def test_compatible_but_incomplete_metadata_requires_review_and_is_not_auto_used():
    """CC-BY with no creator/licence URL is compatible in principle but cannot be
    attributed correctly, so it must be flagged rather than silently published."""
    gap = _c(license_code="by", creator="", license_url="", source_url="")
    state, _ = ms.validate_license(gap)
    assert state == ms.REQUIRES_REVIEW
    assert not ms.is_acceptable(state)
    assert ms.select([gap], orientation="landscape", min_width=1200) is None


def test_selection_prefers_the_simplest_licence_then_orientation():
    cc0 = _c(license_code="cc0", source_url="https://openverse.org/i/1")
    by = _c(provider_asset_id="x2", license_code="by", creator="A. Photographer",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            source_url="https://openverse.org/i/2", width=4000, height=2500)
    # BY has far higher resolution, but CC0 carries no attribution burden
    assert ms.select([by, cc0], orientation="landscape", min_width=1200).license_code == "cc0"


def test_undersized_images_are_not_selected():
    small = _c(license_code="cc0", source_url="https://o.org/i", width=400, height=300)
    assert ms.select([small], orientation="landscape", min_width=1200) is None


# ── attribution ──────────────────────────────────────────────────────────────
def test_attribution_rendered_for_by_licences_and_omitted_for_cc0():
    by = ms.MediaAsset(asset_id="a", path="p", provider="openverse", provider_asset_id="x",
                       license_code="by", license_url="https://creativecommons.org/licenses/by/4.0/",
                       creator="A. Photographer", source_url="https://openverse.org/i/2",
                       attribution_required=True)
    html = ms.attribute(by)
    assert "A. Photographer" in html and "CC BY" in html and "creativecommons.org" in html
    cc0 = ms.MediaAsset(asset_id="b", path="p", provider="openverse", provider_asset_id="y",
                        license_code="cc0", attribution_required=False)
    assert ms.attribute(cc0) == ""


def test_attribution_escapes_provider_supplied_text():
    hostile = ms.MediaAsset(asset_id="c", path="p", provider="openverse", provider_asset_id="z",
                            license_code="by", license_url="https://x.org/l",
                            creator='<script>alert(1)</script>', attribution_required=True)
    out = ms.attribute(hostile)
    assert "<script>" not in out and "&lt;script&gt;" in out


# ── transport / content security ─────────────────────────────────────────────
@pytest.mark.parametrize("url", [
    "http://images.example.org/a.jpg",      # not HTTPS
    "https://localhost/a.jpg",              # loopback
    "https://127.0.0.1/a.jpg",
    "https://10.0.0.5/a.jpg",               # private range
    "https://169.254.169.254/latest/meta",  # cloud metadata endpoint
    "ftp://images.example.org/a.jpg",
])
def test_unsafe_urls_are_refused(url):
    assert ms._safe_url(url) is False


def test_magic_bytes_must_match_a_supported_image():
    assert ms._sniff(b"\xff\xd8\xff\xe0rest")[0] == "image/jpeg"
    assert ms._sniff(b"\x89PNG\r\n\x1a\nrest")[0] == "image/png"
    assert ms._sniff(b"RIFF____WEBPVP8 ")[0] == "image/webp"
    # an SVG or HTML payload dressed up as an image is not storable
    assert ms._sniff(b"<svg xmlns='http://www.w3.org/2000/svg'>")[0] is None
    assert ms._sniff(b"<!DOCTYPE html>")[0] is None


def test_store_refuses_non_image_bytes(tmp_path):
    with pytest.raises(ms.MediaUnavailable):
        ms.store(_c(license_code="cc0"), b"<svg>not an image</svg>", store_dir=tmp_path)


# ── storage + provenance record ──────────────────────────────────────────────
def test_stored_asset_records_full_auditable_provenance(tmp_path):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 4096
    cand = _c(license_code="by", creator="A. Photographer",
              license_url="https://creativecommons.org/licenses/by/4.0/",
              license_version="4.0", source_url="https://openverse.org/image/x1",
              raw={"id": "x1", "license": "by", "source": "flickr"})
    asset = ms.store(cand, png, "image/png", query="gym training", store_dir=tmp_path)

    assert asset.content_sha256 == hashlib.sha256(png).hexdigest()
    assert asset.provider == "openverse" and asset.provider_asset_id == "x1"
    assert asset.license_code == "by" and asset.license_version == "4.0"
    assert asset.license_url and asset.source_url and asset.creator
    assert asset.retrieved_at and asset.stored_at
    assert asset.raw_metadata.get("source") == "flickr"
    assert asset.provenance_state == ms.PROVIDER_DECLARED and asset.provenance_reason
    assert asset.query == "gym training"
    # sidecar sits beside the bytes so an audit never needs the database
    assert (tmp_path / f"{asset.asset_id}.json").exists()


def test_stored_filename_is_generated_not_provider_controlled(tmp_path):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 4096
    hostile = _c(license_code="cc0", source_url="https://o.org/i",
                 provider_asset_id="../../etc/passwd", title="../../evil")
    asset = ms.store(hostile, png, "image/png", store_dir=tmp_path)
    assert ".." not in asset.path
    assert asset.asset_id in asset.path and len(asset.asset_id) == 32


def test_bytes_on_disk_are_not_permission_to_publish(tmp_path):
    """Storage and publication are separate concerns: an asset is publishable
    only once a delivery layer has assigned it a URL. This is what keeps the
    'no public delivery yet' boundary honest."""
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 4096
    asset = ms.store(_c(license_code="cc0", source_url="https://o.org/i"), png,
                     "image/png", store_dir=tmp_path)
    assert asset.publishable() is False
    asset.public_url = "https://getszy.com/assets/" + asset.asset_id
    assert asset.publishable() is True
    # a review-flagged asset stays unpublishable even with a URL
    asset.provenance_state = ms.REQUIRES_REVIEW
    assert asset.publishable() is False


# ── graceful degradation: media never blocks a build ─────────────────────────
@pytest.mark.asyncio
async def test_provider_failure_returns_none_and_never_raises(monkeypatch):
    class Broken(ms.MediaProvider):
        name = "broken"

        async def search(self, query, *, count=12, orientation="landscape"):
            raise RuntimeError("provider down")

    monkeypatch.setattr(ms, "_PROVIDERS", [Broken()])
    assert await ms.source_image("gym training") is None


@pytest.mark.asyncio
async def test_no_licence_clean_candidate_returns_none_rather_than_a_fallback_image(monkeypatch):
    class OnlyNC(ms.MediaProvider):
        name = "onlync"

        async def search(self, query, *, count=12, orientation="landscape"):
            return [_c(license_code="by-nc"), _c(license_code="by-nd")]

    monkeypatch.setattr(ms, "_PROVIDERS", [OnlyNC()])
    assert await ms.source_image("gym training") is None


def test_default_provider_needs_no_credentials_or_customer_account():
    ov = ms.OpenverseProvider()
    assert ov.requires_credentials is False
    assert ov.available() is True
    assert any(p.name == "openverse" for p in ms.providers())


def test_new_providers_register_without_touching_the_builder():
    class Fake(ms.MediaProvider):
        name = "fake"

    before = len(ms.providers())
    try:
        ms.register_provider(Fake())
        assert any(p.name == "fake" for p in ms.providers())
        assert len(ms.providers()) == before + 1
    finally:
        ms._PROVIDERS[:] = [p for p in ms._PROVIDERS if p.name != "fake"]
