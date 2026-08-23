import asyncio
"""Builder Agents — Multi-agent pipeline for website generation.

Pipeline: Planner → Designer → Coder → Reviewer
Each agent specializes in one aspect, producing better output than a single monolithic LLM call.
"""
import re
import json
import html as _html
import logging
from llm_provider import professional_builder_completion
from builder_quality import evaluate_landing_page_quality

logger = logging.getLogger('getszy.builder.agents')


# ── Agent System Prompts ──────────────────────────────────────────────────────

PLANNER_PROMPT = """You are a website strategist/planner.

Given a user request, produce a concise site plan as JSON:
{
  "site_type": "landing|portfolio|business|blog|saas",
  "sections": ["hero", "features", "testimonials", "pricing", "cta", "footer"],
  "color_scheme": "warm|cool|dark|light|vibrant",
  "typography": "modern|classic|playful|minimal",
  "tone": "professional|friendly|bold|elegant",
  "key_message": "one sentence describing the site's core purpose",
  "target_audience": "who this site is for",
  "primary_goal": "one measurable action such as collect leads, book a demo, sell a product, or start a trial",
  "primary_cta": "short action-led button label",
  "proof_strategy": "only real proof supplied by the customer, otherwise an honest proof-plan placeholder"
}

Reply ONLY with valid JSON. No prose."""

DESIGNER_PROMPT = """You are a UI/UX designer specializing in modern web design.

Given a site plan (JSON), output a detailed design brief as JSON:
{
  "palette": {"primary": "#hex", "secondary": "#hex", "accent": "#hex", "bg": "#hex", "text": "#hex"},
  "fonts": {"display": "Font Name", "body": "Font Name"},
  "sections": [
    {
      "name": "hero",
      "layout": "centered|split|full-width",
      "description": "what goes here",
      "visual_style": "gradient|image-bg|solid|glass",
      "elements": ["heading", "subheading", "cta-button", "hero-image"]
    }
  ],
  "animations": ["fade-in", "slide-up", "hover-scale"],
  "responsive_notes": "mobile hierarchy, touch targets, and breakpoint considerations",
  "conversion_hierarchy": "what visitors should understand and do in the first 5 seconds"
}

Reply ONLY with valid JSON. No prose."""

CODER_PROMPT = """You are a world-class front-end designer, art director and conversion copywriter trusted by premium brands. Generate a stunning, modern, fully-responsive, conversion-focused SINGLE-PAGE WEBSITE that looks custom-built by a top studio — never a template.

STRICT OUTPUT RULES:
1. Output ONLY a SINGLE complete HTML document. No prose. No markdown fences.
2. Begin with <!DOCTYPE html> and end with </html>.
3. Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
4. Use Google Fonts via <link> for premium typography (e.g. Inter, Plus Jakarta Sans, Space Grotesk).
5. Images: use ONLY real product images provided in the brief. If none are provided, use tasteful CSS gradients, brand colors, or inline SVG — NEVER use placeholder/random image services (no picsum, no lorem, no via.placeholder).
6. Treat the supplied professional page brief as product truth. Do not invent testimonials, company logos, customer counts, pricing, guarantees, legal claims, integrations, or capabilities. If authentic proof is not supplied, use an honest editable proof-plan placeholder rather than a fake testimonial or statistic.
7. Build around one conversion goal and one primary CTA. Include only sections that support that goal: hero with a benefit-led H1 and CTA, relevant benefits, how it works, real proof or proof-plan, offer/pricing only when supplied, FAQ, closing CTA and footer. Do not add distracting navigation or competing CTAs to a campaign landing page.
8. Micro-interactions via CSS transitions/animations and a tiny inline <script> ONLY for the mobile menu toggle and scroll-reveal (no other JS needed).
9. Premium aesthetic: generous whitespace, refined typographic scale, consistent spacing, restrained decoration, strong CTA contrast, and content that remains readable rather than merely decorative.
10. Fully responsive and mobile-first. Verify the information hierarchy, CTA visibility, horizontal overflow, and touch targets at 375px, tablet width, and 1440px.
11. Accessibility: semantic header/main/footer landmarks, a single H1, alt text on every meaningful image, sufficient contrast, visible focus rings, and ARIA where helpful. SEO: complete head with title, meta description, Open Graph, and structured JSON-LD only when the supplied brief supports it.
12. Compelling, specific conversion copy (not lorem ipsum): clear headline, concise benefit-driven body, and action-led CTA that matches the primary goal.
13. NEVER include forms that POST to external URLs. NEVER include trackers or fetch() to third-party.
14. Do not use a generic card grid as the primary visual language. Compose one intentional hero, one editorial rhythm, two or three distinct section treatments, and a closing conversion moment. Use the supplied visual direction rather than repeating the same layout.
15. If no real customer image is supplied, create a premium CSS/SVG art direction that is specific to the business brief; do not leave empty image cards or image placeholder areas.
16. Total HTML should be 300-800 lines. Color scheme, fonts, and section layout MUST match the design brief exactly.
17. WORLD-CLASS BAR: this must read as a $20k+ bespoke site, not a generator output. Compose a distinctive art direction (custom gradient/duotone or inline-SVG motif derived from the brand), an editorial rhythm with varied section treatments and typographic scale, refined micro-interactions, a confident hero, and a decisive closing conversion moment. Avoid generic utility-only layouts and repetitive card grids.

START IMMEDIATELY WITH <!DOCTYPE html>. End with </html>. Nothing else."""

