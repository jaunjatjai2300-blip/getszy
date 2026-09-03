"""Provider-agnostic sourcing of REAL, openly-licensed photography.

WHY
    The builder's only visual asset was a decorative SVG carrying a large emoji
    glyph. On a premium request that reads as clip-art, not design. A real-world
    premium site needs real photography -- but only imagery whose provenance we
    can show, and whose licence we can defend.

CONTRACT (the pipeline every provider goes through)
    search()            ask a provider for candidates
    validate_license()  classify licence compatibility -- never rubber-stamp it
    select()            pick the best acceptable candidate for the art direction
    download()          fetch server-side under strict transport/content limits
    store()             persist bytes with full provenance beside them
    attribute()         render the credit the licence requires

PROVENANCE IS A CLAIM, NOT A VERDICT
    A licence field returned by an aggregator is the PROVIDER'S DECLARATION. It
    is not independent legal verification: aggregators index upstream sources
    that can be mislabelled, and an upstream record can change after indexing.
    So nothing here is ever marked "verified" automatically. Every asset carries
    a review state:

        PROVIDER_DECLARED -- provider asserts a compatible licence (default)
        REQUIRES_REVIEW   -- compatible but incomplete/ambiguous metadata
        REJECTED          -- provably incompatible, refused outright
        VERIFIED          -- a human/records check confirmed it (set externally)

    Automatic acceptance may only ever reach PROVIDER_DECLARED. Promotion to
    VERIFIED is a deliberate act recorded elsewhere, never a side effect of a
    successful HTTP call.

DELIBERATE LIMITS
    * NO provider credential ever reaches a customer page; providers are called
      server-side only and keys stay in the environment.
    * NO customer account required -- the default provider (Openverse) needs no
      key, so sourcing works out of the box.
    * "Free" is never assumed to mean "unrestricted": only licences permitting
      COMMERCIAL use and MODIFICATION (we crop/scale to fit) are acceptable.
    * NO runtime hotlink and NO public delivery yet. Bytes are stored locally
      behind a storage abstraction; attaching a secure public delivery layer
      later must not require changing the builder.
    * MEDIA IS OPTIONAL. Every failure path returns None so website generation
      continues with a direction-aware non-photographic composition.

Reliability/limits stay with the existing production layers (task_limits,
failure_isolation, resource_admission). This module owns no retry loop.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import socket
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── provenance / review states ───────────────────────────────────────────────
PROVIDER_DECLARED = "provider_declared"
REQUIRES_REVIEW = "requires_review"
REJECTED = "rejected"
VERIFIED = "verified"          # only ever set by an explicit external review

# ── licence policy ───────────────────────────────────────────────────────────
COMMERCIAL_SAFE = {"cc0", "pdm", "by", "by-sa"}
REFUSED_LICENCES = {
    "by-nc": "NonCommercial: a customer website is a commercial use.",
    "by-nc-sa": "NonCommercial: a customer website is a commercial use.",
    "by-nc-nd": "NonCommercial + NoDerivatives.",
    "by-nd": "NoDerivatives: layout requires cropping/scaling.",
    "nc-sampling+": "NonCommercial sampling licence.",
    "sampling+": "Sampling licence does not cover general site imagery.",
}
ATTRIBUTION_REQUIRED = {"by", "by-sa"}

MAX_IMAGE_BYTES = int(os.environ.get("MEDIA_MAX_IMAGE_BYTES", 8 * 1024 * 1024))
MIN_IMAGE_BYTES = 1024
HTTP_TIMEOUT = float(os.environ.get("MEDIA_HTTP_TIMEOUT", 12))
MAX_REDIRECTS = 3
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")

# Magic bytes -> extension. Content-Type alone is attacker/provider controlled,
# so the actual bytes must also look like the image type they claim to be.
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
)


def _sniff(data: bytes):
    """(mime, ext) from magic bytes, or (None, None) if not a supported image."""
    for sig, mime, ext in _MAGIC:
        if data.startswith(sig):
            return mime, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None, None


_STORE_DIR = Path(os.environ.get("MEDIA_CACHE_DIR",
                                str(Path(__file__).resolve().parent / "media_cache"))) / "stock"


class MediaUnavailable(Exception):
    """No legally usable image could be sourced. Callers degrade, never fake."""


@dataclass
class MediaCandidate:
    """One provider result, before licence classification."""
    provider: str
    provider_asset_id: str
    url: str                 # direct bytes
    title: str = ""
    creator: str = ""
    creator_url: str = ""
    source_url: str = ""     # upstream landing page, for attribution + audit
    license_code: str = ""
    license_version: str = ""
    license_url: str = ""
    width: int = 0
    height: int = 0
    retrieved_at: float = field(default_factory=time.time)
    raw: dict = field(default_factory=dict)   # original provider metadata

    def orientation(self) -> str:
        if not self.width or not self.height:
            return "unknown"
        if self.width >= self.height * 1.15:
            return "landscape"
        if self.height >= self.width * 1.15:
            return "portrait"
        return "square"


@dataclass
class MediaAsset:
    """A stored image plus the provenance record that justifies publishing it."""
    asset_id: str
    path: str
    provider: str
    provider_asset_id: str
    license_code: str
    license_url: str = ""
    license_version: str = ""
    creator: str = ""
    creator_url: str = ""
    source_url: str = ""
    title: str = ""
    width: int = 0
    height: int = 0
    bytes: int = 0
    content_sha256: str = ""
    content_type: str = ""
    attribution_required: bool = False
    provenance_state: str = PROVIDER_DECLARED
    provenance_reason: str = ""
    query: str = ""
    retrieved_at: float = 0.0
    stored_at: float = field(default_factory=time.time)
    raw_metadata: dict = field(default_factory=dict)
    # Set by a future secure delivery layer; the builder only ever reads this.
    public_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def publishable(self) -> bool:
        """Bytes on disk are not permission to publish. A page may only use an
        asset that is licence-acceptable AND has a delivery URL."""
        return bool(self.public_url) and self.provenance_state in (PROVIDER_DECLARED, VERIFIED)


# ── SSRF-safe URL checks ─────────────────────────────────────────────────────
def _is_public_host(host: str) -> bool:
    """Refuse private/loopback/link-local/reserved targets."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True


