"""Security contract for the ONE unauthenticated media route.

This route exists so generated customer sites can show real photographs without
hotlinking a third party. That makes it the only place where bytes leave the
platform without an auth check, so its boundaries are tested explicitly:
opaque ids only, one directory only, publishable assets only, real images only,
and no way to reach private or user-uploaded media.
"""
import importlib
import json
import os
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 4096
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096


@pytest.fixture
def media_env(tmp_path, monkeypatch):
    """A fresh media root: private files at the root, generated stock beneath."""
    monkeypatch.setenv("MEDIA_CACHE_DIR", str(tmp_path))
    import routes_media_public as rmp
    importlib.reload(rmp)

    stock = tmp_path / "stock"
    stock.mkdir(parents=True, exist_ok=True)

    # A private/user-uploaded file lives in the media root, NOT in stock.
    (tmp_path / "private-user-upload.jpg").write_bytes(JPEG)

    app = FastAPI()
    app.include_router(rmp.router, prefix="/api")
    return {"client": TestClient(app), "stock": stock, "root": tmp_path, "mod": rmp}


def _publish(stock, *, data=JPEG, ext=".jpg", content_type="image/jpeg",
             state="provider_declared", public=True, asset_id=None):
    aid = asset_id or uuid.uuid4().hex
    (stock / f"{aid}{ext}").write_bytes(data)
    record = {
        "asset_id": aid, "provider": "openverse", "provider_asset_id": "x",
        "license_code": "cc0", "content_type": content_type,
        "provenance_state": state,
        "public_url": f"/api/assets/{aid}{ext}" if public else "",
    }
    (stock / f"{aid}.json").write_text(json.dumps(record), encoding="utf-8")
    return aid


