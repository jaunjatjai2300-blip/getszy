"""Builder Agents — Multi-agent pipeline for website generation.

Pipeline: Planner → Designer → Coder → Reviewer
Each agent specializes in one aspect, producing better output than a single monolithic LLM call.
"""
import re
import json
import logging
from llm_provider import chat_completion

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

CODER_PROMPT = """You are an award-winning front-end designer and copywriter. Generate a stunning, modern, fully-responsive, conversion-focused SINGLE-PAGE WEBSITE.

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
14. Total HTML should be 300-800 lines. Color scheme, fonts, and section layout MUST match the design brief exactly.

START IMMEDIATELY WITH <!DOCTYPE html>. End with </html>. Nothing else."""

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


def _sanitize(html: str) -> str:
    html = re.sub(r'(file://|javascript:eval\()', '', html, flags=re.IGNORECASE)
    return html


async def plan_site(prompt: str, session_id: str = 'builder') -> dict:
    """Agent 1: Plan the site structure."""
    raw = await chat_completion(
        system=PLANNER_PROMPT,
        user=f"User request: {prompt}",
        session_id=f'{session_id}-plan',
        temperature=0.4,
    )
    plan = _extract_json(raw)
    if not plan:
        plan = {
            'site_type': 'landing',
            'sections': ['hero', 'features', 'testimonials', 'cta', 'footer'],
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
    raw = await chat_completion(
        system=DESIGNER_PROMPT,
        user=f"Original request: {prompt}\n\nSite plan:\n{json.dumps(plan, indent=2)}",
        session_id=f'{session_id}-design',
        temperature=0.5,
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
    raw = await chat_completion(
        system=CODER_PROMPT,
        user=context,
        session_id=f'{session_id}-code',
        temperature=0.6,
        max_tokens=8000,
    )
    html = _extract_html(raw)
    if not html.lower().startswith('<!doctype html'):
        # Graceful, valid fallback: a real (if minimal) HTML page — never a raw
        # <pre> dump presented as a "website", and never a silent failure.
        safe = (raw or 'Content could not be generated. Please retry.').replace('<', '&lt;').replace('>', '&gt;')
        html = (
            "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Generated Preview</title>"
            "<script src='https://cdn.tailwindcss.com'></script></head>"
            "<body class='p-8 font-sans bg-white text-gray-900'>"
            f"<div class='prose max-w-3xl mx-auto'>{safe}</div></body></html>"
        )
    logger.info(f'Builder coded: {len(html)} chars')
    return html


async def review_site(html: str, session_id: str = 'builder') -> str:
    """Agent 4: Review and fix issues."""
    try:
        raw = await chat_completion(
            system=REVIEWER_PROMPT,
            user=f"Review and fix this HTML:\n\n{html}",
            session_id=f'{session_id}-review',
            temperature=0.3,
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
    raw = await chat_completion(
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
    refined = _extract_html(raw)
    if refined.lower().startswith('<!doctype html') and len(refined) > len(html) * 0.5:
        return refined
    return html


# ── Full Pipeline ──────────────────────────────────────────────────────────────

async def build_site(prompt: str, session_id: str = 'builder') -> str:
    """Run the full multi-agent pipeline: plan → design → code → review."""
    plan = await plan_site(prompt, session_id)
    design = await design_site(plan, prompt, session_id)
    html = await code_site(prompt, plan, design, session_id)
    html = await review_site(html, session_id)
    return _sanitize(html)