def _safe_url(url: str, allowed_hosts: tuple = ()) -> bool:
    """HTTPS only, resolvable to a public address, optional host allowlist."""
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme != "https" or not u.hostname:
        return False
    if allowed_hosts and not any(
        u.hostname == h or u.hostname.endswith("." + h) for h in allowed_hosts
    ):
        return False
    return _is_public_host(u.hostname)


# ── providers ────────────────────────────────────────────────────────────────
class MediaProvider:
    """Interface every source implements. Adding Pexels/Unsplash later means
    adding a class here -- the builder never changes."""
    name = "base"
    requires_credentials = False
    api_hosts: tuple = ()        # allowlist for the SEARCH endpoint

    def available(self) -> bool:
        return True

    async def search(self, query: str, *, count: int = 12,
                     orientation: str = "landscape") -> list:
        raise NotImplementedError


class OpenverseProvider(MediaProvider):
    """Openverse (WordPress Foundation) aggregates openly-licensed media.

    Default because it needs no API key and no customer account, and returns
    explicit per-result licence metadata. That metadata is a DECLARATION which
    validate_license classifies -- it is never treated as legal verification.
    """
    name = "openverse"
    requires_credentials = False
    api_hosts = ("openverse.org",)
    API = "https://api.openverse.org/v1/images/"

    async def search(self, query: str, *, count: int = 12,
                     orientation: str = "landscape") -> list:
        import httpx
        if not _safe_url(self.API, allowed_hosts=self.api_hosts):
            return []
        params = {
            "q": query,
            "page_size": max(1, min(count, 20)),
            "license_type": "commercial,modification",   # server-side pre-filter
            "mature": "false",
        }
        headers = {"User-Agent": "Getszy/1.0 (+https://getszy.com)"}
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False) as c:
                r = await c.get(self.API, params=params, headers=headers)
                if r.status_code != 200:
                    logger.info("openverse search %s -> %s", query, r.status_code)
                    return []
                data = r.json()
        except Exception as e:
            logger.info("openverse search failed: %s", type(e).__name__)
            return []

        out = []
        for it in (data.get("results") or []):
            url = it.get("url") or ""
            if not url:
                continue
            out.append(MediaCandidate(
                provider=self.name,
                provider_asset_id=str(it.get("id") or ""),
                url=url,
                title=(it.get("title") or "")[:200],
                creator=(it.get("creator") or "")[:120],
                creator_url=it.get("creator_url") or "",
                source_url=it.get("foreign_landing_url") or "",
                license_code=(it.get("license") or "").lower(),
                license_version=str(it.get("license_version") or ""),
                license_url=it.get("license_url") or "",
                width=int(it.get("width") or 0),
                height=int(it.get("height") or 0),
                raw={k: it.get(k) for k in
                     ("id", "license", "license_version", "license_url", "source",
                      "provider", "foreign_landing_url", "creator", "creator_url",
                      "title", "width", "height", "filetype", "attribution")
                     if k in it},
            ))
        return out


