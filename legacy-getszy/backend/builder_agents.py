import asyncio
"""Builder Agents — Multi-agent pipeline for website generation.

Pipeline: Planner → Designer → Coder → Reviewer
Each agent specializes in one aspect, producing better output than a single monolithic LLM call.

This module integrates with the Agent Factory reliability layer:
- resource_admission: memory-aware execution gate
- task_limits: per-task resource limits
- failure_isolation: timeout, cancellation, exception boundaries
- attempt_ledger: structured evidence for repair loops
- bounded_output: prevents unbounded string accumulation
- reviewer: verification of task results
"""
import re
import json
import html as _html
import logging
import uuid
import time
from llm_provider import professional_builder_completion
from builder_quality import evaluate_landing_page_quality
from resource_admission import admit_task, get_degraded_config, AdmissionDecision
from task_limits import (
    create_tracker, remove_tracker, LimitTracker, TaskLimits,
    MAX_REPAIR_ATTEMPTS, MAX_TOOL_ROUNDS, DEFAULT_EXECUTION_TIMEOUT,
)
from failure_isolation import ExceptionBoundary, FailureType, FailureRecord, child_failure_to_evidence
from attempt_ledger import (
    AttemptLedger, AttemptOutcome, StrategyType,
    get_ledger, remove_ledger,
)
from task_limits import MAX_REPAIR_ATTEMPTS as _FACTORY_MAX_REPAIR
from bounded_output import bounded_llm_output, bounded_html_output, BoundedResult
from reviewer import review_task_result, ReviewVerdict

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
3. Put ALL styling in a SINGLE inline <style> block in the <head> — a real design system (CSS custom-property tokens, a fluid clamp() type scale, shadows, gradients, rounded cards, transitions). The page MUST render fully styled with NO network access — do NOT use Tailwind, any external CSS framework, or a styling CDN.
4. Fonts: use a system font stack, or at most ONE Google Fonts <link> for premium typography (e.g. Inter, Plus Jakarta Sans, Space Grotesk).
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

OUTPUT: ONLY one complete HTML document, beginning with <!DOCTYPE html> and ending with </html>. Put ALL styling in a SINGLE inline <style> block in the <head> — a real design system with CSS custom-property tokens (color/space/radius), a fluid type scale using clamp(), shadows, gradients, rounded surfaces and smooth transitions. The page MUST render fully styled with NO network access: do NOT use Tailwind, any external CSS framework, or a styling CDN. Fonts: a system font stack, or at most ONE Google Fonts <link>.

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
    {'primary': '0ea5e9', 'accent': '8b5cf6', 'bg': 'ffffff', 'text': '0f172a', 'surface': 'f0ffff'},
]

