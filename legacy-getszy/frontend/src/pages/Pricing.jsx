/* eslint-disable react/no-unescaped-entities */
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import { Check, Sparkles, Rocket, ShoppingBag, Package, Shield, Globe, Leaf, Bot, ArrowRight, Loader2, Hand, Info } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const fadeUp = { hidden: { opacity: 0, y: 24 }, visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } } };

function Section({ children, className = "", id = "" }) {
  const ref = useRef(null);
  const inview = useInView(ref, { once: true, margin: "-80px" });
  return (<motion.section ref={ref} id={id} initial="hidden" animate={inview ? "visible" : "hidden"} variants={stagger} className={"gs-section " + className}>{children}</motion.section>);
}

// ── Plan presentation copy ───────────────────────────────────────
// Price, plan name and monthly credit allowance are deliberately NOT hardcoded
// here — they are fetched from /api/billing/pricing (backed by credits.py
// CREDIT_PACKS / CREATOR_PACKS) so this page can never advertise a price the
// payment system does not actually charge. This map holds marketing copy only,
// keyed by the backend plan id.
const PLAN_COPY = {
  creator_pass: {
    tag: "Create & Publish",
    for: "मैं short-form content बनाती हूँ और तेज़ी से publish करना चाहती हूँ।",
    cta: "Start Creating",
    features: ["Everything in Starter", "Guided creation workflows", "Brand Kit", "Private preview", "QR mobile testing", "Quality Gate", "Priority support"],
  },
  lite: {
    tag: "Start Building",
    for: "मैं अपना digital presence बनाना शुरू कर रही हूँ।",
    cta: "Start Building",
    features: ["Everything in Starter", "Guided website / landing-page workflows", "Brand Kit", "Evidence & Claims Vault", "Private preview", "Version history", "Quality Gate"],
  },
  pro: {
    tag: "Build & Grow",
    recommended: true,
    for: "मेरा business बढ़ रहा है और मुझे ज्यादा powerful digital support चाहिए।",
    cta: "Start Growing",
    features: ["Everything in Lite", "Store / advanced digital workflows where supported", "Campaign workflows", "Advanced brand & evidence management", "Growth-oriented Neo workflows", "Priority support", "More project capacity"],
  },
  ultra: {
    tag: "Scale Up",
    for: "मुझे सबसे ज़्यादा capacity और advanced workflows चाहिए।",
    cta: "Go Ultra",
    features: ["Everything in Pro", "Highest monthly usage", "Maximum project capacity", "Advanced campaign & growth workflows", "Priority support"],
  },
};

// Starter and Enterprise stay static on purpose: neither is a recurring Razorpay
// pack, so neither is returned by /api/billing/pricing. Starter is the free
// signup tier, Enterprise is contact-sales with no fixed price.
// NOTE: Starter deliberately does NOT promise introductory credits — credits.py
// is explicit that new users start with 0 credits and no free allowance.
const STATIC_STARTER = {
  id: "starter", name: "Starter", tag: "Start Free", priceLabel: "₹0", period: "", creditsLabel: "",
  for: "मैं Getszy को explore करना चाहती हूँ।",
  features: ["Shop Getszy products", "Wishlist", "Neo basic guidance", "Explore selected digital experiences", "My Getszy account", "Order tracking", "Basic support"],
  cta: "Start Free", to: "/signup",
};
const STATIC_ENTERPRISE = {
  id: "enterprise", name: "Enterprise", tag: "Built for Bigger Teams", priceLabel: "Custom", period: "", creditsLabel: "",
  for: "हमें multiple brands, workflows या managed digital solutions चाहिए।",
  features: ["Multiple brands", "Custom workflows", "Dedicated support", "Advanced security requirements", "Custom usage", "Business integrations where approved", "Custom commercial terms"],
  cta: "Talk to Getszy", to: "/support",
};

