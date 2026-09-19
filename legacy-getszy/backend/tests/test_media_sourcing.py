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


# ── media reaches the page, and only in the approved shape ───────────────────
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 4096


def _published_asset(tmp_path, monkeypatch, **over):
    """A stored + published asset, without touching the network."""
    monkeypatch.setenv("MEDIA_CACHE_DIR", str(tmp_path))
    cand = _c(license_code=over.pop("license_code", "cc0"),
              source_url="https://openverse.org/image/x1",
              license_url=over.pop("license_url", ""),
              creator=over.pop("creator", ""), width=1600, height=900)
    asset = ms.store(cand, JPEG_BYTES, "image/jpeg", query="gym",
                     store_dir=tmp_path / "stock")
    published = ms.publish(asset)
    assert published is not None
    return published


def test_generated_page_uses_the_local_url_and_never_a_third_party_host(tmp_path, monkeypatch):
    """The whole point of self-hosting: a customer page must reference OUR url,
    so no provider becomes a runtime dependency or a tracker on their site."""
    import re
    from builder_agents import _premium_template

    asset = _published_asset(tmp_path, monkeypatch)
    brief = {"brand_name": "Iron Vault", "vertical": "fitness",
             "design_recipe": "cinematic_luxury",
             "_media_assets": [asset], "_hero_asset": asset}
    html = _premium_template("cinematic luxury fitness club", brief)

    srcs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    assert srcs, "photography was supplied but no <img> was rendered"
    assert all(s.startswith("/api/assets/") for s in srcs), srcs
    assert not [s for s in srcs if s.startswith("http")], "third-party image hotlink leaked"
    # the opaque id, never a filesystem path
    assert str(tmp_path) not in html and "stock/" not in html


def test_page_with_photography_carries_no_emoji_or_cartoon_art(tmp_path, monkeypatch):
    from builder_agents import _premium_template
    asset = _published_asset(tmp_path, monkeypatch)
    html = _premium_template("cinematic luxury fitness club", {
        "brand_name": "Iron Vault", "vertical": "fitness",
        "design_recipe": "cinematic_luxury",
        "_media_assets": [asset], "_hero_asset": asset})
    assert not [ch for ch in html if ord(ch) > 0x2500], "emoji artwork present"
    low = html.lower()
    for banned in ("cartoon", "mascot", "clipart", "undraw", "storyset"):
        assert banned not in low


def test_attribution_appears_next_to_an_attribution_licensed_photo(tmp_path, monkeypatch):
    from builder_agents import _premium_template
    # A BY licence needs creator + licence URL up front, otherwise the pipeline
    # correctly flags it requires_review and refuses to publish it at all.
    asset = _published_asset(
        tmp_path, monkeypatch, license_code="by", creator="A. Photographer",
        license_url="https://creativecommons.org/licenses/by/4.0/")
    assert asset.attribution_required is True
    html = _premium_template("cinematic luxury fitness club", {
        "brand_name": "Iron Vault", "vertical": "fitness",
        "design_recipe": "cinematic_luxury",
        "_media_assets": [asset], "_hero_asset": asset})
    assert "A. Photographer" in html and 'class="credit"' in html


def test_unpublished_asset_is_never_embedded(tmp_path, monkeypatch):
    """An asset with bytes but no delivery URL must not appear in the page --
    the builder degrades to the designed treatment instead of a broken image."""
    import re
    from builder_agents import _premium_template
    monkeypatch.setenv("MEDIA_CACHE_DIR", str(tmp_path))
    cand = _c(license_code="cc0", source_url="https://openverse.org/i/1",
              width=1600, height=900)
    stored = ms.store(cand, JPEG_BYTES, "image/jpeg", store_dir=tmp_path / "stock")
    assert stored.publishable() is False

    html = _premium_template("cinematic luxury fitness club", {
        "brand_name": "Iron Vault", "vertical": "fitness",
        "design_recipe": "cinematic_luxury",
        "_media_assets": [stored], "_hero_asset": stored})
    assert not re.findall(r'<img[^>]+src="([^"]+)"', html)
    assert not [ch for ch in html if ord(ch) > 0x2500]   # and still no emoji filler


def test_no_media_available_still_produces_a_premium_non_cartoon_page(tmp_path):
    """The graceful path: photography requested, none obtainable. The page must
    still be premium and must NOT reach for clip-art."""
    from builder_agents import _premium_template
    from builder_quality import evaluate_landing_page_quality
    brief = {"brand_name": "Iron Vault", "vertical": "fitness",
             "design_recipe": "cinematic_luxury"}
    html = _premium_template("cinematic luxury fitness club", brief)
    assert evaluate_landing_page_quality(html, brief)["status"] == "ready_for_human_review"
    assert not [ch for ch in html if ord(ch) > 0x2500]
    assert "pv-cinematic" in html      # the direction's designed treatment