# Vertical families give the deterministic fallback real variety so a customer
# whose LLM call fails still gets a page tuned to their business type — not a
# one-size-fits-all shell. Copy stays honest (no invented testimonials/promises).
_VERTICAL_LABELS = {
    'fitness': 'Fitness', 'salon': 'Beauty & Wellness', 'restaurant': 'Hospitality',
    'education': 'Education', 'consultant': 'Advisory', 'ecommerce': 'Retail',
    'service': 'Local Service', 'portfolio': 'Studio', 'saas': 'Software',
    'health': 'Wellness', 'default': 'Business',
}
# Order matters: the first matching family wins, so more specific families come
# before broader ones (fitness/salon before the generic health family).
_VERTICAL_RULES = [
    ('fitness', ('gym', 'fitness', 'workout', 'crossfit', 'strength', 'personal train', 'bootcamp', 'pilates', 'cycling', 'martial', 'boxing', 'athletic')),
    ('salon', ('salon', 'spa', 'beauty', 'hair', 'nail', 'makeup', 'barber', 'skincare', 'lash', 'brow', 'aesthetic', 'grooming')),
    ('restaurant', ('restaurant', 'cafe', 'coffee', 'bakery', 'bar', 'food', 'pizza', 'dining', 'menu', 'kitchen', 'bistro', 'catering')),
    ('education', ('academy', 'school', 'course', 'tutor', 'coaching class', 'education', 'learning', 'institute', 'classes', 'college', 'training center')),
    ('consultant', ('consultant', 'consulting', 'coach', 'advisory', 'mentor', 'strategist', 'accountant', 'lawyer', 'advisor')),
    ('ecommerce', ('shop', 'store', 'ecommerce', 'e-commerce', 'retail', 'product', 'fashion', 'boutique', 'sell', 'marketplace', 'apparel', 'jewel')),
    ('service', ('plumb', 'electric', 'cleaning', 'repair', 'contractor', 'handyman', 'moving', 'landscap', 'roofing', 'pest', 'locksmith', 'detailing')),
    ('portfolio', ('portfolio', 'agency', 'freelance', 'designer', 'photographer', 'artist', 'studio', 'creative', 'illustrator', 'creator', 'videographer')),
    ('saas', ('saas', 'software', 'platform', 'app', 'tool', 'startup', 'ai', 'api', 'tech', 'automation', 'dashboard')),
    ('health', ('health', 'wellness', 'clinic', 'yoga', 'therapy', 'medical', 'nutrition', 'dental', 'physio', 'counsel')),
]
_VERTICAL_SECTIONS = {
    'saas': [
        ('Product', 'What you ship', [
            ('Onboarding', 'A guided first run that delivers value in minutes, not weeks.'),
            ('Automation', 'Repeatable workflows that remove the busywork your team dislikes.'),
            ('Insights', 'Clear dashboards so the next decision is obvious.'),
        ]),
        ('Integrations', 'Works where you already work', [
            ('API', 'A clean, documented API for the systems you rely on.'),
            ('Webhooks', 'Real-time events keep every connected tool in sync.'),
            ('Teams', 'Roles and permissions that scale with you.'),
        ]),
    ],
    'restaurant': [
        ('Menu', 'Tastes worth the trip', [
            ('Starters', 'Small plates designed to share and surprise.'),
            ('Mains', 'Considered dishes built from local, seasonal ingredients.'),
            ('Desserts', 'A short, confident list worth saving room for.'),
        ]),
        ('Visit', 'Find us and book', [
            ('Hours', 'Open daily for lunch and dinner service.'),
            ('Location', 'A calm, easy-to-reach room with seating inside and out.'),
            ('Reserve', 'Book a table online in a few taps.'),
        ]),
    ],
    'portfolio': [
        ('Work', 'Selected projects', [
            ('Brand', 'Identity systems with a clear point of view.'),
            ('Product', 'Interfaces that feel effortless to use.'),
            ('Motion', 'Detail-oriented motion that earns attention.'),
        ]),
        ('About', 'The person behind it', [
            ('Approach', 'Strategy first, then craft.'),
            ('Clients', 'Founders, teams and labels who trusted the work.'),
            ('Recognition', 'Awards and features worth mentioning.'),
        ]),
    ],
    'ecommerce': [
        ('Shop', 'Collections', [
            ('New', 'The latest drop, curated and in stock.'),
            ('Bestsellers', 'The pieces customers return for.'),
            ('Essentials', 'Quiet staples that complete the look.'),
        ]),
        ('Why us', 'Reasons to choose us', [
            ('Quality', 'Materials and construction we stand behind.'),
            ('Shipping', 'Fast, tracked delivery with clear updates.'),
            ('Support', 'Real help from people who know the product.'),
        ]),
    ],
    'health': [
        ('Approach', 'How we help', [
            ('Assessment', 'We start with where you are, not a template.'),
            ('Plan', 'A realistic path you can actually follow.'),
            ('Progress', 'Honest check-ins that keep momentum.'),
        ]),
        ('Care', 'What to expect', [
            ('Sessions', 'Focused time with someone who listens.'),
            ('Resources', 'Practical tools to use between visits.'),
            ('Community', 'People walking the same path.'),
        ]),
    ],
}


def _vertical_for(brief: dict, prompt: str) -> str:
    text = ' '.join([
        str(brief.get('vertical', '') or ''),
        str(brief.get('industry', '') or ''),
        str(brief.get('business_type', '') or ''),
        str(brief.get('category', '') or ''),
        prompt,
    ]).lower()
    for vertical, keywords in _VERTICAL_RULES:
        if any(k in text for k in keywords):
            return vertical
    return 'default'