# ── the happy path ───────────────────────────────────────────────────────────
def test_published_asset_is_served_with_correct_type_and_headers(media_env):
    aid = _publish(media_env["stock"])
    r = media_env["client"].get(f"/api/assets/{aid}.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/jpeg")
    assert r.content == JPEG
    # cache + hardening headers
    assert "immutable" in r.headers["cache-control"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["cross-origin-resource-policy"] == "cross-origin"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_png_is_served_when_stored_as_png(media_env):
    aid = _publish(media_env["stock"], data=PNG, ext=".png", content_type="image/png")
    r = media_env["client"].get(f"/api/assets/{aid}.png")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/png")


# ── publication is an explicit act ───────────────────────────────────────────
def test_asset_without_a_public_url_is_not_served(media_env):
    """Bytes on disk are not permission to publish."""
    aid = _publish(media_env["stock"], public=False)
    assert media_env["client"].get(f"/api/assets/{aid}.jpg").status_code == 404


@pytest.mark.parametrize("state", ["requires_review", "rejected", "", "bogus"])
def test_non_acceptable_provenance_states_are_not_served(media_env, state):
    aid = _publish(media_env["stock"], state=state)
    assert media_env["client"].get(f"/api/assets/{aid}.jpg").status_code == 404


def test_file_without_a_provenance_sidecar_is_not_served(media_env):
    aid = uuid.uuid4().hex
    (media_env["stock"] / f"{aid}.jpg").write_bytes(JPEG)   # bytes only, no record
    assert media_env["client"].get(f"/api/assets/{aid}.jpg").status_code == 404


# ── private media is unreachable ─────────────────────────────────────────────
def test_private_user_media_outside_stock_cannot_be_reached(media_env):
    """The private upload exists in the media root; this route serves only the
    stock subdirectory, so there is no id that resolves to it."""
    assert (media_env["root"] / "private-user-upload.jpg").exists()
    for attempt in ("private-user-upload.jpg", "..%2Fprivate-user-upload.jpg",
                    "../private-user-upload.jpg"):
        assert media_env["client"].get(f"/api/assets/{attempt}").status_code in (404, 400)


@pytest.mark.parametrize("evil", [
    "../../etc/passwd",
    "..%2f..%2fetc%2fpasswd",
    "....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "/etc/passwd",
    "C:\\\\Windows\\\\win.ini",
    "..\\\\..\\\\windows\\\\win.ini",
])
def test_path_traversal_is_refused(media_env, evil):
    r = media_env["client"].get(f"/api/assets/{evil}")
    assert r.status_code in (400, 404), r.status_code
    assert b"root:" not in r.content


@pytest.mark.parametrize("bad_id", [
    "short", "NOTHEX" * 5, "../abc", "abc def",
    "0123456789abcdef0123456789abcdeg",          # non-hex char
    "0123456789abcdef0123456789abcde",           # 31 chars
])
def test_non_opaque_identifiers_are_refused(media_env, bad_id):
    assert media_env["client"].get(f"/api/assets/{bad_id}.jpg").status_code in (400, 404)


# ── only real images, whatever the metadata claims ───────────────────────────
def test_bytes_that_are_not_the_declared_image_type_are_refused(media_env):
    """A file swapped on disk (or an SVG/HTML payload) must not be served from
    our origin just because the sidecar claims image/jpeg."""
    aid = _publish(media_env["stock"], data=b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    assert media_env["client"].get(f"/api/assets/{aid}.jpg").status_code == 404


def test_extension_must_match_the_recorded_content_type(media_env):
    aid = _publish(media_env["stock"], data=PNG, ext=".png", content_type="image/jpeg")
    assert media_env["client"].get(f"/api/assets/{aid}.png").status_code == 404


@pytest.mark.parametrize("ext", [".svg", ".html", ".js", ".json", ".txt", ".gif"])
def test_non_image_extensions_are_never_served(media_env, ext):
    aid = uuid.uuid4().hex
    (media_env["stock"] / f"{aid}{ext}").write_bytes(b"<script>alert(1)</script>")
    (media_env["stock"] / f"{aid}.json").write_text(json.dumps({
        "provenance_state": "provider_declared",
        "public_url": f"/api/assets/{aid}{ext}", "content_type": "image/jpeg"}),
        encoding="utf-8")
    assert media_env["client"].get(f"/api/assets/{aid}{ext}").status_code == 404


def test_missing_asset_is_a_plain_404_without_filesystem_detail(media_env):
    r = media_env["client"].get(f"/api/assets/{uuid.uuid4().hex}.jpg")
    assert r.status_code == 404
    body = r.text.lower()
    # no path, drive letter or directory structure leaks to the caller
    assert "stock" not in body and "media_cache" not in body
    assert "/" not in r.json().get("detail", "") and "\\" not in r.json().get("detail", "")


# ── publish() is the only thing that grants reachability ─────────────────────
def test_publish_assigns_a_same_origin_url_and_refuses_bad_input(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_CACHE_DIR", str(tmp_path))
    import media_sourcing as ms
    importlib.reload(ms)

    cand = ms.MediaCandidate(provider="openverse", provider_asset_id="x1",
                             url="https://images.example.org/a.jpg",
                             license_code="cc0", source_url="https://openverse.org/i/1",
                             width=1600, height=900)
    asset = ms.store(cand, JPEG, "image/jpeg", query="gym", store_dir=tmp_path / "stock")
    assert asset.publishable() is False              # stored, not published

    published = ms.publish(asset)
    assert published is not None
    assert published.public_url.startswith("/api/assets/")   # same origin, no host
    assert "http://" not in published.public_url and "https://" not in published.public_url
    assert published.publishable() is True

    # a review-flagged asset is never granted a URL
    flagged = ms.store(cand, JPEG, "image/jpeg", store_dir=tmp_path / "stock")
    flagged.provenance_state = ms.REQUIRES_REVIEW
    assert ms.publish(flagged) is None

    # neither is one whose bytes no longer match the declared type
    swapped = ms.store(cand, JPEG, "image/jpeg", store_dir=tmp_path / "stock")
    open(swapped.path, "wb").write(b"<svg/>")
    assert ms.publish(swapped) is None