FAST_COMPOSITION_PROMPT = """You are Getszy's Professional Composition Engine. Create one distinctive, premium, conversion-grade, responsive private landing-page draft from the verified customer brief.

OUTPUT: ONLY one complete HTML document, beginning with <!DOCTYPE html> and ending with </html>. Use Tailwind CSS via CDN and one refined premium Google Font pairing (e.g. Plus Jakarta Sans + Inter, or Space Grotesk + Source Serif).

PREMIUM DESIGN SYSTEM (apply deliberately, never a generic template):
- Editorial hierarchy: one decisive hero with a benefit-led H1, a supporting sub-headline, and a single high-contrast primary CTA.
- Restrained, intentional art direction: a branded gradient/duotone or inline SVG motif derived from the brief, generous whitespace, a disciplined spacing rhythm, and a consistent accent color used sparingly for emphasis and the CTA.
- Two or three distinct section treatments (not a repeated card grid): an editorial feature block, a process/steps rhythm, and a proof or offer block. Vary typography scale, background tint, and alignment between sections.
- Refined micro-typography: tight display headings, a comfortable body measure, visible focus rings, and a real mobile breakpoint at 375px.

NON-NEGOTIABLE:
1. Treat VERIFIED CUSTOMER BRIEF as the only product truth. Never invent testimonials, ratings, awards, logos, addresses, phone numbers, prices, discounts, guarantees, urgency, stock, certifications, or legal claims.
2. Build a unique visual composition for this brief, not a reusable generic card grid: a strong editorial hero, one intentional art direction, varied section rhythms, decisive CTA, and a polished mobile experience.
3. If no real image URL is supplied, create a business-specific premium CSS/SVG visual treatment; never use image placeholders, random image services, empty image cards, or third-party trackers.
4. Include: title, meta description, semantic header/main/footer, exactly one H1, a CTA matching the supplied goal, responsive rules, focus styles, useful image alt text, and private-draft-safe copy.
5. Use 5–7 meaningful sections only. Prefer specific benefit, process and offer sections. Include testimonials/prices/claims only when they appear in the verified brief.
6. No external form POST, fetch(), trackers, iframes, data:text/html, or unsafe JavaScript. Use a tiny mobile-menu script only if necessary.
7. Target 250–450 lines with refined typography, generous whitespace, strong hierarchy and clear device responsiveness. Do not narrate your work or output markdown.

WORLD-CLASS BAR: the result must read as a bespoke $20k+ studio site, not a generator output. Lead with a distinctive art direction (branded gradient/duotone or an inline-SVG motif built from the brief), an editorial rhythm with varied section treatments and typographic scale, restrained motion, a confident hero, and one decisive closing conversion moment. Never fall back to a generic utility-only layout or a repeated card grid.

Speed matters. Make the complete professional draft in this one response. A deterministic Getszy quality check will inspect it before the customer sees it."""