# ── business-aware composition playbook ─────────────────────────────────────
# Per family: navigation, a supporting hero line, two alternating feature rows,
# a services block, a numbered process, and an FAQ. Copy is honest and generic-
# but-tailored — it never states unverified facts (counts, awards, ratings,
# hours, addresses, testimonials). {brand}/{audience} are filled at render time.
_PLAY = {
    'fitness': {
        'nav': ['Programs', 'Coaching', 'Process', 'FAQ'],
        'hero': 'Structured training, real coaching and a room that actually keeps you coming back.',
        'rows': [
            ('Programs', 'Training built around your goal', 'Strength, conditioning and mobility programmed properly — so every session moves you forward instead of just tiring you out.',
             ['Clear progression, not random workouts', 'Scalable for every level', 'Coaches who watch your form']),
            ('Coaching', 'People who actually coach', 'Attentive coaching that adjusts the plan to your body, your schedule and your goal — the difference between a gym and a result.',
             ['Personalised adjustments', 'Honest, supportive feedback', 'A community that shows up']),
        ],
        'services': ('What you can train', 'Choose your focus', [
            ('Strength', 'Barbell and functional strength with real progression.'),
            ('Conditioning', 'Efficient sessions that build a genuine engine.'),
            ('Mobility', 'Move well and stay injury-free for the long run.'),
            ('Personal training', 'One-to-one coaching tuned entirely to you.')]),
        'process': ('How to start', 'Three simple steps', [
            ('Book an intro', 'Tell us your goal and where you are today.'),
            ('Get your plan', 'A realistic program you can actually follow.'),
            ('Train and progress', 'Show up, get coached, see the change.')]),
        'faq': [('Do I need to be fit to start?', 'No. Every program scales to your current level and progresses from there.'),
                ('How often should I train?', 'Most members train two to four times a week; we help you set a realistic rhythm.'),
                ('Is coaching included?', 'Yes — coaching and form guidance are part of every session.')],
    },
    'salon': {
        'nav': ['Services', 'Experience', 'Process', 'FAQ'],
        'hero': 'A calm space, skilled hands and a finish you will actually want to show off.',
        'rows': [
            ('Craft', 'Considered, not rushed', 'Time taken to understand what suits you, then execute it with care. You leave looking like the best version of yourself, not a trend you did not ask for.',
             ['A proper consultation first', 'Skilled, attentive stylists', 'Products chosen for your hair and skin']),
            ('Experience', 'The visit should feel good too', 'A relaxed, unhurried atmosphere from the moment you walk in — because how it feels matters as much as how it looks.',
             ['A calm, welcoming room', 'Honest advice, never a hard sell', 'Easy online booking']),
        ],
        'services': ('What we offer', 'Services', [
            ('Hair', 'Cuts, colour and styling tailored to you.'),
            ('Skin', 'Treatments that leave skin genuinely healthier.'),
            ('Nails', 'Precise, long-lasting and beautifully finished.'),
            ('Occasion', 'Looks prepared for the days that matter.')]),
        'process': ('How it works', 'From booking to finish', [
            ('Book online', 'Pick a service and a time that suits you.'),
            ('Consult', 'We understand the look you are after.'),
            ('Enjoy the result', 'Leave polished, relaxed and ready.')]),
        'faq': [('Do I need to book ahead?', 'Booking ahead is recommended so we can give you an unhurried appointment.'),
                ('Can I get a consultation first?', 'Yes — every appointment begins with a short consultation.'),
                ('What products do you use?', 'We choose professional products suited to your hair and skin.')],
    },
    'restaurant': {
        'nav': ['Menu', 'Atmosphere', 'Visit', 'FAQ'],
        'hero': 'Honest cooking, a warm room and a table worth coming back to.',
        'rows': [
            ('Kitchen', 'Cooked with care', 'A short, confident menu built from good ingredients and treated with respect. Fewer dishes, done properly — the way food should be.',
             ['Fresh, seasonal ingredients', 'A menu that changes with what is good', 'Options for every table']),
            ('Room', 'A place that feels right', 'A warm, easy atmosphere for a quick lunch, a long dinner or something in between — comfortable, unhurried and genuinely welcoming.',
             ['Comfortable seating', 'Friendly, attentive service', 'Easy to reach and easy to enjoy']),
        ],
        'services': ('On the menu', 'What to expect', [
            ('Starters', 'Small plates made to share and enjoy.'),
            ('Mains', 'Considered dishes built on good produce.'),
            ('Desserts', 'A short list worth saving room for.'),
            ('Drinks', 'A thoughtful selection to match the food.')]),
        'process': ('Plan your visit', 'Simple and welcoming', [
            ('Choose a time', 'Drop in or reserve a table online.'),
            ('Settle in', 'Relax into a warm, easy room.'),
            ('Enjoy', 'Eat well and leave looking forward to next time.')]),
        'faq': [('Do you take reservations?', 'Yes — you can reserve a table online in a few taps.'),
                ('Are there options for dietary needs?', 'We do our best to accommodate; just let us know when you book.'),
                ('Is it good for groups?', 'Yes — get in touch and we will help arrange the table.')],
    },
    'consultant': {
        'nav': ['Services', 'Approach', 'Process', 'FAQ'],
        'hero': 'Clear thinking, practical advice and work that actually moves the needle.',
        'rows': [
            ('Focus', 'Advice you can act on', 'No jargon and no filler — a sharp read of your situation and a concrete plan you can put to work this week.',
             ['A clear diagnosis first', 'Practical, prioritised recommendations', 'Support through the follow-through']),
            ('Partnership', 'In it with you', 'Not a report that gathers dust — a working partnership focused on the outcome you actually care about.',
             ['Straight, honest guidance', 'Tailored to your business, not a template', 'Measured by results, not slides']),
        ],
        'services': ('How I can help', 'Services', [
            ('Strategy', 'A clear direction and the priorities that matter.'),
            ('Advisory', 'A trusted sounding board when it counts.'),
            ('Execution', 'Hands-on help to make the plan real.'),
            ('Review', 'An honest audit of where you are today.')]),
        'process': ('How we work', 'A simple engagement', [
            ('Discovery', 'Understand your goal and your constraints.'),
            ('Plan', 'Agree a focused, practical way forward.'),
            ('Deliver', 'Execute and review against real outcomes.')]),
        'faq': [('How do engagements start?', 'With a short discovery conversation to understand your goal — no obligation.'),
                ('Do you work remotely?', 'Yes — engagements are run in whatever way suits you best.'),
                ('How is success measured?', 'Against the real outcomes we agree at the start, not activity.')],
    },
    'ecommerce': {
        'nav': ['Shop', 'Why us', 'Process', 'FAQ'],
        'hero': 'Pieces worth keeping, presented properly and delivered without the fuss.',
        'rows': [
            ('Product', 'Made to last', 'Considered materials and honest construction — quiet quality you can feel, not a trend you will regret next season.',
             ['Materials we stand behind', 'Details that hold up', 'Designed to be worn, not stored']),
            ('Service', 'Buying should be easy', 'Clear information, fast tracked delivery and real help when you need it — the parts of shopping online that usually go wrong, done right.',
             ['Fast, tracked delivery', 'Simple, fair returns', 'Support from people who know the product']),
        ],
        'services': ('The collection', 'Explore', [
            ('New', 'The latest pieces, curated and in stock.'),
            ('Bestsellers', 'The pieces customers return for.'),
            ('Essentials', 'Quiet staples that complete the look.'),
            ('Gifting', 'Easy choices for the people who matter.')]),
        'process': ('How it works', 'From cart to doorstep', [
            ('Browse', 'Find the pieces that are right for you.'),
            ('Checkout', 'A quick, secure and simple checkout.'),
            ('Delivered', 'Fast, tracked shipping to your door.')]),
        'faq': [('What is your returns policy?', 'Simple, fair returns — if it is not right, we make it easy to put right.'),
                ('How fast is delivery?', 'Orders ship quickly with tracking so you always know where it is.'),
                ('Do you ship widely?', 'Yes — delivery options are shown clearly at checkout.')],
    },
    'service': {
        'nav': ['Services', 'Why us', 'Process', 'FAQ'],
        'hero': 'Reliable work, fair pricing and a job done properly the first time.',
        'rows': [
            ('Reliability', 'Turn up and do it right', 'On time, tidy and straightforward — the basics most people wish they could count on, done every single visit.',
             ['Punctual and dependable', 'Clean, careful work', 'Clear pricing, no surprises']),
            ('Trust', 'Treated like it is our own', 'Honest advice about what actually needs doing — and what does not — from people who take pride in the work.',
             ['Upfront, honest quotes', 'Respect for your home or site', 'Work we stand behind']),
        ],
        'services': ('What we do', 'Services', [
            ('Callouts', 'Prompt help when something needs fixing.'),
            ('Installations', 'Done properly, checked and tidy.'),
            ('Maintenance', 'Keep things running before they fail.'),
            ('Advice', 'An honest opinion, obligation-free.')]),
        'process': ('How it works', 'Easy from the first call', [
            ('Get in touch', 'Tell us what you need — we listen first.'),
            ('Clear quote', 'A fair, upfront price with no surprises.'),
            ('Job done', 'Work completed properly and left tidy.')]),
        'faq': [('Do you give free quotes?', 'Yes — we provide a clear, upfront quote before any work begins.'),
                ('Are you insured?', 'We carry appropriate cover; ask us for details when you get in touch.'),
                ('How soon can you come?', 'Get in touch and we will give you the earliest realistic time.')],
    },
}