// Keyed by plan id (not array position) so the table adapts to whatever plans
// the billing API actually returns.
const COMPARE = [
  { f: "Shop Physical",      v: { starter: "✓", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Neo Guidance",       v: { starter: "✓", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Digital Usage",      v: { starter: "—", creator_pass: "Included", lite: "Included", pro: "Higher", ultra: "Highest", enterprise: "Custom" } },
  { f: "Brand Kit",          v: { starter: "—", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Evidence Vault",     v: { starter: "—", creator_pass: "—", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Private Preview",    v: { starter: "—", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "QR Mobile Test",     v: { starter: "—", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Version History",    v: { starter: "—", creator_pass: "—", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Quality Gate",       v: { starter: "Selected", creator_pass: "✓", lite: "✓", pro: "✓", ultra: "✓", enterprise: "✓" } },
  { f: "Campaign workflows", v: { starter: "—", creator_pass: "—", lite: "Selected", pro: "✓", ultra: "✓", enterprise: "Custom" } },
  { f: "Priority Support",   v: { starter: "—", creator_pass: "✓", lite: "—", pro: "✓", ultra: "✓", enterprise: "Dedicated" } },
  { f: "Multiple Brands",    v: { starter: "—", creator_pass: "—", lite: "—", pro: "—/limited", ultra: "✓", enterprise: "✓" } },
];

const FAQ = [
  { q: "Do I need a subscription to shop?", a: "No. You can shop eligible Getszy physical products without a digital subscription." },
  { q: "Do physical products use Credits?", a: "No. Physical products are purchased in ₹." },
  { q: "What are Getszy Credits?", a: "Credits are usage units for eligible digital AI experiences." },
  { q: "Do Credits expire?", a: "Usage terms follow your active plan. We will always show them clearly before you confirm." },
  { q: "Can I cancel my subscription?", a: "Yes — you can cancel anytime from your account; you keep access until the period ends." },
  { q: "Can I upgrade later?", a: "Yes. Move to a higher plan whenever your work needs more." },
  { q: "Can Neo publish something automatically?", a: "No. Important external actions require your approval." },
  { q: "Can I restore an older version?", a: "Where Version History is supported, yes." },
  { q: "Is Getszy a marketplace?", a: "No. Getszy directly provides the products and digital solutions offered through the platform." },
];

export default function Pricing() {
  const navigate = useNavigate();
  const [paidPlans, setPaidPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState(false);

  // Single source of truth for money: the billing API. Never hardcode prices
  // here — a mismatch between this page and Razorpay is a real customer harm.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/billing/pricing");
        if (cancelled) return;
        const mapped = (data?.plans || [])
          .filter((p) => PLAN_COPY[p.id])
          .sort((a, b) => (a.price_monthly || 0) - (b.price_monthly || 0))
          .map((p) => ({
            id: p.id,
            name: p.name,
            priceLabel: "₹" + Number(p.price_monthly || 0).toLocaleString("en-IN"),
            period: "/ month",
            creditsLabel: p.credits ? `${p.credits} credits / month` : "",
            tagline: p.tagline || "",
            to: "/signup",
            ...PLAN_COPY[p.id],
          }));
        setPaidPlans(mapped);
      } catch (e) {
        if (!cancelled) setPlansError(true);
      } finally {
        if (!cancelled) setPlansLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Starter / Enterprise bookend the paid plans returned by the API.
  const plans = [STATIC_STARTER, ...paidPlans, STATIC_ENTERPRISE];

  return (
    <div className="bg-[#FBF7F2]">
      <section className="relative overflow-hidden">
        <div className="gs-hero-wash absolute inset-0" />
        <div className="gs-noise" />
        <div className="gs-container relative pt-16 pb-12 lg:pt-24 text-center">
          <span className="gs-eyebrow justify-center">Made for women who do it all</span>
          <h1 className="font-display text-[40px] sm:text-6xl lg:text-7xl text-[#1B1A18] mt-4 leading-[1.02]">Choose how you want to <span className="text-[#C58B7A] italic">grow</span> with Getszy.</h1>
          <p className="mt-5 text-lg text-[#5F5951] max-w-2xl mx-auto">Shop what you love. Build what you need. Grow what matters — with one Getszy account.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {[{ icon: ShoppingBag, t: "Shop", s: "Physical products" }, { icon: Rocket, t: "Build & Grow", s: "Digital solutions with Neo" }, { icon: Package, t: "My Getszy", s: "Orders, projects & support" }].map((c) => (
              <div key={c.t} className="flex items-center gap-3 rounded-2xl bg-white border border-[#E7D9CE] px-4 py-3 shadow-[0_10px_30px_rgba(27,26,24,0.06)]">
                <span className="h-9 w-9 grid place-items-center rounded-full bg-[#F3E2C7] text-[#A86B5B]"><c.icon className="h-5 w-5" /></span>
                <div className="text-left"><div className="text-sm font-semibold text-[#1B1A18]">{c.t}</div><div className="text-xs text-[#6B625B]">{c.s}</div></div>
              </div>
            ))}
          </div>
          {/* Billing is monthly-only (see /api/billing/pricing -> interval).
              A yearly toggle used to be shown here computing a x10 annual price,
              but no annual plan exists in the payment system — removed rather
              than advertise a billing cycle a customer cannot actually buy. */}
          <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-white border border-[#E7D9CE] px-5 py-2 text-sm font-semibold text-[#5F5951]">
            <Check className="h-4 w-4 text-[#C58B7A]" />Monthly billing · cancel anytime
          </div>
        </div>
      </section>

      <Section><div className="gs-container">
        <div className="text-center max-w-2xl mx-auto mb-10"><span className="gs-eyebrow justify-center">One Getszy. Two ways to buy.</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">How you pay depends on what you are buying</h2></div>
        <div className="grid md:grid-cols-2 gap-5">
          <div className="rounded-3xl bg-white border border-[#E7D9CE] p-8">
            <div className="flex items-center gap-2 text-[#A86B5B]"><ShoppingBag className="h-5 w-5" /><span className="font-display text-xl text-[#1B1A18]">Physical — Shop</span></div>
            <p className="mt-3 text-[#5F5951]">Buy eligible Getszy products directly in ₹. No subscription required.</p>
            <ul className="mt-5 space-y-2 text-sm text-[#3D3833]">
              {["Curated lifestyle & home products", "Secure checkout (Razorpay)", "Order tracking in My Getszy", "Open to everyone"].map((t) => (<li key={t} className="flex gap-2"><Check className="h-4 w-4 text-[#C58B7A] mt-0.5" />{t}</li>))}
            </ul>
          </div>
          <div className="rounded-3xl bg-white border border-[#E7D9CE] p-8">
            <div className="flex items-center gap-2 text-[#A86B5B]"><Rocket className="h-5 w-5" /><span className="font-display text-xl text-[#1B1A18]">Digital — Build & Grow</span></div>
            <p className="mt-3 text-[#5F5951]">Create guided websites, brands and launches with Neo's help — usage tracked via Credits.</p>
            <ul className="mt-5 space-y-2 text-sm text-[#3D3833]">
              {["Guided creation workflows", "Brand Kit & Evidence Vault", "Private preview & QR testing", "Quality Gate before launch"].map((t) => (<li key={t} className="flex gap-2"><Check className="h-4 w-4 text-[#C58B7A] mt-0.5" />{t}</li>))}
            </ul>
          </div>
        </div>
      </div></Section>
      <Section className="!pt-0"><div className="gs-container">
        <div className="text-center max-w-2xl mx-auto mb-10"><span className="gs-eyebrow justify-center">Plans</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">Pick your plan</h2></div>
        {plansError && (
          <div className="mb-6 rounded-2xl border border-[#E7D9CE] bg-white p-4 text-sm text-[#6B625B] text-center">
            Live plan pricing could not be loaded right now. Showing free and Enterprise options only — please refresh, or <button onClick={() => navigate("/support")} className="underline font-semibold">contact support</button>.
          </div>
        )}
        {plansLoading && (
          <div className="mb-6 flex items-center justify-center gap-2 text-sm text-[#6B625B]">
            <Loader2 className="h-4 w-4 animate-spin" />Loading current plans…
          </div>
        )}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 items-start">
          {plans.map((p) => {
            const recommended = !!p.recommended;
            return (
              <div key={p.id} className={"relative rounded-3xl p-6 flex flex-col " + (recommended ? "bg-[#1B1A18] text-white border border-[#1B1A18] shadow-[0_24px_60px_rgba(27,26,24,0.25)]" : "bg-white text-[#1B1A18] border border-[#E7D9CE]")}>
                {recommended && <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#C58B7A] text-white text-xs font-semibold px-3 py-1">Recommended</span>}
                <div className={"text-xs font-semibold tracking-wide uppercase " + (recommended ? "text-[#E8C9AE]" : "text-[#A86B5B]")}>{p.tag}</div>
                <h3 className="font-display text-2xl mt-1">{p.name}</h3>
                <div className="mt-3 text-3xl font-display">{p.priceLabel}<span className="text-base font-sans">{p.period}</span></div>
                {p.creditsLabel && <div className={"mt-1 text-sm font-semibold " + (recommended ? "text-[#E8C9AE]" : "text-[#A86B5B]")}>{p.creditsLabel}</div>}
                {p.tagline && <div className={"mt-1 text-xs " + (recommended ? "text-white/60" : "text-[#6B625B]")}>{p.tagline}</div>}
                <p className={"mt-3 text-sm italic " + (recommended ? "text-white/70" : "text-[#6B625B]")}>{p.for}</p>
                <button onClick={() => navigate(p.to)} className={"mt-5 w-full rounded-full py-3 text-sm font-semibold inline-flex items-center justify-center gap-2 " + (recommended ? "bg-[#C58B7A] text-white hover:bg-[#b87a68]" : "bg-[#1B1A18] text-white hover:bg-[#2c2a26]")}>{p.cta}<ArrowRight className="h-4 w-4" /></button>
                <ul className={"mt-6 space-y-2 text-sm " + (recommended ? "text-white/85" : "text-[#3D3833]")}>
                  {p.features.map((f) => (<li key={f} className="flex gap-2"><Check className="h-4 w-4 text-[#C58B7A] mt-0.5 shrink-0" />{f}</li>))}
                </ul>
              </div>
            );
          })}
        </div>
      </div></Section>
      <Section className="!pt-0"><div className="gs-container grid md:grid-cols-3 gap-5">
        <div className="rounded-3xl bg-white border border-[#E7D9CE] p-8">
          <Bot className="h-6 w-6 text-[#A86B5B]" />
          <h3 className="font-display text-xl text-[#1B1A18] mt-3">What are Credits?</h3>
          <p className="mt-2 text-sm text-[#5F5951]">Credits are usage units for eligible digital AI experiences. Physical products do not use Credits — they are purchased in ₹. We always show usage terms clearly before you confirm.</p>
        </div>
        <div className="rounded-3xl bg-white border border-[#E7D9CE] p-8">
          <Shield className="h-6 w-6 text-[#A86B5B]" />
          <h3 className="font-display text-xl text-[#1B1A18] mt-3">No surprises</h3>
          <p className="mt-2 text-sm text-[#5F5951]">No hidden marketplace fees. No auto-publishing by Neo. Cancel anytime from your account; keep access until the period ends.</p>
        </div>
        <div className="rounded-3xl bg-white border border-[#E7D9CE] p-8">
          <Hand className="h-6 w-6 text-[#A86B5B]" />
          <h3 className="font-display text-xl text-[#1B1A18] mt-3">Women-first, always</h3>
          <p className="mt-2 text-sm text-[#5F5951]">Getszy is built for women who create and grow. Simple language, honest terms, and tools that respect your time and your work.</p>
        </div>
      </div></Section>
      <Section className="!pt-0"><div className="gs-container">
        <div className="text-center max-w-2xl mx-auto mb-10"><span className="gs-eyebrow justify-center">Why Getszy</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">Built around you</h2></div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[{ icon: Leaf, t: "Simple", s: "Plain language. No jargon." }, { icon: Shield, t: "Safe", s: "You approve every important action." }, { icon: Hand, t: "Honest", s: "Real terms, no fake numbers." }, { icon: Sparkles, t: "Supportive", s: "Neo guides, you decide." }, { icon: Globe, t: "Yours", s: "Your brand, your work, your way." }].map((c) => (
            <div key={c.t} className="rounded-2xl bg-white border border-[#E7D9CE] p-5 text-center">
              <span className="mx-auto h-10 w-10 grid place-items-center rounded-full bg-[#F3E2C7] text-[#A86B5B]"><c.icon className="h-5 w-5" /></span>
              <div className="font-display text-lg text-[#1B1A18] mt-3">{c.t}</div>
              <div className="text-xs text-[#6B625B] mt-1">{c.s}</div>
            </div>
          ))}
        </div>
      </div></Section>

      <Section className="!pt-0"><div className="gs-container">
        <div className="text-center max-w-2xl mx-auto mb-10"><span className="gs-eyebrow justify-center">Compare</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">What's included</h2></div>
        <div className="overflow-x-auto rounded-3xl border border-[#E7D9CE] bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-[#E7D9CE]">
                <th className="p-4 font-display text-[#1B1A18]">Feature</th>
                {plans.map((p) => (<th key={p.id} className="p-4 font-display text-[#1B1A18] text-center">{p.name}</th>))}
              </tr>
            </thead>
            <tbody>
              {COMPARE.map((row) => (
                <tr key={row.f} className="border-b border-[#F1E7DD] last:border-0">
                  <td className="p-4 text-[#3D3833]">{row.f}</td>
                  {plans.map((p) => {
                    const val = row.v[p.id] ?? "—";
                    return (<td key={p.id} className="p-4 text-center text-[#5F5951]">{val === "✓" ? <Check className="h-4 w-4 mx-auto text-[#C58B7A]" /> : val}</td>);
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div></Section>
      <Section className="!pt-0"><div className="gs-container">
        <div className="rounded-3xl bg-[#1B1A18] text-white p-8 sm:p-10">
          <div className="flex items-center gap-2 text-[#E8C9AE]"><Bot className="h-5 w-5" /><span className="font-display text-xl">Not sure which plan? Ask Neo</span></div>
          <p className="mt-2 text-white/70 text-sm">Tell Neo what you want to do. She will suggest the plan that fits — no pressure.</p>
          <NeoHelper />
        </div>
      </div></Section>

      <Section className="!pt-0"><div className="gs-container">
        <div className="text-center max-w-2xl mx-auto mb-10"><span className="gs-eyebrow justify-center">Questions</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">Honest answers</h2></div>
        <div className="grid md:grid-cols-2 gap-4 max-w-4xl mx-auto">
          {FAQ.map((item) => (
            <div key={item.q} className="rounded-2xl bg-white border border-[#E7D9CE] p-6">
              <div className="flex gap-2"><Info className="h-4 w-4 text-[#C58B7A] mt-1 shrink-0" /><h3 className="font-display text-lg text-[#1B1A18]">{item.q}</h3></div>
              <p className="mt-2 text-sm text-[#5F5951]">{item.a}</p>
            </div>
          ))}
        </div>
      </div></Section>

      <section className="relative overflow-hidden"><div className="gs-hero-wash absolute inset-0" /><div className="gs-noise" />
        <div className="gs-container relative text-center py-16">
          <h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18]">Ready when you are.</h2>
          <p className="mt-4 text-[#5F5951] max-w-xl mx-auto">Start free, shop what you love, and let Neo help you build and grow — on your terms.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button onClick={() => navigate("/signup")} className="rounded-full bg-[#1B1A18] text-white px-7 py-3 text-sm font-semibold inline-flex items-center gap-2 hover:bg-[#2c2a26]">Start Free<ArrowRight className="h-4 w-4" /></button>
            <button onClick={() => navigate("/shop")} className="rounded-full border border-[#C58B7A] text-[#A86B5B] px-7 py-3 text-sm font-semibold inline-flex items-center gap-2 hover:bg-[#F3E2C7]">Shop Getszy</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function NeoHelper() {
  const [q, setQ] = useState("Which plan is right for me?");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState("");
  const ask = async () => {
    if (!q.trim()) return;
    setBusy(true); setReply("");
    try {
      const { data } = await api.post("/ai-tools/neo/chat", { message: q });
      setReply((data && (data.reply || data.response || data.message)) || "Got it — tell me a bit more about what you want to build.");
    } catch (e) {
      toast.error("Neo is resting. Try again in a moment.");
    } finally { setBusy(false); }
  };
  return (
    <div className="mt-5">
      <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={2} className="w-full rounded-2xl bg-white/10 border border-white/20 px-4 py-3 text-sm text-white placeholder-white/50 outline-none" placeholder="I want to launch a small home brand..." />
      <button onClick={ask} disabled={busy} className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#C58B7A] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#b87a68] disabled:opacity-60">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}Ask Neo</button>
      {reply && <div className="mt-4 rounded-2xl bg-white/10 border border-white/15 p-4 text-sm text-white/90">{reply}</div>}
    </div>
  );
}