REVIEWER_PROMPT = """You are a code reviewer for HTML/CSS websites.

Review the provided HTML and fix:
1. Broken image URLs by removing the image or replacing it only with a real asset supplied in the brief; never add placeholder or random-image services.
2. Missing mobile-responsive layout rules, CTA visibility, or horizontal-overflow issues.
3. Accessibility issues: missing landmarks, missing image alt text, low contrast, missing focus styles, or invalid heading hierarchy.
4. CSS inconsistencies, broken layouts, and visual clutter that obscures the primary conversion goal.
5. JavaScript errors or third-party network calls that are not required for the page.
6. Missing technical metadata: charset, viewport, descriptive title, and meta description.
7. Fabricated proof, claims, prices, guarantees, testimonials, logos, or metrics. Remove unverified claims and leave an honest editable placeholder where customer proof is needed.

Output ONLY the COMPLETE, FIXED HTML document. No explanation. No markdown."""

ELEMENT_REFINE_PROMPT = """You are refining a SPECIFIC SECTION of an existing website.

You will be given:
1. The FULL current HTML
2. The CSS selector or section name to target
3. The user's refinement instruction

RULES:
1. Output ONLY the COMPLETE, UPDATED HTML document (not just the changed part).
2. Apply the change precisely to the targeted section.
3. Keep everything else identical.
4. Begin with <!DOCTYPE html>. End with </html>.

START IMMEDIATELY WITH <!DOCTYPE html>."""


# ── Pipeline Functions ─────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    """Extract JSON from LLM response."""
    raw = raw.strip()
    s = raw.find('{')
    e = raw.rfind('}')
    if s != -1 and e > s:
        try:
            return json.loads(raw[s:e + 1])
        except json.JSONDecodeError:
            pass
    return None