def _play(vertical: str, vlabel: str) -> dict:
    """Content for a family, falling back to a strong generic business playbook."""
    if vertical in _PLAY:
        return _PLAY[vertical]
    return {
        'nav': ['What we do', 'Why us', 'Process', 'FAQ'],
        'hero': 'A clear, honest offer and a single focused next step for {audience}.',
        'rows': [
            ('What we do', 'Focused on one outcome', 'One message, one audience and one goal — a clean, professional presentation that makes the next step obvious.',
             ['A clear, single-minded offer', 'A professional, trustworthy presentation', 'One confident call to action']),
            ('Why it works', 'Built to convert, honestly', 'No noise and no invented claims — just a considered layout that earns attention and guides {audience} to act.',
             ['Honest, review-ready copy', 'A considered visual system', 'Designed to move visitors forward']),
        ],
        'services': ('What we offer', 'How we help', [
            ('Clarity', 'A message {audience} understand in seconds.'),
            ('Quality', 'A presentation that looks genuinely professional.'),
            ('Momentum', 'A single, high-contrast path to act.'),
            ('Trust', 'Honest content, never invented proof.')]),
        'process': ('How it works', 'Three simple steps', [
            ('Get in touch', 'Tell us what you need.'),
            ('We prepare', 'A focused plan built around your goal.'),
            ('Move forward', 'A clear next step, ready to go.')]),
        'faq': [('How do we start?', 'Reach out and tell us your goal — we take it from there.'),
                ('Is the content accurate?', 'Yes — we never invent facts, claims or testimonials.'),
                ('Can it be tailored?', 'Absolutely; everything is built around your business.')],
    }


def _fmt(text: str, brand: str, audience: str) -> str:
    return _esc(text.replace('{brand}', brand).replace('{audience}', audience))


def _svg_panel(p: str, a: str, glyph: str) -> str:
    """A self-contained decorative hero/feature visual — pure CSS/SVG, no assets."""
    return (
        f'<div class="panel" aria-hidden="true">'
        f'<svg viewBox="0 0 400 300" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">'
        f'<defs><linearGradient id="g{glyph}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#{p}"/><stop offset="1" stop-color="#{a}"/></linearGradient></defs>'
        f'<rect width="400" height="300" fill="url(#g{glyph})" opacity="0.14"/>'
        f'<circle cx="320" cy="70" r="120" fill="#{a}" opacity="0.10"/>'
        f'<circle cx="90" cy="240" r="90" fill="#{p}" opacity="0.10"/>'
        f'<text x="50%" y="54%" text-anchor="middle" font-size="86" opacity="0.9">{glyph}</text>'
        f'</svg></div>'
    )


