"""Curated, license-vetted ART DIRECTION registry for the customer builder.

WHY THIS EXISTS
    Before this module the builder had exactly ONE visual system: a single
    hardcoded CSS string with colour substitution. Every customer -- a luxury
    gym, a glass-styled salon, an AI SaaS -- received the same layout, the same
    type pairing and the same motion. Business VERTICAL changed the copy;
    nothing changed the DESIGN. That is why output read as "one template".

    A recipe here is a complete visual system: palette roles, type pairing,
    spacing/rhythm, surface treatment, motion budget and asset policy. Selecting
    a recipe changes how the page LOOKS, not merely what it says.

PROVENANCE / LICENSING (audited before inclusion, per the capability rules)
    * All CSS in this module is ORIGINAL WORK authored for Getszy. No third-party
      stylesheet, component library or snippet is copied or vendored, so there is
      no upstream licence to inherit, attribute or track.
    * The *techniques* used (backdrop-filter glassmorphism, CSS grid editorial
      layouts, gradient meshes, scroll-driven reveals) are open web-platform
      features documented by MDN/W3C -- specifications, not licensed code.
    * ZERO runtime dependencies: no CDN script, no external stylesheet, no build
      step, no npm package. Everything ships inline in the generated page, which
      is what keeps the self-contained guarantee in builder_quality intact.
    * Typefaces are referenced by family name with a full system fallback stack,
      so a page renders correctly even when no webfont loads.

    A new recipe MUST satisfy the same bar before being added: original or
    permissively-licensed, no runtime dependency, no unvetted third-party code,
    and it must pass the out-of-band render gate (tools/design_render_check.py).

The deterministic premium template remains the SAFETY FLOOR: recipes change the
art direction, they never remove the floor, the quality gate or Policy A.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# ── shared foundation ────────────────────────────────────────────────────────
# One reset/rhythm base every direction builds on. Recipes differ in visual
# language, not in resetting the box model five times -- that would be the
# duplication this registry exists to avoid.
_BASE = (
    "*{box-sizing:border-box;margin:0;padding:0}"
    "html{scroll-behavior:smooth}"
    "img{max-width:100%;display:block}svg{display:block}"
    "a{color:inherit}p{max-width:66ch}"
    ".wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}"
    ".narrow{max-width:760px}.muted{opacity:.74}"
    ".cluster{display:flex;gap:14px;flex-wrap:wrap;align-items:center}"
    "@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}"
    # components the direction plans compose with. Kept in the shared base so
    # each recipe overrides look, not layout plumbing.
    ".shotwrap{margin:0;position:relative}"
    ".shotwrap .shot{width:100%;height:100%;object-fit:cover}"
    ".credit{position:absolute;left:0;bottom:0;font-size:11px;padding:6px 10px;background:rgba(0,0,0,.55);color:#fff;opacity:.9}"
    ".credit a{color:#fff;text-decoration:underline}"
    ".gstrip{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:28px}"
    ".gtile .panel{aspect-ratio:3/4}"
    ".lgrid{display:grid;grid-template-columns:1.25fr .75fr;gap:clamp(20px,4vw,54px);align-items:start}"
    ".ltile:nth-child(2){margin-top:clamp(28px,7vw,96px)}"
    ".indexlist{list-style:none;margin-top:28px;display:grid;gap:0}"
    ".idx{display:grid;grid-template-columns:64px 1fr;gap:18px;padding:22px 0;border-top:1px solid currentColor;border-color:color-mix(in srgb,currentColor 16%,transparent)}"
    ".idx .num{font-size:14px;opacity:.5;letter-spacing:.12em}"
    ".idxt strong{display:block;font-size:19px;margin-bottom:5px}"
    ".idxt em{font-style:normal;font-size:15px}"
    ".manifesto{max-width:20ch}"
    ".specs .scard{display:grid;gap:6px}"
    ".reveal{opacity:1}"
    # Scroll-driven reveal. The from-state deliberately keeps content LEGIBLE
    # (opacity .35, not 0): a section that never enters its animation range --
    # print, full-page capture, landing mid-page via an anchor -- must still be
    # readable. Stranding customer content at opacity 0 is not an acceptable
    # failure mode for a deliverable website.
    "@supports (animation-timeline:view()){"
    "@keyframes reveal-in{from{opacity:.35;transform:translateY(18px)}to{opacity:1;transform:none}}"
    ".reveal{animation:reveal-in linear both;animation-timeline:view();animation-range:entry 0% entry 60%}}"
    "@media(max-width:860px){.gstrip{grid-template-columns:1fr 1fr}.lgrid{grid-template-columns:1fr}.ltile:nth-child(2){margin-top:0}}"
)

# Focus styling is an accessibility requirement, never a per-recipe choice.
_A11Y = (
    "a:focus-visible,button:focus-visible,summary:focus-visible{"
    "outline:3px solid var(--a);outline-offset:3px;border-radius:6px}"
)


@dataclass(frozen=True)
class DesignRecipe:
    """One complete, vetted visual system."""
    id: str
    label: str
    # Deterministic intent signals. Matched against the customer prompt.
    signals: tuple
    # Verticals this direction suits well (soft preference, never a hard gate).
    affinity: tuple
    palette: dict          # p=primary a=accent bg=page tx=text sf=surface
    display_font: str      # heading family (with fallbacks applied downstream)
    body_font: str
    motion: str            # 'none' | 'subtle' | 'expressive'
    asset_policy: str      # 'photo' | 'svg' | 'gradient'
    density: str           # 'airy' | 'balanced' | 'dense'
    css: Callable[[dict], str] = field(repr=False, default=None)
    notes: str = ""

    # ── structural art direction (a recipe must control more than colour) ──
    # Ordered section plan. Different directions tell a different STORY in a
    # different ORDER with different components -- this is what makes two
    # directions structurally different rather than palette-swapped.
    composition: tuple = ()
    # Interaction/motion vocabulary this direction is allowed to use.
    motion_rules: dict = field(default_factory=dict)
    # Surface language: borders, elevation, blur, corner treatment.
    surface_rules: dict = field(default_factory=dict)
    # Detailed, art-direction-aware asset policy (see ASSET_* contract below).
    assets: dict = field(default_factory=dict)

    # ── governance metadata (required for every recipe) ──
    provenance: dict = field(default_factory=dict)
    license: str = ""
    security_review: str = ""
    render_verification: dict = field(default_factory=dict)

    def requires_photography(self) -> bool:
        """True when this direction is not honestly deliverable without real
        imagery. Used by the quality gate to reject emoji/blob stand-ins."""
        return self.assets.get("photography") == "required"

    def forbids_illustration_hero(self) -> bool:
        return self.assets.get("illustration_hero") == "forbidden"

    def fonts_query(self) -> str:
        """Google Fonts css2 query for this pairing. Families are requested by
        name only; every rule that uses them also names a system fallback, so a
        blocked/absent webfont degrades gracefully instead of breaking layout."""
        fams = []
        for fam, weights in ((self.display_font, "600;700;800;900"),
                             (self.body_font, "400;500;600")):
            if fam and fam not in [f.split(":")[0] for f in fams]:
                fams.append(f"{fam.replace(' ', '+')}:wght@{weights}")
        return "&".join(f"family={f}" for f in fams)


def _vars(r: "DesignRecipe") -> str:
    p = r.palette
    return (
        f":root{{--p:{p['p']};--a:{p['a']};--bg:{p['bg']};--tx:{p['tx']};--sf:{p['sf']};"
        f"--maxw:{p.get('maxw', '1140px')};--r:{p.get('r', '20px')};"
        f"--display:'{r.display_font}',{p.get('dfallback', 'system-ui,sans-serif')};"
        f"--body:'{r.body_font}',{p.get('bfallback', 'system-ui,sans-serif')}}}"
    )


# ── 1. CINEMATIC LUXURY ──────────────────────────────────────────────────────
# Dark theatrical ground, huge condensed display type, wide letterspaced
# eyebrows, photography carries the page. Reads like a premium brand film.
def _css_cinematic(t: dict) -> str:
    return (
        "body{font-family:var(--body);color:var(--tx);background:var(--bg);line-height:1.6;"
        "-webkit-font-smoothing:antialiased}"
        "h1{font-family:var(--display);font-weight:900;letter-spacing:-.035em;line-height:.95;"
        "font-size:clamp(44px,8vw,104px);text-transform:uppercase}"
        "h2{font-family:var(--display);font-weight:800;letter-spacing:-.02em;line-height:1.05;"
        "font-size:clamp(30px,4.6vw,54px);margin-bottom:16px}"
        "h3{font-family:var(--display);font-weight:700;font-size:20px;margin-bottom:8px}"
        ".eyebrow{display:inline-block;text-transform:uppercase;letter-spacing:.34em;font-size:11px;"
        "font-weight:700;color:var(--a);margin-bottom:18px}"
        ".section{padding:clamp(72px,11vw,150px) 0;position:relative}"
        ".section.tint{background:var(--sf)}"
        # full-bleed cinematic hero: image + heavy scrim so type always reads
        ".hero{position:relative;min-height:min(92vh,860px);display:flex;align-items:flex-end;"
        "overflow:hidden;background:var(--sf)}"
        ".hero .shot{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(.85) contrast(1.08)}"
        # the hero visual is the backdrop; copy sits above it
        ".hero .panel{position:absolute;inset:0;z-index:0;aspect-ratio:auto;border:0;opacity:.6}"
        ".hero .panel svg{width:100%;height:100%}"
        ".hero .herogrid{display:block}"
        ".hero::after{content:'';position:absolute;inset:0;background:"
        "linear-gradient(180deg,rgba(8,8,10,.30) 0%,rgba(8,8,10,.72) 62%,rgba(8,8,10,.94) 100%)}"
        ".herogrid{position:relative;z-index:2;padding:0 0 clamp(48px,8vw,96px);max-width:900px}"
        ".hero .sub{font-size:clamp(17px,2vw,21px);margin:20px 0 32px;opacity:.9;max-width:60ch}"
        ".btn{display:inline-flex;align-items:center;gap:10px;background:var(--a);color:#0b0b0d;"
        "padding:17px 40px;border-radius:2px;font-weight:800;letter-spacing:.1em;font-size:13px;"
        "text-transform:uppercase;text-decoration:none;transition:transform .35s cubic-bezier(.2,.8,.2,1),filter .35s}"
        ".btn:hover{transform:translateY(-3px);filter:brightness(1.12)}"
        ".btn.ghost{background:transparent;color:var(--tx);border:1px solid rgba(255,255,255,.34)}"
        ".btn.ghost:hover{background:rgba(255,255,255,.08)}"
        ".nav{position:sticky;top:0;z-index:50;background:rgba(10,10,12,.72);"
        "backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,.09)}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:76px}"
        ".nav .brand{font-family:var(--display);font-weight:800;font-size:19px;letter-spacing:.16em;"
        "text-transform:uppercase;text-decoration:none;color:var(--tx)}"
        ".nav .links{display:flex;gap:34px}.nav .links a{text-decoration:none;font-size:12px;"
        "letter-spacing:.16em;text-transform:uppercase;font-weight:600;opacity:.72}"
        ".nav .links a:hover{opacity:1;color:var(--a)}"
        # editorial split rows, image bleeding to the page edge
        ".featrow{display:grid;grid-template-columns:1fr 1fr;gap:clamp(32px,6vw,88px);align-items:center}"
        ".featrow.flip .rowtext{order:2}"
        ".panel{position:relative;aspect-ratio:4/5;overflow:hidden;background:var(--sf);"
        "border:1px solid rgba(255,255,255,.10)}"
        ".panel img{width:100%;height:100%;object-fit:cover;transition:transform 1.1s cubic-bezier(.2,.8,.2,1)}"
        ".featrow:hover .panel img{transform:scale(1.05)}"
        ".ticks{list-style:none;margin-top:24px;display:grid;gap:14px}"
        ".ticks li{position:relative;padding-left:34px;opacity:.86}"
        ".ticks li::before{content:'';position:absolute;left:0;top:9px;width:20px;height:1px;background:var(--a)}"
        ".grid3{display:grid;gap:1px;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));"
        "margin-top:44px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.10)}"
        ".scard{background:var(--bg);padding:38px 30px;transition:background .4s}"
        ".scard:hover{background:var(--sf)}"
        ".scard .dot{display:block;width:34px;height:2px;background:var(--a);margin-bottom:22px}"
        ".steps{display:grid;gap:36px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-top:44px}"
        ".step .num{font-family:var(--display);font-weight:900;font-size:60px;color:var(--a);"
        "opacity:.30;display:block;line-height:1;margin-bottom:10px}"
        ".stats{display:flex;flex-wrap:wrap;gap:1px;margin-top:36px;background:rgba(255,255,255,.10)}"
        ".stat{flex:1 1 200px;background:var(--bg);padding:32px}"
        ".faq{border-bottom:1px solid rgba(255,255,255,.12)}"
        ".faq summary{cursor:pointer;list-style:none;font-family:var(--display);font-weight:700;"
        "font-size:19px;padding:24px 0;display:flex;justify-content:space-between;gap:16px}"
        ".faq summary::-webkit-details-marker{display:none}"
        ".faq summary::after{content:'+';color:var(--a);font-size:26px;line-height:1}"
        ".faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 24px;opacity:.8}"
        ".ctaband{position:relative;padding:clamp(64px,10vw,124px) 24px;text-align:center;"
        "background:linear-gradient(135deg,var(--p),var(--a));color:#0b0b0d;overflow:hidden}"
        ".ctaband h2{color:#0b0b0d}.ctaband p{margin:0 auto 30px;color:rgba(11,11,13,.82)}"
        ".ctaband .btn{background:#0b0b0d;color:var(--a)}"
        ".foot{border-top:1px solid rgba(255,255,255,.10);padding:64px 0 32px}"
        ".footgrid{display:grid;grid-template-columns:1.6fr 1fr 1fr;gap:36px}"
        ".foot .brand{font-family:var(--display);font-weight:800;letter-spacing:.16em;"
        "text-transform:uppercase;font-size:18px}"
        ".foot nav{display:grid;gap:11px}.foot nav a{text-decoration:none;opacity:.66;font-size:14px}"
        ".foot .base{margin-top:34px;padding-top:20px;border-top:1px solid rgba(255,255,255,.08);"
        "display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:12px;opacity:.6}"
        "@media(max-width:860px){.featrow{grid-template-columns:1fr}.featrow.flip .rowtext{order:0}"
        ".nav .links{display:none}.panel{aspect-ratio:16/11}.footgrid{grid-template-columns:1fr}}"
    )


# ── 2. GLASSMORPHISM ─────────────────────────────────────────────────────────
# Luminous pastel ground, layered translucent panels, soft depth. Every surface
# is frosted glass over a colour field.
def _css_glass(t: dict) -> str:
    return (
        "body{font-family:var(--body);color:var(--tx);line-height:1.68;-webkit-font-smoothing:antialiased;"
        "background:var(--bg);position:relative;overflow-x:hidden}"
        # ambient colour field the glass refracts
        "body::before{content:'';position:fixed;inset:-20%;z-index:-1;pointer-events:none;background:"
        "radial-gradient(680px 520px at 12% 8%,var(--p)3d,transparent 62%),"
        "radial-gradient(760px 560px at 88% 22%,var(--a)3d,transparent 62%),"
        "radial-gradient(700px 620px at 46% 92%,var(--p)2b,transparent 64%)}"
        "h1{font-family:var(--display);font-weight:800;letter-spacing:-.032em;line-height:1.04;"
        "font-size:clamp(40px,6.6vw,74px)}"
        "h2{font-family:var(--display);font-weight:800;letter-spacing:-.02em;"
        "font-size:clamp(27px,3.8vw,43px);margin-bottom:14px}"
        "h3{font-family:var(--display);font-weight:700;font-size:19px;margin-bottom:8px}"
        ".eyebrow{display:inline-block;padding:7px 16px;border-radius:999px;font-size:12px;font-weight:700;"
        "letter-spacing:.14em;text-transform:uppercase;color:var(--p);margin-bottom:16px;"
        "background:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.75);"
        "backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}"
        ".section{padding:clamp(60px,9vw,116px) 0}"
        ".section.tint{background:rgba(255,255,255,.36);backdrop-filter:blur(22px);"
        "-webkit-backdrop-filter:blur(22px);border-top:1px solid rgba(255,255,255,.6);"
        "border-bottom:1px solid rgba(255,255,255,.6)}"
        ".hero{padding:clamp(56px,9vw,110px) 0}"
        ".herogrid{display:grid;grid-template-columns:1.05fr .95fr;gap:52px;align-items:center}"
        ".hero .sub{font-size:clamp(17px,2vw,20px);margin:20px 0 32px;opacity:.82}"
        # the glass primitive, reused by every surface
        ".glass,.scard,.stat,.panel,.step{background:rgba(255,255,255,.52);"
        "border:1px solid rgba(255,255,255,.78);border-radius:var(--r);"
        "backdrop-filter:blur(20px) saturate(165%);-webkit-backdrop-filter:blur(20px) saturate(165%);"
        "box-shadow:0 18px 44px -22px rgba(31,38,135,.34),inset 0 1px 0 rgba(255,255,255,.85)}"
        ".btn{display:inline-flex;align-items:center;gap:9px;padding:15px 32px;border-radius:999px;"
        "font-weight:700;text-decoration:none;color:#fff;background:linear-gradient(135deg,var(--p),var(--a));"
        "box-shadow:0 12px 30px -10px var(--p)88;transition:transform .3s cubic-bezier(.2,.8,.2,1),box-shadow .3s}"
        ".btn:hover{transform:translateY(-3px);box-shadow:0 20px 40px -12px var(--p)aa}"
        ".btn.ghost{background:rgba(255,255,255,.55);color:var(--p);border:1px solid rgba(255,255,255,.85);"
        "backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);box-shadow:none}"
        ".nav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.55);"
        "backdrop-filter:blur(20px) saturate(165%);-webkit-backdrop-filter:blur(20px) saturate(165%);"
        "border-bottom:1px solid rgba(255,255,255,.7)}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:72px}"
        ".nav .brand{font-family:var(--display);font-weight:800;font-size:20px;color:var(--p);text-decoration:none}"
        ".nav .links{display:flex;gap:28px}.nav .links a{text-decoration:none;font-weight:600;font-size:15px;opacity:.78}"
        ".nav .links a:hover{opacity:1;color:var(--p)}"
        ".panel{overflow:hidden;aspect-ratio:4/3;padding:0}"
        ".panel img{width:100%;height:100%;object-fit:cover}"
        ".featrow{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}"
        ".featrow.flip .rowtext{order:2}"
        ".ticks{list-style:none;margin-top:22px;display:grid;gap:12px}"
        ".ticks li{position:relative;padding-left:32px;opacity:.86}"
        ".ticks li::before{content:'';position:absolute;left:0;top:6px;width:18px;height:18px;border-radius:50%;"
        "background:linear-gradient(135deg,var(--p),var(--a));box-shadow:0 0 0 4px rgba(255,255,255,.6)}"
        ".grid3{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:34px}"
        ".scard{padding:28px;transition:transform .35s cubic-bezier(.2,.8,.2,1),box-shadow .35s}"
        ".scard:hover{transform:translateY(-6px);box-shadow:0 28px 56px -24px rgba(31,38,135,.44)}"
        ".scard .dot{display:block;width:44px;height:44px;border-radius:14px;"
        "background:linear-gradient(135deg,var(--p),var(--a));margin-bottom:16px;"
        "box-shadow:0 8px 18px -6px var(--p)88}"
        ".steps{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:34px}"
        ".step{padding:26px}"
        ".step .num{font-family:var(--display);font-weight:800;font-size:44px;display:block;line-height:1;"
        "background:linear-gradient(135deg,var(--p),var(--a));-webkit-background-clip:text;"
        "background-clip:text;color:transparent;margin-bottom:6px}"
        ".stats{display:flex;flex-wrap:wrap;gap:18px;margin-top:30px}.stat{flex:1 1 200px;padding:26px}"
        ".faq{border-bottom:1px solid rgba(255,255,255,.7)}"
        ".faq summary{cursor:pointer;list-style:none;font-family:var(--display);font-weight:700;font-size:18px;"
        "padding:20px 0;display:flex;justify-content:space-between;gap:16px}"
        ".faq summary::-webkit-details-marker{display:none}"
        ".faq summary::after{content:'+';font-size:26px;color:var(--p);line-height:1}"
        ".faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 20px;opacity:.8}"
        ".ctaband{border-radius:32px;padding:clamp(52px,8vw,92px) 24px;text-align:center;color:#fff;"
        "background:linear-gradient(135deg,var(--p),var(--a));box-shadow:0 30px 70px -30px var(--p)aa}"
        ".ctaband h2{color:#fff}.ctaband p{margin:0 auto 26px;opacity:.92}"
        ".ctaband .btn{background:rgba(255,255,255,.95);color:var(--p);box-shadow:0 14px 30px -12px rgba(0,0,0,.3)}"
        ".foot{border-top:1px solid rgba(255,255,255,.7);padding:52px 0 30px}"
        ".footgrid{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:32px}"
        ".foot .brand{font-family:var(--display);font-weight:800;font-size:20px;color:var(--p)}"
        ".foot nav{display:grid;gap:10px}.foot nav a{text-decoration:none;opacity:.74;font-size:14px}"
        ".foot .base{margin-top:30px;padding-top:18px;border-top:1px solid rgba(255,255,255,.6);"
        "display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:13px;opacity:.7}"
        "@media(max-width:860px){.herogrid,.featrow{grid-template-columns:1fr}"
        ".featrow.flip .rowtext{order:0}.nav .links{display:none}.footgrid{grid-template-columns:1fr 1fr}}"
        "@media(max-width:520px){.footgrid{grid-template-columns:1fr}}"
    )


# ── 3. FUTURISTIC AI / SAAS ──────────────────────────────────────────────────
# Deep space ground, luminous gradient mesh, technical grid, monospace accents.
def _css_futuristic(t: dict) -> str:
    return (
        "body{font-family:var(--body);color:var(--tx);background:var(--bg);line-height:1.65;"
        "-webkit-font-smoothing:antialiased;position:relative;overflow-x:hidden}"
        # engineering grid + aurora, pure CSS, no canvas/WebGL runtime cost
        "body::before{content:'';position:fixed;inset:0;z-index:-2;pointer-events:none;"
        "background-image:linear-gradient(rgba(255,255,255,.038) 1px,transparent 1px),"
        "linear-gradient(90deg,rgba(255,255,255,.038) 1px,transparent 1px);background-size:64px 64px}"
        "body::after{content:'';position:fixed;inset:-30%;z-index:-1;pointer-events:none;opacity:.55;background:"
        "radial-gradient(620px 460px at 18% 4%,var(--p)55,transparent 60%),"
        "radial-gradient(680px 520px at 84% 26%,var(--a)4d,transparent 62%)}"
        "h1{font-family:var(--display);font-weight:800;letter-spacing:-.04em;line-height:1.02;"
        "font-size:clamp(42px,7vw,84px);background:linear-gradient(180deg,var(--tx) 30%,var(--p));"
        "-webkit-background-clip:text;background-clip:text;color:transparent}"
        "h2{font-family:var(--display);font-weight:800;letter-spacing:-.028em;"
        "font-size:clamp(28px,4vw,46px);margin-bottom:14px}"
        "h3{font-family:var(--display);font-weight:700;font-size:19px;margin-bottom:8px}"
        ".eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 14px;border-radius:999px;"
        "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;font-weight:600;"
        "letter-spacing:.12em;text-transform:uppercase;color:var(--a);margin-bottom:18px;"
        "background:var(--a)14;border:1px solid var(--a)33}"
        ".eyebrow::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--a);"
        "box-shadow:0 0 10px var(--a)}"
        ".section{padding:clamp(64px,9vw,124px) 0;position:relative}"
        ".section.tint{background:var(--sf);border-top:1px solid var(--p)1f;border-bottom:1px solid var(--p)1f}"
        ".hero{padding:clamp(58px,9vw,116px) 0}"
        ".herogrid{display:grid;grid-template-columns:1.08fr .92fr;gap:52px;align-items:center}"
        ".hero .sub{font-size:clamp(17px,2vw,20px);margin:20px 0 32px;opacity:.76;max-width:58ch}"
        ".btn{display:inline-flex;align-items:center;gap:9px;padding:15px 30px;border-radius:10px;"
        "font-weight:700;font-size:15px;text-decoration:none;color:#fff;"
        "background:linear-gradient(135deg,var(--p),var(--a));"
        "box-shadow:0 0 0 1px var(--p)55,0 14px 34px -12px var(--p)cc;"
        "transition:transform .28s,box-shadow .28s}"
        ".btn:hover{transform:translateY(-2px);box-shadow:0 0 0 1px var(--a)77,0 20px 44px -14px var(--a)dd}"
        ".btn.ghost{background:var(--p)10;color:var(--tx);border:1px solid var(--p)3d;box-shadow:none}"
        ".btn.ghost:hover{background:var(--p)1f}"
        ".nav{position:sticky;top:0;z-index:50;background:var(--bg)d9;backdrop-filter:blur(16px);"
        "-webkit-backdrop-filter:blur(16px);border-bottom:1px solid var(--p)26}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:70px}"
        ".nav .brand{font-family:var(--display);font-weight:800;font-size:19px;text-decoration:none;color:var(--tx)}"
        ".nav .links{display:flex;gap:28px}"
        ".nav .links a{text-decoration:none;font-size:14px;font-weight:500;opacity:.7}"
        ".nav .links a:hover{opacity:1;color:var(--a)}"
        ".panel{position:relative;border-radius:16px;overflow:hidden;aspect-ratio:4/3;background:var(--sf);"
        "border:1px solid var(--p)33;box-shadow:0 0 0 1px var(--bg),0 40px 80px -40px var(--p)aa}"
        ".panel img{width:100%;height:100%;object-fit:cover;opacity:.92}"
        ".featrow{display:grid;grid-template-columns:1fr 1fr;gap:52px;align-items:center}"
        ".featrow.flip .rowtext{order:2}"
        ".ticks{list-style:none;margin-top:22px;display:grid;gap:12px}"
        ".ticks li{position:relative;padding-left:30px;opacity:.82;"
        "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px}"
        ".ticks li::before{content:'\\203A';position:absolute;left:0;top:-1px;color:var(--a);font-size:18px}"
        ".grid3{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));margin-top:38px}"
        ".scard{background:var(--sf);border:1px solid var(--p)26;border-radius:16px;padding:28px;"
        "transition:border-color .3s,transform .3s,box-shadow .3s;position:relative;overflow:hidden}"
        ".scard::after{content:'';position:absolute;inset:0;opacity:0;transition:opacity .3s;"
        "background:radial-gradient(300px 180px at 50% 0,var(--a)1f,transparent 70%)}"
        ".scard:hover{border-color:var(--a)66;transform:translateY(-4px);box-shadow:0 24px 50px -26px var(--a)88}"
        ".scard:hover::after{opacity:1}"
        ".scard .dot{display:block;width:40px;height:40px;border-radius:11px;"
        "background:linear-gradient(135deg,var(--p),var(--a));margin-bottom:16px;"
        "box-shadow:0 0 20px -4px var(--a)aa}"
        ".steps{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));margin-top:38px}"
        ".step{border-left:2px solid var(--p)33;padding-left:20px}"
        ".step .num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:700;font-size:13px;"
        "letter-spacing:.16em;color:var(--a);display:block;margin-bottom:10px}"
        ".stats{display:grid;gap:1px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-top:34px;"
        "background:var(--p)26;border:1px solid var(--p)26;border-radius:14px;overflow:hidden}"
        ".stat{background:var(--bg);padding:28px}"
        ".faq{border-bottom:1px solid var(--p)26}"
        ".faq summary{cursor:pointer;list-style:none;font-family:var(--display);font-weight:700;font-size:18px;"
        "padding:20px 0;display:flex;justify-content:space-between;gap:16px}"
        ".faq summary::-webkit-details-marker{display:none}"
        ".faq summary::after{content:'+';font-size:24px;color:var(--a);line-height:1}"
        ".faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 20px;opacity:.74}"
        ".ctaband{position:relative;border-radius:22px;padding:clamp(56px,8vw,100px) 24px;text-align:center;"
        "background:linear-gradient(135deg,var(--p)26,var(--a)1f);border:1px solid var(--a)3d;overflow:hidden}"
        ".ctaband p{margin:0 auto 26px;opacity:.84}"
        ".foot{border-top:1px solid var(--p)26;padding:54px 0 30px}"
        ".footgrid{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:32px}"
        ".foot .brand{font-family:var(--display);font-weight:800;font-size:19px}"
        ".foot nav{display:grid;gap:10px}.foot nav a{text-decoration:none;opacity:.66;font-size:14px}"
        ".foot .base{margin-top:30px;padding-top:18px;border-top:1px solid var(--p)1f;display:flex;"
        "justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:13px;opacity:.6;"
        "font-family:ui-monospace,SFMono-Regular,Menlo,monospace}"
        "@media(max-width:860px){.herogrid,.featrow{grid-template-columns:1fr}"
        ".featrow.flip .rowtext{order:0}.nav .links{display:none}.footgrid{grid-template-columns:1fr 1fr}}"
        "@media(max-width:520px){.footgrid{grid-template-columns:1fr}}"
    )


# ── 4. PREMIUM EDITORIAL ─────────────────────────────────────────────────────
# Fashion-magazine discipline: high-contrast serif display, rules, generous
# whitespace, asymmetric grid. Restraint is the luxury signal.
def _css_editorial(t: dict) -> str:
    return (
        "body{font-family:var(--body);color:var(--tx);background:var(--bg);line-height:1.72;"
        "-webkit-font-smoothing:antialiased}"
        "h1{font-family:var(--display);font-weight:400;letter-spacing:-.022em;line-height:1.02;"
        "font-size:clamp(46px,8.4vw,104px)}"
        "h2{font-family:var(--display);font-weight:400;letter-spacing:-.014em;line-height:1.1;"
        "font-size:clamp(30px,4.6vw,52px);margin-bottom:18px}"
        "h3{font-family:var(--display);font-weight:500;font-size:23px;margin-bottom:9px;letter-spacing:-.01em}"
        ".eyebrow{display:block;text-transform:uppercase;letter-spacing:.42em;font-size:10px;font-weight:600;"
        "color:var(--tx);opacity:.55;margin-bottom:26px;font-family:var(--body)}"
        ".section{padding:clamp(72px,11vw,152px) 0}"
        ".section.tint{background:var(--sf)}"
        ".hero{padding:clamp(56px,10vw,128px) 0;border-bottom:1px solid var(--tx)1a}"
        ".herogrid{display:grid;grid-template-columns:1.15fr .85fr;gap:clamp(34px,6vw,80px);align-items:end}"
        ".hero .sub{font-size:clamp(16px,1.7vw,19px);margin:26px 0 34px;opacity:.72;max-width:52ch}"
        ".btn{display:inline-flex;align-items:center;gap:10px;padding:0 0 5px;border-radius:0;"
        "font-family:var(--body);font-weight:600;font-size:14px;letter-spacing:.16em;text-transform:uppercase;"
        "text-decoration:none;color:var(--tx);background:transparent;border-bottom:1.5px solid var(--tx);"
        "transition:gap .3s,opacity .3s}"
        ".btn::after{content:'\\2192'}.btn:hover{gap:16px;opacity:.62}"
        ".btn.ghost{opacity:.6;border-bottom-color:var(--tx)55}.btn.ghost:hover{opacity:1}"
        ".nav{position:sticky;top:0;z-index:50;background:var(--bg)f2;backdrop-filter:blur(10px);"
        "-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--tx)14}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:82px}"
        ".nav .brand{font-family:var(--display);font-weight:400;font-size:25px;letter-spacing:-.01em;"
        "text-decoration:none;color:var(--tx)}"
        ".nav .links{display:flex;gap:36px}"
        ".nav .links a{text-decoration:none;font-size:11px;letter-spacing:.22em;text-transform:uppercase;"
        "font-weight:600;opacity:.62}.nav .links a:hover{opacity:1}"
        ".panel{overflow:hidden;aspect-ratio:3/4;background:var(--sf)}"
        ".panel img{width:100%;height:100%;object-fit:cover;filter:grayscale(.14);transition:filter .8s,transform 1.2s}"
        ".panel:hover img{filter:grayscale(0);transform:scale(1.03)}"
        ".featrow{display:grid;grid-template-columns:.9fr 1.1fr;gap:clamp(34px,6vw,84px);align-items:center;"
        "padding-top:clamp(34px,5vw,64px);border-top:1px solid var(--tx)14}"
        ".featrow.flip{grid-template-columns:1.1fr .9fr}.featrow.flip .rowtext{order:2}"
        ".ticks{list-style:none;margin-top:26px;display:grid;gap:15px}"
        ".ticks li{position:relative;padding-left:0;opacity:.74;border-top:1px solid var(--tx)14;padding-top:13px;"
        "font-size:15px}"
        ".grid3{display:grid;gap:0;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:44px;"
        "border-top:1px solid var(--tx)1a}"
        ".scard{padding:36px 30px 36px 0;border-right:1px solid var(--tx)14;transition:opacity .35s}"
        ".scard:last-child{border-right:none}.scard:hover{opacity:.66}"
        ".scard .dot{display:block;width:100%;height:1px;background:var(--tx);opacity:.28;margin-bottom:24px}"
        ".steps{display:grid;gap:0;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-top:44px}"
        ".step{padding:30px 26px 30px 0;border-top:1px solid var(--tx)1a}"
        ".step .num{font-family:var(--display);font-weight:400;font-size:46px;opacity:.24;display:block;"
        "line-height:1;margin-bottom:12px}"
        ".stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));margin-top:40px;"
        "border-top:1px solid var(--tx)1a}"
        ".stat{padding:30px 24px 30px 0;border-right:1px solid var(--tx)14}.stat:last-child{border-right:none}"
        ".faq{border-bottom:1px solid var(--tx)14}"
        ".faq summary{cursor:pointer;list-style:none;font-family:var(--display);font-weight:400;font-size:22px;"
        "padding:26px 0;display:flex;justify-content:space-between;gap:18px}"
        ".faq summary::-webkit-details-marker{display:none}"
        ".faq summary::after{content:'+';font-size:22px;opacity:.5;line-height:1}"
        ".faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 26px;opacity:.7;max-width:58ch}"
        ".ctaband{padding:clamp(72px,11vw,140px) 24px;text-align:center;background:var(--tx);color:var(--bg);"
        "border-radius:0}"
        ".ctaband h2{color:var(--bg)}.ctaband p{margin:0 auto 32px;opacity:.76}"
        ".ctaband .btn{color:var(--bg);border-bottom-color:var(--bg)}"
        ".foot{border-top:1px solid var(--tx)1a;padding:64px 0 32px}"
        ".footgrid{display:grid;grid-template-columns:1.8fr 1fr 1fr;gap:38px}"
        ".foot .brand{font-family:var(--display);font-weight:400;font-size:26px}"
        ".foot nav{display:grid;gap:12px}"
        ".foot nav a{text-decoration:none;opacity:.6;font-size:11px;letter-spacing:.18em;text-transform:uppercase}"
        ".foot .base{margin-top:38px;padding-top:20px;border-top:1px solid var(--tx)14;display:flex;"
        "justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:11px;letter-spacing:.14em;"
        "text-transform:uppercase;opacity:.5}"
        "@media(max-width:860px){.herogrid,.featrow,.featrow.flip{grid-template-columns:1fr}"
        ".featrow.flip .rowtext{order:0}.nav .links{display:none}.panel{aspect-ratio:4/3}"
        ".scard{border-right:none;border-bottom:1px solid var(--tx)14;padding-right:0}"
        ".footgrid{grid-template-columns:1fr}}"
    )


# ── 5. PROFESSIONAL LOCAL ────────────────────────────────────────────────────
# Trust-first: warm light ground, clear hierarchy, generous tap targets, no
# spectacle. Optimised for "call this business", not for art direction awards.
def _css_professional(t: dict) -> str:
    return (
        "body{font-family:var(--body);color:var(--tx);background:var(--bg);line-height:1.68;"
        "-webkit-font-smoothing:antialiased}"
        "h1{font-family:var(--display);font-weight:800;letter-spacing:-.028em;line-height:1.08;"
        "font-size:clamp(36px,5.4vw,60px)}"
        "h2{font-family:var(--display);font-weight:800;letter-spacing:-.018em;"
        "font-size:clamp(26px,3.4vw,40px);margin-bottom:14px}"
        "h3{font-family:var(--display);font-weight:700;font-size:19px;margin-bottom:8px}"
        ".eyebrow{display:inline-block;text-transform:uppercase;letter-spacing:.15em;font-size:12px;"
        "font-weight:700;color:var(--p);margin-bottom:14px}"
        ".section{padding:clamp(54px,7.5vw,96px) 0}.section.tint{background:var(--sf)}"
        ".hero{background:linear-gradient(170deg,var(--p)0f,var(--a)08);padding:clamp(48px,7vw,92px) 0;"
        "border-bottom:1px solid var(--p)1a}"
        ".herogrid{display:grid;grid-template-columns:1.1fr .9fr;gap:44px;align-items:center}"
        ".hero .sub{font-size:clamp(17px,2vw,20px);margin:18px 0 28px;opacity:.8}"
        # generous, obvious tap targets: this audience converts by phone
        ".btn{display:inline-flex;align-items:center;gap:9px;background:var(--p);color:#fff;"
        "padding:16px 30px;border-radius:12px;font-weight:700;font-size:16px;text-decoration:none;"
        "box-shadow:0 8px 20px -8px var(--p)99;transition:transform .2s,box-shadow .2s}"
        ".btn:hover{transform:translateY(-2px);box-shadow:0 14px 28px -10px var(--p)bb}"
        ".btn.ghost{background:#fff;color:var(--p);border:1.5px solid var(--p)3d;box-shadow:none}"
        ".btn.ghost:hover{background:var(--p)0a}"
        ".nav{position:sticky;top:0;z-index:50;background:var(--bg)f0;backdrop-filter:blur(12px);"
        "-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--p)1a}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:70px}"
        ".nav .brand{font-family:var(--display);font-weight:800;font-size:20px;color:var(--p);text-decoration:none}"
        ".nav .links{display:flex;gap:26px}"
        ".nav .links a{text-decoration:none;font-weight:600;font-size:15px;opacity:.8}"
        ".nav .links a:hover{opacity:1;color:var(--p)}"
        ".panel{border-radius:18px;overflow:hidden;aspect-ratio:4/3;background:var(--sf);"
        "border:1px solid var(--p)1a;box-shadow:0 20px 44px -26px var(--p)77}"
        ".panel img{width:100%;height:100%;object-fit:cover}"
        ".featrow{display:grid;grid-template-columns:1fr 1fr;gap:44px;align-items:center}"
        ".featrow.flip .rowtext{order:2}"
        ".ticks{list-style:none;margin-top:20px;display:grid;gap:12px}"
        ".ticks li{position:relative;padding-left:32px;opacity:.86}"
        ".ticks li::before{content:'\\2713';position:absolute;left:0;top:0;width:20px;height:20px;"
        "border-radius:50%;background:var(--a)26;color:var(--p);font-size:12px;font-weight:700;"
        "display:flex;align-items:center;justify-content:center}"
        ".grid3{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:32px}"
        ".scard{background:#fff;border:1px solid var(--p)1f;border-radius:16px;padding:26px;"
        "transition:transform .2s,box-shadow .2s}"
        ".scard:hover{transform:translateY(-4px);box-shadow:0 20px 40px -22px var(--p)77}"
        ".scard .dot{display:flex;align-items:center;justify-content:center;width:44px;height:44px;"
        "border-radius:12px;background:var(--p)14;color:var(--p);margin-bottom:14px;font-weight:800}"
        ".steps{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-top:32px}"
        ".step{background:#fff;border:1px solid var(--p)1a;border-radius:16px;padding:24px}"
        ".step .num{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;"
        "border-radius:50%;background:var(--p);color:#fff;font-weight:800;font-size:16px;margin-bottom:12px}"
        ".stats{display:flex;flex-wrap:wrap;gap:16px;margin-top:28px}"
        ".stat{flex:1 1 190px;background:#fff;border:1px solid var(--p)1f;border-radius:16px;padding:22px}"
        ".faq{border-bottom:1px solid var(--p)1f}"
        ".faq summary{cursor:pointer;list-style:none;font-family:var(--display);font-weight:700;font-size:18px;"
        "padding:18px 0;display:flex;justify-content:space-between;gap:16px}"
        ".faq summary::-webkit-details-marker{display:none}"
        ".faq summary::after{content:'+';font-size:26px;color:var(--p);line-height:1}"
        ".faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 18px;opacity:.8}"
        ".ctaband{background:linear-gradient(135deg,var(--p),var(--a));color:#fff;border-radius:24px;"
        "padding:clamp(44px,7vw,80px) 24px;text-align:center}"
        ".ctaband h2{color:#fff}.ctaband p{margin:0 auto 24px;opacity:.94}"
        ".ctaband .btn{background:#fff;color:var(--p);box-shadow:0 12px 26px -10px rgba(0,0,0,.34)}"
        ".foot{border-top:1px solid var(--p)1a;padding:48px 0 28px}"
        ".footgrid{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:32px}"
        ".foot .brand{font-family:var(--display);font-weight:800;font-size:20px;color:var(--p)}"
        ".foot nav{display:grid;gap:10px}.foot nav a{text-decoration:none;opacity:.75;font-size:14px}"
        ".foot .base{margin-top:28px;padding-top:18px;border-top:1px solid var(--p)14;display:flex;"
        "justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:13px;opacity:.7}"
        "@media(max-width:860px){.herogrid,.featrow{grid-template-columns:1fr}"
        ".featrow.flip .rowtext{order:0}.nav .links{display:none}.footgrid{grid-template-columns:1fr 1fr}}"
        "@media(max-width:520px){.footgrid{grid-template-columns:1fr}.btn{width:100%;justify-content:center}}"
    )


RECIPES: tuple = (
    DesignRecipe(
        id="cinematic_luxury",
        label="Cinematic luxury",
        signals=("cinematic", "luxury", "luxe", "premium dark", "dramatic", "bold", "elite",
                 "high-end", "exclusive", "athletic", "performance", "strength", "transformation"),
        affinity=("fitness", "restaurant", "health", "portfolio"),
        palette={"p": "#c8a951", "a": "#e8c874", "bg": "#0a0a0c", "tx": "#f4f2ee",
                 "sf": "#141418", "r": "2px", "maxw": "1200px",
                 "dfallback": "Georgia,serif", "bfallback": "system-ui,sans-serif"},
        display_font="Bebas Neue", body_font="Inter",
        motion="expressive", asset_policy="photo", density="airy",
        css=_css_cinematic,
        notes="Dark theatrical ground; photography is the hero. Type is the second subject.",
        composition=('hero_cinematic','feature_rows','gallery_strip','service_grid','process','proof_band','faq','cta_band'),
        motion_rules={'budget':'expressive','allowed':('reveal-on-scroll','image-zoom','parallax-scrim'),'forbidden':('bounce','confetti'),'duration_ms':(350,1100)},
        surface_rules={'corner':'square','elevation':'none','divider':'hairline-light','contrast':'high','ground':'dark'},
        assets={'photography':'required','people':'preferred','illustration_hero':'forbidden','hero_media':'required','treatment':'cinematic-scrim','orientation':'landscape','min_width':1600},
        license='Original work (Getszy). CSS proprietary-internal. No inherited licence.',
        provenance={'author':'Getszy','origin':'original','third_party':(),'techniques':('CSS grid','object-fit','backdrop-filter','gradient scrim')},
        security_review='No JS dependency, no CDN, no external stylesheet, no url(http) in CSS. Generated markup is escaped upstream by builder_agents._esc.',
        render_verification={'status':'static_passed_browser_inspected','harness':'tools/design_render_check.py','browser':'chromium (manual, out-of-band)','playwright_pass':False,'date':'2026-08-30'},
    ),
    DesignRecipe(
        id="glassmorphism",
        label="Luminous glass",
        signals=("glass", "glassmorphism", "frosted", "translucent", "soft", "pastel", "airy",
                 "beauty", "salon", "spa", "wellness", "skincare", "calm", "serene", "aesthetic"),
        affinity=("salon", "health", "service", "ecommerce"),
        palette={"p": "#7c5cff", "a": "#22b8cf", "bg": "#f6f4ff", "tx": "#181433",
                 "sf": "#ffffff", "r": "24px", "maxw": "1140px",
                 "dfallback": "system-ui,sans-serif", "bfallback": "system-ui,sans-serif"},
        display_font="Plus Jakarta Sans", body_font="Inter",
        motion="subtle", asset_policy="photo", density="balanced",
        css=_css_glass,
        notes="Layered translucent surfaces over an ambient colour field. Depth without weight.",
        composition=('hero_split_glass','glass_cards','feature_rows','process','proof_band','faq','cta_band'),
        motion_rules={'budget':'subtle','allowed':('hover-lift','fade-in','soft-scale'),'forbidden':('parallax','marquee'),'duration_ms':(200,600)},
        surface_rules={'corner':'rounded-lg','elevation':'soft','divider':'translucent','blur':'required','contrast':'medium','ground':'light'},
        assets={'photography':'preferred','people':'optional','illustration_hero':'discouraged','hero_media':'preferred','treatment':'behind-glass','orientation':'landscape','min_width':1200},
        license='Original work (Getszy). CSS proprietary-internal. No inherited licence.',
        provenance={'author':'Getszy','origin':'original','third_party':(),'techniques':('backdrop-filter','radial-gradient field','CSS grid')},
        security_review='No JS dependency, no CDN, no external stylesheet, no url(http) in CSS. Generated markup is escaped upstream by builder_agents._esc.',
        render_verification={'status':'static_passed_browser_inspected','harness':'tools/design_render_check.py','browser':'chromium (manual, out-of-band)','playwright_pass':False,'date':'2026-08-30'},
    ),
    DesignRecipe(
        id="futuristic_saas",
        label="Futuristic product",
        signals=("ai", "saas", "futuristic", "tech", "platform", "dashboard", "automation",
                 "developer", "api", "data", "analytics", "neon", "cyber", "software", "startup"),
        affinity=("saas", "consultant", "service"),
        palette={"p": "#6366f1", "a": "#22d3ee", "bg": "#07070c", "tx": "#eef2ff",
                 "sf": "#0e0e18", "r": "16px", "maxw": "1180px",
                 "dfallback": "system-ui,sans-serif", "bfallback": "system-ui,sans-serif"},
        display_font="Space Grotesk", body_font="Inter",
        motion="subtle", asset_policy="gradient", density="dense",
        css=_css_futuristic,
        notes="Engineering grid + aurora field in pure CSS. No canvas/WebGL runtime cost.",
        composition=('hero_product','feature_rows','spec_grid','process','metrics','faq','cta_band'),
        motion_rules={'budget':'subtle','allowed':('glow-hover','fade-up','grid-drift'),'forbidden':('parallax-hero','autoplay-video'),'duration_ms':(180,520)},
        surface_rules={'corner':'rounded-md','elevation':'glow','divider':'hairline-accent','contrast':'high','ground':'dark'},
        assets={'photography':'preferred','people':'optional','illustration_hero':'discouraged','hero_media':'preferred','treatment':'gradient-mesh','orientation':'landscape','min_width':1200},
        license='Original work (Getszy). CSS proprietary-internal. No inherited licence.',
        provenance={'author':'Getszy','origin':'original','third_party':(),'techniques':('repeating grid background','radial aurora','background-clip text')},
        security_review='No JS dependency, no CDN, no external stylesheet, no url(http) in CSS. Generated markup is escaped upstream by builder_agents._esc.',
        render_verification={'status':'static_passed_browser_inspected','harness':'tools/design_render_check.py','browser':'chromium (manual, out-of-band)','playwright_pass':False,'date':'2026-08-30'},
    ),
    DesignRecipe(
        id="editorial_fashion",
        label="Premium editorial",
        signals=("editorial", "fashion", "magazine", "minimal", "boutique", "atelier", "couture",
                 "gallery", "curated", "designer", "elegant", "refined", "timeless", "monochrome"),
        affinity=("portfolio", "ecommerce", "restaurant"),
        palette={"p": "#1a1a1a", "a": "#8a7355", "bg": "#faf8f5", "tx": "#14120f",
                 "sf": "#f0ece6", "r": "0px", "maxw": "1220px",
                 "dfallback": "Georgia,'Times New Roman',serif", "bfallback": "system-ui,sans-serif"},
        display_font="Playfair Display", body_font="Inter",
        motion="subtle", asset_policy="photo", density="airy",
        css=_css_editorial,
        notes="Magazine discipline: rules, whitespace, asymmetry. Restraint signals luxury.",
        composition=('hero_editorial','manifesto','lookbook','feature_rows','index_list','faq','cta_minimal'),
        motion_rules={'budget':'subtle','allowed':('grayscale-reveal','slow-zoom','underline-slide'),'forbidden':('glow','bounce','parallax'),'duration_ms':(300,1200)},
        surface_rules={'corner':'square','elevation':'none','divider':'rule-system','contrast':'high','ground':'paper'},
        assets={'photography':'required','people':'preferred','illustration_hero':'forbidden','hero_media':'required','treatment':'editorial-crop','orientation':'portrait','min_width':1400},
        license='Original work (Getszy). CSS proprietary-internal. No inherited licence.',
        provenance={'author':'Getszy','origin':'original','third_party':(),'techniques':('asymmetric CSS grid','hairline rule system','type ramp')},
        security_review='No JS dependency, no CDN, no external stylesheet, no url(http) in CSS. Generated markup is escaped upstream by builder_agents._esc.',
        render_verification={'status':'static_passed_browser_inspected','harness':'tools/design_render_check.py','browser':'chromium (manual, out-of-band)','playwright_pass':False,'date':'2026-08-30'},
    ),
    DesignRecipe(
        id="professional_local",
        label="Professional local",
        signals=("local", "trusted", "family", "professional", "reliable", "affordable", "near me",
                 "clinic", "repair", "plumber", "electrician", "dentist", "legal", "accounting",
                 "consultant", "service", "appointment", "book"),
        affinity=("service", "consultant", "health", "education", "default"),
        palette={"p": "#1d4ed8", "a": "#0ea5e9", "bg": "#ffffff", "tx": "#0f172a",
                 "sf": "#f1f5f9", "r": "16px", "maxw": "1140px",
                 "dfallback": "system-ui,sans-serif", "bfallback": "system-ui,sans-serif"},
        display_font="Plus Jakarta Sans", body_font="Inter",
        motion="none", asset_policy="photo", density="balanced",
        css=_css_professional,
        notes="Trust-first. Big tap targets, obvious contact paths, zero spectacle.",
        composition=('hero_local','trust_row','service_grid','feature_rows','process','faq','cta_band'),
        motion_rules={'budget':'none','allowed':('hover-lift',),'forbidden':('parallax','autoplay','marquee','glow'),'duration_ms':(120,260)},
        surface_rules={'corner':'rounded-md','elevation':'soft','divider':'solid-light','contrast':'medium','ground':'light'},
        assets={'photography':'preferred','people':'preferred','illustration_hero':'discouraged','hero_media':'preferred','treatment':'plain','orientation':'landscape','min_width':1200},
        license='Original work (Getszy). CSS proprietary-internal. No inherited licence.',
        provenance={'author':'Getszy','origin':'original','third_party':(),'techniques':('CSS grid','solid borders','system type stack')},
        security_review='No JS dependency, no CDN, no external stylesheet, no url(http) in CSS. Generated markup is escaped upstream by builder_agents._esc.',
        render_verification={'status':'static_passed_browser_inspected','harness':'tools/design_render_check.py','browser':'chromium (manual, out-of-band)','playwright_pass':False,'date':'2026-08-30'},
    ),
)

_BY_ID = {r.id: r for r in RECIPES}
DEFAULT_RECIPE_ID = "professional_local"


def get_recipe(recipe_id: str) -> DesignRecipe:
    """Look up a vetted recipe, falling back to the safe professional default."""
    return _BY_ID.get(recipe_id or "", _BY_ID[DEFAULT_RECIPE_ID])


def all_recipe_ids() -> list:
    return [r.id for r in RECIPES]


def stylesheet(recipe: DesignRecipe) -> str:
    """Full self-contained stylesheet for one recipe: tokens + base + a11y + system.

    Self-contained by construction -- no @import, no CDN, no external stylesheet
    beyond the optional webfont link, which always has a system fallback.
    """
    return _vars(recipe) + _BASE + _A11Y + recipe.css(recipe.palette)


__all__ = ["DesignRecipe", "RECIPES", "get_recipe", "all_recipe_ids", "stylesheet",
           "DEFAULT_RECIPE_ID"]