def _extract_html(raw: str) -> str:
    """Pull HTML doc out of LLM response."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:html)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    m = re.search(r'<!DOCTYPE\s+html[^>]*>', raw, re.IGNORECASE)
    if m:
        raw = raw[m.start():]
    else:
        m2 = re.search(r'<html', raw, re.IGNORECASE)
        if m2:
            raw = '<!DOCTYPE html>\n' + raw[m2.start():]
    end = re.search(r'</html\s*>', raw, re.IGNORECASE)
    if end:
        raw = raw[:end.end()]
    return raw


def _esc(value) -> str:
    return _html.escape(str(value), quote=True)


def _derive_name(prompt: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', prompt or '')[:6]
    return ' '.join(words).title() or 'Your Brand'


def _repair_html(html: str) -> str:
    """Guarantee a valid, complete, premium-ready single document.

    Safety net on every generated page so the customer never receives broken or
    markdown-wrapped markup. Only repairs structure; never changes copy.
    """
    if not html:
        return html
    raw = _extract_html(html)
    lowered = raw.lower()

    if '<head' not in lowered:
        m = re.search(r'<html[^>]*>', raw, re.IGNORECASE)
        if m:
            raw = raw[:m.end()] + '<head></head>' + raw[m.end():]
        else:
            raw = '<html><head></head>' + raw
        lowered = raw.lower()
    if 'charset' not in lowered:
        raw = raw.replace('<head>', '<head>\n<meta charset="utf-8">', 1)
        lowered = raw.lower()
    if 'name="viewport"' not in lowered and "name='viewport'" not in lowered:
        raw = raw.replace('</head>', '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>', 1)
        lowered = raw.lower()
    if '<title' not in lowered:
        raw = raw.replace('</head>', '<title>Getszy Site</title>\n</head>', 1)
        lowered = raw.lower()
    if '<body' not in lowered:
        raw = raw.replace('</head>', '</head>\n<body>', 1)
        if '</html>' in raw.lower():
            raw = raw.replace('</html>', '</body>\n</html>', 1)
        else:
            raw = raw + '\n</body>\n</html>'
        lowered = raw.lower()
    if '</html>' not in lowered:
        raw = raw + '\n</html>'
    return raw


# Curated, restrained premium palettes (hex without '#'). Picked deterministically
# from the brand name so the same brand always looks the same.
_PREMIUM_PALETTES = [
    {'primary': '4f46e5', 'accent': '06b6d4', 'bg': 'ffffff', 'text': '0f172a', 'surface': 'f8fafc'},
    {'primary': '059669', 'accent': 'f59e0b', 'bg': 'ffffff', 'text': '111827', 'surface': 'ecfdf5'},
    {'primary': 'e11d48', 'accent': 'f43f5e', 'bg': '0f172a', 'text': 'f8fafc', 'surface': '1e293b'},
    {'primary': '0ea5e9', 'accent': '8b5cf6', 'bg': 'ffffff', 'text': '0f172a', 'surface': 'f0f9ff'},
]


def _premium_template(prompt: str, brief: dict | None = None) -> str:
    """Deterministic, always-available premium landing page.

    FINAL GUARANTEE: if every LLM provider is unavailable we still return a
    complete, responsive, on-brand, conversion-focused page so the customer
    never sees an error or a blank draft. No external calls, no randomness.
    """
    brief = brief or {}
    confirmed = {k: v for k, v in brief.items() if v not in (None, '', [])}
    brand = str(confirmed.get('brand_name') or confirmed.get('business_name') or _derive_name(prompt))
    goal = str(confirmed.get('primary_goal') or 'reach more of the right customers')
    cta = str(confirmed.get('primary_cta') or 'Get started')
    audience = str(confirmed.get('audience') or 'your customers')
    proof_points = confirmed.get('proof_points') or []
    cta_lower = (cta or 'get started').lower()

    palette = _PREMIUM_PALETTES[sum(ord(c) for c in brand) % len(_PREMIUM_PALETTES)]
    p, a, bg, tx, sf = palette['primary'], palette['accent'], palette['bg'], palette['text'], palette['surface']

    style = (
        ":root{--p:#__P__;--a:#__A__;--bg:#__BG__;--tx:#__TX__;--sf:#__SF__}"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "html{scroll-behavior:smooth}"
        "body{font-family:'Inter',system-ui,sans-serif;color:#__TX__;background:#__BG__;line-height:1.6;-webkit-font-smoothing:antialiased}"
        ".display{font-family:'Plus Jakarta Sans',system-ui,sans-serif;font-weight:800;letter-spacing:-0.02em;line-height:1.05}"
        ".wrap{max-width:1120px;margin:0 auto;padding:0 24px}"
        ".hero{background:radial-gradient(1200px 600px at 80% -10%, #__A__22, transparent),linear-gradient(135deg,#__P__0d,#__A__05);color:#__TX__}"
        ".btn{display:inline-flex;align-items:center;gap:8px;background:#__P__;color:#fff;padding:14px 26px;border-radius:999px;font-weight:700;text-decoration:none;transition:transform .2s ease, box-shadow .2s ease}"
        ".btn:hover{transform:translateY(-2px);box-shadow:0 12px 30px #__A__33}"
        "section{padding:88px 0}"
        ".eyebrow{text-transform:uppercase;letter-spacing:.18em;font-size:12px;font-weight:700;color:#__A__}"
        ".card{background:#__SF__;border:1px solid #__P__22;border-radius:20px;padding:28px;transition:transform .2s ease, box-shadow .2s ease}"
        ".card:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(15,23,42,.08)}"
        "h2{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:clamp(28px,4vw,40px);letter-spacing:-0.02em;margin-bottom:14px}"
        ".muted{opacity:.72}"
        "a:focus-visible,button:focus-visible{outline:3px solid #__A__;outline-offset:3px;border-radius:6px}"
        "@media(max-width:720px){section{padding:56px 0}.hero{padding-top:64px}}"
    )
    style = (
        style.replace('__P__', p).replace('__A__', a)
        .replace('__BG__', bg).replace('__TX__', tx).replace('__SF__', sf)
    )

    if proof_points:
        proof_items = "".join(
            f'<li class="card"><strong>{_esc(pt)}</strong></li>' for pt in proof_points[:4]
        )
        proof_block = (
            '<section class="wrap"><span class="eyebrow">Proof</span>'
            '<h2>Results customers can stand behind</h2>'
            f'<ul style="display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));list-style:none;margin-top:24px">{proof_items}</ul></section>'
        )
    else:
        proof_block = (
            '<section class="wrap"><span class="eyebrow">Proof plan</span>'
            '<h2>Add verified results</h2>'
            '<p class="muted" style="max-width:60ch">Replace this section with real customer outcomes — metrics, case notes, or a short quote you are authorised to publish. '
            'We never invent testimonials or statistics, so the published page stays truthful and review-ready.</p></section>'
        )

    script = (
        "<script>document.addEventListener('click',function(e){"
        "var t=e.target.closest('a[href^=\"#\"]');if(t){"
        "var id=t.getAttribute('href');if(id&&id.length>1){"
        "var el=document.querySelector(id);if(el){el.scrollIntoView({behavior:'smooth'});e.preventDefault();}}}});</script>"
    )

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(brand)} — {_esc(goal[:48])}</title>
<meta name="description" content="{_esc(brand)} helps {_esc(audience)} {_esc(goal)}. {_esc(cta)} today.">
<meta property="og:title" content="{_esc(brand)}">
<meta property="og:description" content="{_esc(goal)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>{style}</style>
</head>
<body>
<header class="wrap" style="display:flex;align-items:center;justify-content:space-between;padding:20px 24px">
  <span class="display" style="font-size:20px;color:#{p}">{_esc(brand)}</span>
  <a class="btn" href="#cta">{_esc(cta)}</a>
</header>
<main>
  <section class="hero">
    <div class="wrap" style="padding:96px 24px">
      <span class="eyebrow">For {_esc(audience)}</span>
      <h1 class="display" style="font-size:clamp(40px,7vw,72px);max-width:16ch;margin:14px 0">{_esc(brand)} helps {_esc(audience)} {_esc(goal)}</h1>
      <p class="muted" style="max-width:56ch;font-size:19px;margin-bottom:28px">{_esc(brand)} turns attention into action with a clear, honest offer and a single focused next step.</p>
      <a class="btn" href="#cta">{_esc(cta)}</a>
    </div>
  </section>
  <section class="wrap">
    <span class="eyebrow">Why it works</span>
    <h2>Built around one outcome</h2>
    <div style="display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:24px">
      <div class="card"><h3 class="display" style="font-size:20px;margin-bottom:8px">Clarity</h3><p class="muted">One message, one audience, one goal — no competing calls to action.</p></div>
      <div class="card"><h3 class="display" style="font-size:20px;margin-bottom:8px">Trust</h3><p class="muted">Honest proof and a clean, professional presentation your visitors recognise.</p></div>
      <div class="card"><h3 class="display" style="font-size:20px;margin-bottom:8px">Momentum</h3><p class="muted">A single high-contrast path from first glance to {_esc(cta_lower)}.</p></div>
    </div>
  </section>
  {proof_block}
  <section id="cta" class="wrap" style="text-align:center;background:#{sf};border-radius:28px;padding:64px 24px;margin:40px auto">
    <h2>Ready to begin?</h2>
    <p class="muted" style="max-width:52ch;margin:0 auto 24px">{_esc(brand)} is ready for {_esc(audience)}. {_esc(cta)} and move forward with confidence.</p>
    <a class="btn" href="#">{_esc(cta)}</a>
  </section>
</main>
<footer class="wrap" style="padding:32px 24px;opacity:.7;font-size:14px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px">
  <span>&copy; {_esc(brand)}</span>
  <span>Made with Getszy</span>
</footer>
{script}
</body>
</html>'''
    return html


class ProfessionalCompositionError(RuntimeError):
    """Raised when the managed builder cannot produce a reviewable private draft."""


def _sanitize(html: str) -> str:
    html = re.sub(r'(file://|javascript:eval\()', '', html, flags=re.IGNORECASE)
    return html


async def plan_site(prompt: str, session_id: str = 'builder') -> dict:
    """Agent 1: Plan the site structure."""
    raw = await professional_builder_completion(
        system=PLANNER_PROMPT,
        user=f"User request: {prompt}",
        session_id=f'{session_id}-plan',
        temperature=0.35,
    )
    plan = _extract_json(raw)
    if not plan:
        plan = {
            'site_type': 'landing',
            'sections': ['hero', 'benefits', 'how_it_works', 'cta', 'footer'],
            'color_scheme': 'cool',
            'typography': 'modern',
            'tone': 'professional',
            'key_message': prompt[:100],
            'target_audience': 'general audience',
        }
    logger.info(f'Builder plan: {plan.get("site_type", "unknown")} with {len(plan.get("sections", []))} sections')
    return plan


async def design_site(plan: dict, prompt: str, session_id: str = 'builder') -> dict:
    """Agent 2: Create design brief from plan."""
    raw = await professional_builder_completion(
        system=DESIGNER_PROMPT,
        user=f"Original request: {prompt}\n\nSite plan:\n{json.dumps(plan, indent=2)}",
        session_id=f'{session_id}-design',
        temperature=0.45,
    )
    design = _extract_json(raw)
    if not design:
        design = {
            'palette': {'primary': '#1e8e8e', 'secondary': '#2563eb', 'accent': '#f59e0b', 'bg': '#ffffff', 'text': '#1f2937'},
            'fonts': {'display': 'Inter', 'body': 'Inter'},
            'sections': [{'name': s, 'layout': 'centered', 'description': s, 'visual_style': 'solid', 'elements': []} for s in plan.get('sections', ['hero', 'features', 'footer'])],
            'animations': ['fade-in', 'slide-up'],
        }
    logger.info(f'Builder design: {design.get("palette", {}).get("primary", "?")} primary')
    return design


async def code_site(prompt: str, plan: dict, design: dict, session_id: str = 'builder') -> str:
    """Agent 3: Generate the actual HTML."""
    context = (
        f"Original request: {prompt}\n\n"
        f"Site plan:\n{json.dumps(plan, indent=2)}\n\n"
        f"Design brief:\n{json.dumps(design, indent=2)}\n\n"
        "Now generate the complete HTML website following this plan and design exactly."
    )
    raw = await professional_builder_completion(
        system=CODER_PROMPT,
        user=context,
        session_id=f'{session_id}-code',
        temperature=0.48,
        max_tokens=8000,
    )
    html = _repair_html(_extract_html(raw))
    if not html.lower().startswith('<!doctype html') or len(html) < 4000:
        raise ProfessionalCompositionError('The managed composition engine did not return a complete professional private draft. No generic fallback page was created.')
    logger.info(f'Builder coded: {len(html)} chars')
    return html


async def review_site(html: str, session_id: str = 'builder', quality_feedback: list[str] | None = None) -> str:
    """Agent 4: Review and fix issues, including deterministic preflight feedback."""
    feedback = ""
    if quality_feedback:
        feedback = "\n\nDETERMINISTIC PREFLIGHT FAILURES TO FIX:\n- " + "\n- ".join(quality_feedback)
    try:
        raw = await professional_builder_completion(
            system=REVIEWER_PROMPT,
            user=f"Review and fix this HTML:{feedback}\n\n{html}",
            session_id=f'{session_id}-review',
            temperature=0.25,
            max_tokens=8000,
        )
        reviewed = _extract_html(raw)
        if reviewed.lower().startswith('<!doctype html') and len(reviewed) > len(html) * 0.5:
            logger.info(f'Builder reviewed: {len(reviewed)} chars (was {len(html)})')
            return reviewed
    except Exception as e:
        logger.warning(f'Builder review failed, using original: {e}')
    return html


async def refine_element(html: str, selector: str, instruction: str, session_id: str = 'builder') -> str:
    """Refine a specific section/element of the site."""
    raw = await professional_builder_completion(
        system=ELEMENT_REFINE_PROMPT,
        user=(
            f"TARGET: {selector}\n"
            f"INSTRUCTION: {instruction}\n\n"
            f"CURRENT HTML:\n\n{html}"
        ),
        session_id=f'{session_id}-refine',
        temperature=0.5,
        max_tokens=8000,
    )
    refined = _repair_html(_extract_html(raw))
    if refined.lower().startswith('<!doctype html') and len(refined) > len(html) * 0.5:
        return refined
    return html


# ── Full Pipeline ──────────────────────────────────────────────────────────────

async def compose_site_fast(prompt: str, brief: dict | None = None, session_id: str = 'builder', style_profile: str | None = None) -> str:
    """Create a premium customer draft in one managed quality-ladder call (no wait).

    Runs a small design-brief step first (DESIGNER_PROMPT) so the composer does
    not invent a color system and copy in a single shot, then composes the draft
    with FAST_COMPOSITION_PROMPT. The design step is best-effort and never fails
    the whole build — on any failure we fall back to the single-call composition.
    """
    brief = brief or {}
    confirmed = {key: value for key, value in brief.items() if value not in (None, '', [])}

    design_brief = None
    try:
        design_raw = await professional_builder_completion(
            system=DESIGNER_PROMPT,
            user=(
                f"Original request: {prompt}\n\n"
                f"Verified customer brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}"
            ),
            session_id=f'{session_id}-design-fast',
            temperature=0.45,
            max_tokens=900,
        )
        design_brief = _extract_json(design_raw)
    except Exception as exc:  # pragma: no cover - design step is a quality upgrade only
        logger.warning('Fast design-brief call failed (%s); falling back to single-call composition.', exc)

    style_directive = ""
    if style_profile:
        style_directive = (
            f"\n\nEXPLICIT STYLE DIRECTION (override defaults but stay brand-faithful): "
            f"{style_profile.strip()}\n"
        )
    design_block = ""
    if design_brief:
        design_block = (
            f"\n\nDESIGN BRIEF:\n{json.dumps(design_brief, ensure_ascii=False, indent=2)}\n"
        )
    context = (
        f"CUSTOMER REQUEST:\n{prompt}\n\n"
        f"VERIFIED CUSTOMER BRIEF:\n{json.dumps(confirmed, ensure_ascii=False, indent=2)}\n"
        f"{design_block}{style_directive}\n"
        "Compose the complete private draft now."
    )
    raw = await professional_builder_completion(
        system=FAST_COMPOSITION_PROMPT,
        user=context,
        session_id=f'{session_id}-fast-compose',
        temperature=0.38,
        max_tokens=6000,
    )
    html = _repair_html(_extract_html(raw))
    if not html.lower().startswith('<!doctype html'):
        raise ProfessionalCompositionError('The fast managed composer did not return a complete reviewable private draft.')

    quality = evaluate_landing_page_quality(html, confirmed)
    if quality['status'] == 'needs_work':
        fix_context = (
            context
            + "\n\nThis draft failed the automated premium-quality preflight. Correct ONLY these issues, "
            + "then output the complete corrected HTML document:\n"
            + "\n".join(f"- {item}" for item in quality.get('next_actions', []))
        )
        try:
            raw2 = await professional_builder_completion(
                system=FAST_COMPOSITION_PROMPT,
                user=fix_context,
                session_id=f'{session_id}-fast-compose-fix',
                temperature=0.3,
                max_tokens=6000,
            )
            html2 = _repair_html(_extract_html(raw2))
            if html2.lower().startswith('<!doctype html'):
                q2 = evaluate_landing_page_quality(html2, confirmed)
                if q2['required_checks_passed'] >= quality['required_checks_passed']:
                    html = html2
                    quality = q2
        except Exception as exc:  # pragma: no cover - self-heal is best-effort
            logger.warning('Premium quality self-heal failed; keeping first draft: %s', exc)

    logger.info('Fast professional composition completed: %s chars (quality=%s)', len(html), quality.get('status'))
    return _sanitize(html)


async def polish_site_async(html: str, brief: dict | None = None, session_id: str = 'builder') -> str:
    """Background polish pass: upgrade the instant draft (visual refinement, stricter
    accessibility, tighter copy) without changing product truth. Runs after the
    customer already received the instant result, so there is no wait.
    """
    brief = brief or {}
    confirmed = {key: value for key, value in brief.items() if value not in (None, '', [])}
    context = (
        f"VERIFIED CUSTOMER BRIEF:\n{json.dumps(confirmed, ensure_ascii=False, indent=2)}\n\n"
        "Refine the provided draft into a more premium, polished result. Keep all product truth, "
        "sections, and the primary CTA. Improve visual hierarchy, spacing, typography, and "
        "accessibility only. Do not add testimonials, prices, or claims that are not in the brief."
    )
    try:
        raw = await professional_builder_completion(
            system=REVIEWER_PROMPT,
            user=f"Polish this HTML (do not invent proof or claims):\n\n{html}\n\n{context}",
            session_id=f'{session_id}-polish',
            temperature=0.25,
            max_tokens=8000,
        )
    except Exception as exc:  # pragma: no cover - network/provider failure must not crash background task
        logger.warning('Background polish failed, keeping instant draft: %s', exc)
        return html
    polished = _repair_html(_extract_html(raw))
    if polished.lower().startswith('<!doctype html') and len(polished) > len(html) * 0.6:
        logger.info('Background polish completed: %s chars (was %s)', len(polished), len(html))
        return _sanitize(polished)
    return html


async def build_site(prompt: str, session_id: str = 'builder', brief: dict | None = None) -> str:
    """Run the managed professional pipeline: plan → design → code → review.

    The customer brief is supplied as project truth. It is deliberately passed to
    every stage so a generic prompt cannot override the confirmed offer, audience,
    CTA, visual direction, or evidence policy.
    """
    brief = brief or {}
    confirmed = {key: value for key, value in brief.items() if value not in (None, '', [])}
    enriched_prompt = f"{prompt}\n\nCONFIRMED CUSTOMER BRIEF (treat as product truth):\n{json.dumps(confirmed, ensure_ascii=False)}"
    plan = await plan_site(enriched_prompt, session_id)
    design = await design_site(plan, enriched_prompt, session_id)
    html = await code_site(enriched_prompt, plan, design, session_id)
    html = _repair_html(await review_site(html, session_id))
    return _sanitize(html)

_DESIGN_BRIEF_TIMEOUT_SEC = 20.0

async def design_brief_fast(prompt: str, brief: dict | None = None, session_id: str = 'builder') -> dict | None:
    """One extra, small LLM call before fast composition: ask for an explicit
    palette/fonts/section-layout brief so the coder isn't inventing copy AND a
    color system in the same single shot. Reuses DESIGNER_PROMPT from the full
    build_site pipeline (adapted to run directly off the prompt/brief, since the
    fast path deliberately skips the plan_site step that build_site feeds it).

    Never raises. Returns None on any failure, bad JSON, or timeout, so callers
    can fall back to the pre-existing single-call behavior rather than fail an
    otherwise-working build over a step that's only a quality upgrade.
    """
    brief = brief or {}
    context = (
        f"Original request: {prompt}\n\n"
        f"Verified customer brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}"
    )
    try:
        raw = await asyncio.wait_for(
            professional_builder_completion(
                system=DESIGNER_PROMPT,
                user=context,
                session_id=f'{session_id}-design-fast',
                temperature=0.45,
                max_tokens=900,
            ),
            timeout=_DESIGN_BRIEF_TIMEOUT_SEC,
        )
    except Exception as e:
        logger.warning('Fast design-brief call failed (%s); falling back to single-call composition.', e)
        return None
    design = _extract_json(raw)
    if not design:
        logger.warning('Fast design-brief call returned no parseable JSON; falling back to single-call composition.')
    return design