_GLYPH = {'fitness': '🏋️', 'salon': '💇', 'restaurant': '🍽️', 'consultant': '📈',
          'ecommerce': '🛍️', 'service': '🛠️', 'education': '🎓', 'portfolio': '🎨',
          'saas': '⚡', 'health': '🌿', 'default': '✦'}


def _compose_sections(vertical, brand, audience, goal, cta, proof_points, p, a):
    """Assemble the body from distinct components — never a repeated card grid.
    Rows alternate direction; sections alternate background for real rhythm."""
    play = _play(vertical, _VERTICAL_LABELS.get(vertical, 'Business'))
    glyph = _GLYPH.get(vertical, '✦')
    out = []

    # alternating feature rows (media + text) — the core layout variety
    for i, (eyebrow, heading, body, bullets) in enumerate(play['rows']):
        flip = ' flip' if i % 2 else ''
        tint = ' tint' if i % 2 else ''
        items = "".join(f'<li>{_fmt(b, brand, audience)}</li>' for b in bullets)
        text = (
            f'<div class="rowtext"><span class="eyebrow">{_fmt(eyebrow, brand, audience)}</span>'
            f'<h2>{_fmt(heading, brand, audience)}</h2>'
            f'<p class="muted">{_fmt(body, brand, audience)}</p>'
            f'<ul class="ticks">{items}</ul></div>'
        )
        out.append(
            f'<section class="section{tint}"><div class="wrap featrow{flip}">'
            f'{text}{_svg_panel(p, a, glyph)}</div></section>'
        )

    # services grid (icon dot + title + desc)
    s_eyebrow, s_head, s_items = play['services']
    cards = "".join(
        f'<div class="scard"><span class="dot"></span>'
        f'<h3>{_fmt(t, brand, audience)}</h3><p class="muted">{_fmt(d, brand, audience)}</p></div>'
        for t, d in s_items
    )
    out.append(
        f'<section id="services" class="section"><div class="wrap">'
        f'<span class="eyebrow">{_esc(s_eyebrow)}</span><h2>{_esc(s_head)}</h2>'
        f'<div class="grid3">{cards}</div></div></section>'
    )

    # numbered process
    pr_eyebrow, pr_head, pr_steps = play['process']
    steps = "".join(
        f'<div class="step"><span class="num">{i+1:02d}</span>'
        f'<h3>{_fmt(t, brand, audience)}</h3><p class="muted">{_fmt(d, brand, audience)}</p></div>'
        for i, (t, d) in enumerate(pr_steps)
    )
    out.append(
        f'<section id="process" class="section tint"><div class="wrap">'
        f'<span class="eyebrow">{_esc(pr_eyebrow)}</span><h2>{_esc(pr_head)}</h2>'
        f'<div class="steps">{steps}</div></div></section>'
    )

    # stats band — ONLY when the customer supplied real proof points (never invented)
    if proof_points:
        stat_items = "".join(f'<div class="stat"><strong>{_esc(str(pt))}</strong></div>' for pt in proof_points[:4])
        out.append(
            f'<section class="section"><div class="wrap"><span class="eyebrow">Proof</span>'
            f'<h2>Results customers can stand behind</h2><div class="stats">{stat_items}</div></div></section>'
        )

    # FAQ accordion (self-contained, no JS)
    faqs = "".join(
        f'<details class="faq"><summary>{_esc(q)}</summary><p class="muted">{_esc(ans)}</p></details>'
        for q, ans in play['faq']
    )
    out.append(
        f'<section id="faq" class="section"><div class="wrap narrow">'
        f'<span class="eyebrow">Questions</span><h2>Good to know</h2>{faqs}</div></section>'
    )
    return "".join(out), play