_PROVIDERS: list = [OpenverseProvider()]


def register_provider(provider: MediaProvider) -> None:
    """Add a source (Pexels/Unsplash/internal library) without touching the
    builder. Providers are tried in registration order."""
    _PROVIDERS.insert(0, provider)


def providers() -> list:
    return [p for p in _PROVIDERS if p.available()]


# ── licence classification ───────────────────────────────────────────────────
def validate_license(candidate: MediaCandidate) -> tuple:
    """(state, reason) -- classification, never legal verification.

    Automatic acceptance tops out at PROVIDER_DECLARED. Missing or unknown
    licence data is REJECTED rather than assumed permissive; compatible but
    incomplete metadata is flagged REQUIRES_REVIEW so it is auditable instead
    of silently published.
    """
    code = (candidate.license_code or "").strip().lower()
    if not code:
        return REJECTED, "No licence metadata supplied by the provider."
    if code in REFUSED_LICENCES:
        return REJECTED, REFUSED_LICENCES[code]
    if code not in COMMERCIAL_SAFE:
        return REJECTED, f"Licence '{code}' is not on the commercial-safe allowlist."

    gaps = []
    if code in ATTRIBUTION_REQUIRED:
        if not candidate.creator:
            gaps.append("attribution licence with no creator named")
        if not candidate.license_url:
            gaps.append("attribution licence with no licence URL to cite")
    if not candidate.source_url:
        gaps.append("no upstream landing page for audit")
    if gaps:
        return REQUIRES_REVIEW, (
            f"Provider declares '{code}' (compatible) but metadata is incomplete: "
            + "; ".join(gaps) + "."
        )
    return PROVIDER_DECLARED, (
        f"Provider declares '{code}', which permits commercial use and modification. "
        "Provider declaration only -- not independently verified."
    )


def is_acceptable(state: str) -> bool:
    """States automatic selection may use. REQUIRES_REVIEW is deliberately not
    auto-usable: it is recorded for a human, not shipped to a customer."""
    return state in (PROVIDER_DECLARED, VERIFIED)


def select(candidates: list, *, orientation: str = "landscape",
           min_width: int = 1200) -> "MediaCandidate | None":
    """Best acceptable candidate for this art direction, or None."""
    cleared = []
    for c in candidates or []:
        state, _ = validate_license(c)
        if not is_acceptable(state):
            continue
        if c.width and c.width < min_width:
            continue
        cleared.append(c)
    if not cleared:
        return None

    def rank(c: MediaCandidate):
        return (
            0 if c.license_code in ("cc0", "pdm") else 1,       # simplest licence
            0 if c.orientation() == orientation else 1,          # right shape
            -(c.width * c.height),                               # then resolution
        )
    return sorted(cleared, key=rank)[0]