# ── relevance: a real photograph of the WRONG thing is not acceptable ────────
def _cand(title, tags=(), **kw):
    return _c(title=title, tags=tuple(tags), license_code=kw.pop("license_code", "cc0"),
              source_url="https://openverse.org/i/1", **kw)


def test_irrelevant_photograph_scores_zero_however_good_its_licence():
    """The failure this prevents: a CC0 photograph of a street outranking a
    CC-BY photograph of the actual subject, because ranking looked at licence
    and resolution but never at what the picture showed."""
    street = _cand("Church Street, Hereford", ("street", "building"))
    salon = _cand("D&L Hair Salon, South Miami", ("salon", "hair"), license_code="by",
                  license_url="https://creativecommons.org/licenses/by/2.0/",
                  creator="A. Photographer")
    q = "hair salon interior"
    assert ms.relevance(street, q) == 0.0
    assert ms.relevance(salon, q) > 0.5
    # and selection follows relevance, not the simpler licence
    assert ms.select([street, salon], orientation="landscape", min_width=900,
                     query=q).title.startswith("D&L")


def test_a_single_generic_tag_match_is_not_evidence_of_relevance():
    """Machine tags are broad: a manicurist IS tagged 'technician'. One such tag,
    with nothing in the title, must not qualify the image for a plumbing site."""
    manicurist = _cand("A manicurist at work", ("beauty", "manicure", "technician", "job"))
    assert ms.relevance(manicurist, "technician working at work") == 0.0
    assert ms.select([manicurist], orientation="landscape", min_width=900,
                     query="technician working at work") is None


def test_two_corroborating_tags_do_qualify_a_descriptively_titled_photo():
    """Real subject photos often have prose titles; two independent tag matches
    are enough corroboration so they are not thrown away."""
    gym = _cand("Girl doing stability ball crunches",
                ("gym", "fitness", "training", "exercise"))
    assert ms.relevance(gym, "gym strength training") >= ms.MIN_RELEVANCE


def test_relevance_ignores_generic_words():
    """'work', 'home', 'business' appear on almost every stock photograph and
    must not, by themselves, make an image relevant."""
    generic = _cand("Work at Home", ("business", "computer", "desk", "work", "home"))
    assert ms.relevance(generic, "home repair professional") == 0.0


def test_no_relevant_image_returns_none_rather_than_an_irrelevant_one():
    irrelevant = [_cand("Sunset over a lake", ("water", "sky")),
                  _cand("Vintage car show", ("car", "chrome"))]
    assert ms.select(irrelevant, orientation="landscape", min_width=900,
                     query="hair salon interior") is None


# ── NAT64: a resolver quirk must not silently disable sourcing ───────────────
def test_nat64_addresses_are_judged_by_their_embedded_ipv4():
    """DNS64 environments return 64:ff9b::/96 addresses, which Python classifies
    as 'reserved'. Treating those as unsafe silently disabled image sourcing
    entirely. The embedded IPv4 is the real destination -- and judging it is
    also STRICTER, since a NAT64-wrapped private address is now caught."""
    import ipaddress
    public = ipaddress.ip_address("64:ff9b::ac42:9956")        # 172.66.153.86
    private = ipaddress.ip_address("64:ff9b::a00:1")           # 10.0.0.1
    loopback = ipaddress.ip_address("64:ff9b::7f00:1")         # 127.0.0.1
    assert str(ms._effective_ip(public)) == "172.66.153.86"
    assert ms._effective_ip(private).is_private is True
    assert ms._effective_ip(loopback).is_loopback is True
    # a plain IPv6 address is untouched
    assert str(ms._effective_ip(ipaddress.ip_address("2606:4700::1111"))) == "2606:4700::1111"


# ── provider-supplied text never decorates a customer's page ─────────────────
def test_provider_display_text_is_stripped_of_emoji_and_symbols():
    """A real Flickr account name encountered in production sourcing carried
    pictographs. Attribution must credit the human without importing their
    decoration into a paying customer's website."""
    cleaned = ms.clean_provider_text("666isMONEY \u262e \u2665 & \u2620")
    assert "666isMONEY" in cleaned
    assert not [ch for ch in cleaned if ord(ch) > 0x2500]

    asset = ms.MediaAsset(asset_id="a", path="p", provider="openverse",
                          provider_asset_id="x", license_code="by",
                          license_url="https://creativecommons.org/licenses/by/2.0/",
                          creator="666isMONEY \u262e \u2665 & \u2620",
                          source_url="https://flickr.com/x", attribution_required=True)
    html = ms.attribute(asset)
    assert not [ch for ch in html if ord(ch) > 0x2500]
    assert "666isMONEY" in html          # attribution is still given


def test_clean_provider_text_keeps_ordinary_names_and_accents():
    assert ms.clean_provider_text("José Álvarez-Núñez") == "José Álvarez-Núñez"
    assert ms.clean_provider_text("USDA Forest Service") == "USDA Forest Service"
    assert ms.clean_provider_text("   spaced   out   ") == "spaced out"