def _premium_template(prompt: str, brief: dict | None = None) -> str:
    """Deterministic, always-available premium landing page.

    FINAL GUARANTEE: if every LLM provider is unavailable we still return a
    complete, responsive, on-brand, conversion-focused page so the customer
    never sees an error or a blank draft. No external calls, no randomness.
    Picks a vertical family (SaaS / hospitality / studio / retail / wellness /
    default) so the fallback is tuned to the business, not generic.
    """
    brief = brief or {}
    confirmed = {k: v for k, v in brief.items() if v not in (None, '', [])}
    brand = str(confirmed.get('brand_name') or confirmed.get('business_name') or _derive_name(prompt))
    goal = str(confirmed.get('primary_goal') or 'reach more of the right customers')
    cta = str(confirmed.get('primary_cta') or 'Get started')
    audience = str(confirmed.get('audience') or 'your customers')
    proof_points = confirmed.get('proof_points') or []
    cta_lower = (cta or 'get started').lower()
    vertical = _vertical_for(brief, prompt)
    vlabel = _VERTICAL_LABELS.get(vertical, 'Business')

    palette = _PREMIUM_PALETTES[sum(ord(c) for c in brand) % len(_PREMIUM_PALETTES)]
    p, a, bg, tx, sf = palette['primary'], palette['accent'], palette['bg'], palette['text'], palette['surface']
    glyph = _GLYPH.get(vertical, '✦')

    style = (
        ":root{--p:#__P__;--a:#__A__;--bg:#__BG__;--tx:#__TX__;--sf:#__SF__;--maxw:1140px;--r:20px}"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "html{scroll-behavior:smooth}"
        "body{font-family:'Inter',system-ui,sans-serif;color:#__TX__;background:#__BG__;line-height:1.65;-webkit-font-smoothing:antialiased}"
        "img{max-width:100%;display:block}svg{display:block}"
        ".display{font-family:'Plus Jakarta Sans',system-ui,sans-serif;font-weight:800;letter-spacing:-0.02em;line-height:1.05}"
        ".wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}.narrow{max-width:760px}"
        ".muted{opacity:.74}p{max-width:64ch}a{color:inherit}"
        ".eyebrow{display:inline-block;text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:700;color:#__A__;margin-bottom:12px}"
        "h1{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;letter-spacing:-0.03em;line-height:1.04;font-size:clamp(38px,6.2vw,66px)}"
        "h2{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:clamp(26px,3.6vw,40px);letter-spacing:-0.02em;margin-bottom:14px}"
        "h3{font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:19px;margin-bottom:8px}"
        "a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #__A__;outline-offset:3px;border-radius:6px}"
        ".btn{display:inline-flex;align-items:center;gap:8px;background:#__P__;color:#fff;padding:14px 28px;border-radius:999px;font-weight:700;text-decoration:none;transition:transform .2s ease,box-shadow .2s ease;box-shadow:0 10px 24px -8px #__P__66}"
        ".btn:hover{transform:translateY(-2px);box-shadow:0 16px 34px -8px #__P__aa}"
        ".btn.ghost{background:transparent;color:#__P__;box-shadow:none;border:1.5px solid #__P__44}.btn.ghost:hover{background:#__P__0f}"
        ".nav{position:sticky;top:0;z-index:50;background:#__BG__cc;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid #__P__1a}"
        ".nav .row{display:flex;align-items:center;justify-content:space-between;height:68px}"
        ".nav .brand{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:20px;color:#__P__;text-decoration:none}"
        ".nav .links{display:flex;gap:28px;align-items:center}"
        ".nav .links a{text-decoration:none;font-weight:600;font-size:15px;opacity:.8}.nav .links a:hover{opacity:1;color:#__P__}"
        ".section{padding:clamp(56px,8vw,104px) 0}.section.tint{background:#__SF__}"
        ".hero{background:radial-gradient(1100px 560px at 82% -12%,#__A__26,transparent),linear-gradient(160deg,#__P__12,#__A__06);overflow:hidden}"
        ".herogrid{display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center;padding:clamp(56px,8vw,108px) 0}"
        ".hero .sub{font-size:clamp(17px,2vw,20px);margin:18px 0 30px;opacity:.82}.cluster{display:flex;gap:14px;flex-wrap:wrap;align-items:center}"
        ".panel{border-radius:26px;overflow:hidden;aspect-ratio:4/3;background:#__SF__;border:1px solid #__P__1a;box-shadow:0 30px 60px -30px #__P__55}"
        ".featrow{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}.featrow.flip .rowtext{order:2}"
        ".ticks{list-style:none;margin-top:20px;display:grid;gap:12px}.ticks li{position:relative;padding-left:30px;opacity:.86}"
        ".ticks li::before{content:'';position:absolute;left:0;top:7px;width:16px;height:16px;border-radius:50%;background:#__A__;box-shadow:0 0 0 4px #__A__22}"
        ".grid3{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin-top:32px}"
        ".scard{background:#__BG__;border:1px solid #__P__1f;border-radius:var(--r);padding:26px;transition:transform .2s ease,box-shadow .2s ease}"
        ".scard:hover{transform:translateY(-4px);box-shadow:0 22px 44px -22px #__P__66}"
        ".scard .dot{display:block;width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#__P__,#__A__);margin-bottom:16px}"
        ".steps{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:32px}"
        ".step .num{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:42px;color:#__P__;opacity:.26;display:block;margin-bottom:4px}"
        ".stats{display:flex;flex-wrap:wrap;gap:18px;margin-top:28px}.stat{flex:1 1 200px;background:#__BG__;border:1px solid #__P__1f;border-radius:var(--r);padding:24px}"
        ".faq{border-bottom:1px solid #__P__1f}.faq summary{cursor:pointer;list-style:none;font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:18px;padding:18px 0;display:flex;justify-content:space-between;align-items:center;gap:16px}"
        ".faq summary::-webkit-details-marker{display:none}.faq summary::after{content:'+';font-size:26px;color:#__A__;line-height:1}.faq[open] summary::after{content:'\\2013'}.faq p{padding:0 0 18px}"
        ".ctaband{background:linear-gradient(135deg,#__P__,#__A__);color:#fff;border-radius:30px;padding:clamp(48px,7vw,84px) 24px;text-align:center}.ctaband h2{color:#fff}.ctaband p{margin:0 auto 24px}.ctaband .btn{background:#fff;color:#__P__;box-shadow:0 14px 30px -10px rgba(0,0,0,.35)}"
        ".foot{border-top:1px solid #__P__1a;padding:48px 0 28px}.footgrid{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:32px}"
        ".foot .brand{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:20px;color:#__P__}.foot nav{display:grid;gap:10px}.foot nav a{text-decoration:none;opacity:.75;font-size:14px}"
        ".foot .base{margin-top:28px;padding-top:18px;border-top:1px solid #__P__14;display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:13px;opacity:.7}"
        "@media(max-width:860px){.herogrid,.featrow{grid-template-columns:1fr}.featrow.flip .rowtext{order:0}.nav .links{display:none}.panel{aspect-ratio:16/10}.footgrid{grid-template-columns:1fr 1fr}}"
        "@media(max-width:520px){.footgrid{grid-template-columns:1fr}}"
    )
    for k, v in (('__P__', p), ('__A__', a), ('__BG__', bg), ('__TX__', tx), ('__SF__', sf)):
        style = style.replace(k, v)

    body, play = _compose_sections(vertical, brand, audience, goal, cta, proof_points, p, a)
    hero_sub = _fmt(play['hero'], brand, audience)

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
<style>{style}</style>
</head>
<body>
<header class="nav"><div class="wrap row">
  <a class="brand" href="#top">{_esc(brand)}</a>
  <nav class="links"><a href="#services">Services</a><a href="#process">How it works</a><a href="#faq">FAQ</a></nav>
  <a class="btn" href="#cta">{_esc(cta)}</a>