async def download(candidate: MediaCandidate, *, provider: MediaProvider | None = None) -> tuple:
    """(bytes, mime) fetched under strict transport and content limits.

    Redirects are followed MANUALLY so every hop is re-validated -- an initial
    HTTPS public URL must not be able to bounce us to http:// or to an internal
    address.
    """
    import httpx
    url = candidate.url
    if not _safe_url(url):
        raise MediaUnavailable(f"Unsafe or non-public image URL: {url[:80]}")

    headers = {"User-Agent": "Getszy/1.0 (+https://getszy.com)"}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False) as c:
        for _hop in range(MAX_REDIRECTS + 1):
            r = await c.get(url, headers=headers)
            if r.status_code in (301, 302, 303, 307, 308):
                nxt = r.headers.get("location") or ""
                if not nxt:
                    raise MediaUnavailable("Redirect without a location header")
                if nxt.startswith("/"):
                    u = urlparse(url)
                    nxt = f"https://{u.hostname}{nxt}"
                if not _safe_url(nxt):          # re-validated at EVERY hop
                    raise MediaUnavailable(f"Unsafe redirect target: {nxt[:80]}")
                url = nxt
                continue
            break
        else:
            raise MediaUnavailable("Too many redirects")

        if r.status_code != 200:
            raise MediaUnavailable(f"Image fetch returned {r.status_code}")
        ctype = (r.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ctype not in ALLOWED_CONTENT_TYPES:
            raise MediaUnavailable(f"Refused content-type {ctype!r}")
        data = r.content
        if not data or len(data) < MIN_IMAGE_BYTES:
            raise MediaUnavailable("Image body missing or implausibly small")
        if len(data) > MAX_IMAGE_BYTES:
            raise MediaUnavailable(f"Image exceeds {MAX_IMAGE_BYTES} bytes")

        sniffed, _ext = _sniff(data)
        if sniffed is None:
            raise MediaUnavailable("Bytes are not a supported image (magic-byte check failed)")
        if sniffed != ctype:
            raise MediaUnavailable(
                f"Content-Type {ctype!r} disagrees with actual bytes {sniffed!r}")
        return data, sniffed


def store(candidate: MediaCandidate, data: bytes, mime: str = "", *, query: str = "",
          store_dir: "Path | None" = None) -> MediaAsset:
    """Persist bytes plus a provenance sidecar.

    Filenames are generated (uuid4 hex + sniffed extension) and never derived
    from provider-supplied text, so no provider string can influence the path.
    Provenance travels WITH the file so an audit never needs a database.
    """
    d = Path(store_dir) if store_dir else _STORE_DIR
    d.mkdir(parents=True, exist_ok=True)

    sniffed, ext = _sniff(data)
    if sniffed is None:
        raise MediaUnavailable("Refusing to store bytes that are not a supported image")
    mime = mime or sniffed

    state, reason = validate_license(candidate)
    asset_id = uuid.uuid4().hex                      # sanitised by construction
    path = d / f"{asset_id}{ext}"
    path.write_bytes(data)

    asset = MediaAsset(
        asset_id=asset_id, path=str(path), provider=candidate.provider,
        provider_asset_id=candidate.provider_asset_id,
        license_code=candidate.license_code, license_url=candidate.license_url,
        license_version=candidate.license_version,
        creator=candidate.creator, creator_url=candidate.creator_url,
        source_url=candidate.source_url, title=candidate.title,
        width=candidate.width, height=candidate.height, bytes=len(data),
        content_sha256=hashlib.sha256(data).hexdigest(),
        content_type=mime,
        attribution_required=candidate.license_code in ATTRIBUTION_REQUIRED,
        provenance_state=state, provenance_reason=reason,
        query=query, retrieved_at=candidate.retrieved_at,
        raw_metadata=dict(candidate.raw or {}),
    )
    (d / f"{asset_id}.json").write_text(
        json.dumps(asset.to_dict(), indent=2, default=str), encoding="utf-8")
    return asset


def attribute(asset: MediaAsset) -> str:
    """The credit the licence requires, as escaped HTML ('' when none required)."""
    if not asset.attribution_required:
        return ""

    def esc(v: str) -> str:
        return (str(v or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    who = esc(asset.creator) or "Unknown creator"
    if asset.source_url:
        who_html = f'<a href="{esc(asset.source_url)}" rel="nofollow noopener">{who}</a>'
    else:
        who_html = who
    lic = esc(asset.license_code.upper())
    lic_html = (f'<a href="{esc(asset.license_url)}" rel="nofollow noopener license">CC {lic}</a>'
                if asset.license_url else f"CC {lic}")
    return f'<span class="credit">Photo by {who_html} · {lic_html}</span>'


async def source_image(query: str, *, orientation: str = "landscape",
                       min_width: int = 1200, store_dir: "Path | None" = None):
    """Full pipeline for one image. Returns a MediaAsset or None.

    None is a normal, expected outcome (no network, rate limit, nothing licence
    clean). Website generation MUST continue: the caller renders a designed,
    direction-aware non-photographic composition -- never a cartoon or emoji.
    """
    for provider in providers():
        try:
            candidates = await provider.search(query, orientation=orientation)
        except Exception as e:
            logger.info("provider %s search failed: %s", provider.name, type(e).__name__)
            continue
        chosen = select(candidates, orientation=orientation, min_width=min_width)
        if not chosen:
            continue
        try:
            data, mime = await download(chosen, provider=provider)
            return store(chosen, data, mime, query=query, store_dir=store_dir)
        except MediaUnavailable as e:
            logger.info("candidate rejected: %s", e)
            continue
        except Exception as e:
            logger.info("download failed: %s", type(e).__name__)
            continue
    return None


async def search_providers(query: str, *, orientation: str = "landscape") -> list:
    """Every provider's candidates whose licence state is auto-acceptable."""
    out = []
    for provider in providers():
        try:
            for c in await provider.search(query, orientation=orientation):
                if is_acceptable(validate_license(c)[0]):
                    out.append(c)
        except Exception:
            continue
    return out


__all__ = [
    "MediaProvider", "OpenverseProvider", "MediaCandidate", "MediaAsset",
    "MediaUnavailable", "register_provider", "providers", "search_providers",
    "validate_license", "is_acceptable", "select", "download", "store",
    "attribute", "source_image", "COMMERCIAL_SAFE", "REFUSED_LICENCES",
    "PROVIDER_DECLARED", "REQUIRES_REVIEW", "REJECTED", "VERIFIED",
]