</div></header>
<main id="top">
  <section class="hero"><div class="wrap herogrid">
    <div>
      <span class="eyebrow">For {_esc(audience)} · {_esc(vlabel)}</span>
      <h1>{_esc(brand)} — {_esc(goal)}</h1>
      <p class="sub">{hero_sub}</p>
      <div class="cluster"><a class="btn" href="#cta">{_esc(cta)}</a><a class="btn ghost" href="#services">See what we offer</a></div>
    </div>
    {_svg_panel(p, a, glyph)}
  </div></section>
  {body}
  <section class="section"><div class="wrap"><div class="ctaband">
    <h2>Ready to begin?</h2>
    <p class="muted" style="color:#fff;opacity:.9;max-width:52ch">{_esc(brand)} is ready for {_esc(audience)}. {_esc(cta)} and move forward with confidence.</p>
    <a class="btn" href="#cta" id="cta">{_esc(cta)}</a>
  </div></div></section>
</main>
<footer class="foot"><div class="wrap">
  <div class="footgrid">
    <div><div class="brand">{_esc(brand)}</div><p class="muted" style="margin-top:10px;max-width:34ch">{hero_sub}</p></div>
    <nav><strong style="opacity:.9">Explore</strong><a href="#services">Services</a><a href="#process">How it works</a><a href="#faq">FAQ</a></nav>
    <nav><strong style="opacity:.9">Get started</strong><a href="#cta">{_esc(cta)}</a></nav>
  </div>
  <div class="base"><span>&copy; {_esc(brand)}</span><span>Made with Getszy</span></div>
</div></footer>
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


# ── Agent Factory Reliability Layer ───────────────────────────────────────────

async def build_site_reliable(
    prompt: str,
    session_id: str = 'builder',
    brief: dict | None = None,
) -> dict:
    """Full pipeline with resource admission, limit tracking, failure isolation,
    attempt ledger, bounded output, and reviewer verification.

    Returns a structured result dict with:
    - html: the generated HTML (or None on failure)
    - success: bool
    - verdict: PASS/FAIL/NEEDS_HUMAN
    - admission: admission result
    - ledger: attempt history
    - breaches: any limit breaches
    - evidence: failure evidence if any
    """
    task_id = f'build-{session_id}-{uuid.uuid4().hex[:8]}'
    brief = brief or {}
    confirmed = {k: v for k, v in brief.items() if v not in (None, '', [])}

    # Step 1: Resource admission
    admission = await admit_task('builder_pipeline', task_id=task_id)
    if admission.decision == AdmissionDecision.REJECT:
        logger.warning('Build rejected: %s', admission.reason)
        return {
            'html': None, 'success': False, 'verdict': 'FAIL',
            'admission': admission.to_dict(), 'ledger': {},
            'breaches': [], 'evidence': {'reason': admission.reason},
        }

    # Step 2: Create limit tracker and ledger
    limits = TaskLimits(execution_timeout=DEFAULT_EXECUTION_TIMEOUT)
    if admission.decision == AdmissionDecision.DEGRADE:
        degraded = get_degraded_config('builder_pipeline')
        limits.max_tool_rounds = degraded.get('max_tool_rounds', 3)
        limits.execution_timeout = degraded.get('timeout', 120.0)

    tracker = create_tracker(task_id, agent_id='builder', limits=limits)
    ledger = get_ledger(task_id, max_attempts=_FACTORY_MAX_REPAIR)

    try:
        # Step 3: Run pipeline with failure isolation and attempt tracking
        html = None
        last_error = None
        max_retries = 2 if admission.decision == AdmissionDecision.DEGRADE else 3

        for attempt in range(max_retries):
            if tracker.check_timeout():
                logger.warning('Build %s: timeout on attempt %d', task_id, attempt + 1)
                break

            strategy = ledger.recommend_next_strategy()
            record = ledger.start_attempt(
                strategy=strategy,
                description=f'Pipeline attempt {attempt + 1}',
                agent_id='builder',
            )

            try:
                if attempt > 0 and ledger.last_attempt:
                    # On retry: provide evidence of what failed
                    briefing = ledger.build_briefing()
                    logger.info('Build %s: retry with evidence — rejected strategies: %s',
                                task_id, briefing.get('rejected_strategies', []))

                enriched_prompt = f"{prompt}\n\nCONFIRMED CUSTOMER BRIEF (treat as product truth):\n{json.dumps(confirmed, ensure_ascii=False)}"

                # Plan -> Design -> Code with bounded output
                plan = await plan_site(enriched_prompt, session_id)
                design = await design_site(plan, enriched_prompt, session_id)
                raw_html = await code_site(enriched_prompt, plan, design, session_id)

                # Bound the HTML output
                bounded = bounded_html_output(raw_html)
                if bounded.truncated:
                    logger.warning('Build %s: HTML output truncated (%d -> %d bytes)',
                                   task_id, bounded.original_length, bounded.returned_length)
                    record.metadata['html_truncated'] = True

                html = _repair_html(bounded.content)

                # Step 4: Review with reviewer agent
                review = review_task_result(
                    result=html,
                    task_type='builder',
                    brief=confirmed,
                )
                record.metadata['review'] = review.to_dict()

                if review.verdict == ReviewVerdict.FAIL:
                    failed_checks = [c for c in review.checks if not c.passed and c.severity == 'required']
                    quality_feedback = [c.message for c in failed_checks]
                    html = _repair_html(await review_site(html, session_id, quality_feedback))
                    # Re-review after fix
                    review = review_task_result(html, 'builder', confirmed)
                    record.metadata['post_fix_review'] = review.to_dict()

                ledger.complete_attempt(
                    record,
                    outcome=AttemptOutcome.SUCCESS,
                    observed_output=f'HTML: {len(html)} chars, review: {review.verdict.value}',
                )
                break

            except Exception as e:
                last_error = e
                logger.warning('Build %s: attempt %d failed: %s', task_id, attempt + 1, e)
                ledger.complete_attempt(
                    record,
                    outcome=AttemptOutcome.FAILED,
                    error_message=str(e),
                )
                continue

        # Final result
        if html:
            review = review_task_result(html, 'builder', confirmed)
            return {
                'html': html,
                'success': True,
                'verdict': review.verdict.value,
                'admission': admission.to_dict(),
                'ledger': ledger.summary(),
                'breaches': [b.to_dict() for b in tracker.breaches],
                'evidence': None,
            }
        else:
            return {
                'html': None,
                'success': False,
                'verdict': 'FAIL',
                'admission': admission.to_dict(),
                'ledger': ledger.summary(),
                'breaches': [b.to_dict() for b in tracker.breaches],
                'evidence': {
                    'last_error': str(last_error) if last_error else 'Pipeline produced no output',
                    'attempt_count': ledger.attempt_count,
                },
            }

    finally:
        remove_tracker(task_id)


async def compose_site_reliable(
    prompt: str,
    brief: dict | None = None,
    session_id: str = 'builder',
    style_profile: str | None = None,
) -> dict:
    """Fast composition with resource admission and verification.

    Same structure as build_site_reliable but uses the fast path.
    """
    task_id = f'fast-{session_id}-{uuid.uuid4().hex[:8]}'
    brief = brief or {}
    confirmed = {k: v for k, v in brief.items() if v not in (None, '', [])}

    # Resource admission
    admission = await admit_task('builder_fast', task_id=task_id)
    if admission.decision == AdmissionDecision.REJECT:
        return {
            'html': None, 'success': False, 'verdict': 'FAIL',
            'admission': admission.to_dict(), 'ledger': {},
            'breaches': [], 'evidence': {'reason': admission.reason},
        }

    # Limit tracker
    limits = TaskLimits(execution_timeout=180.0)
    if admission.decision == AdmissionDecision.DEGRADE:
        degraded = get_degraded_config('builder_fast')
        limits.execution_timeout = degraded.get('timeout', 120.0)

    tracker = create_tracker(task_id, agent_id='fast_composer', limits=limits)

    try:
        html = await compose_site_fast(prompt, brief, session_id, style_profile)

        # Verify with reviewer
        review = review_task_result(html, 'builder', confirmed)

        return {
            'html': html,
            'success': True,
            'verdict': review.verdict.value,
            'admission': admission.to_dict(),
            'ledger': {},
            'breaches': [b.to_dict() for b in tracker.breaches],
            'evidence': None,
        }
    except Exception as e:
        return {
            'html': None,
            'success': False,
            'verdict': 'FAIL',
            'admission': admission.to_dict(),
            'ledger': {},
            'breaches': [b.to_dict() for b in tracker.breaches],
            'evidence': {'error': str(e)},
        }
    finally:
        remove_tracker(task_id)


