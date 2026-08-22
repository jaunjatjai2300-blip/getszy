import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence, useInView } from "framer-motion";
import {
  ArrowRight, Sparkle, Sparkles, Bot, GraduationCap, Wand2, ShoppingBag, Heart, Eye, Star, Home as HomeIcon,
  ChevronRight, Play, Zap, TrendingUp, Package, CreditCard, Search, X, Gift, User,
  Send, Tag, Bookmark, ArrowUpRight, Check, Loader2, Flame, Settings, Globe, Palette,
  PenTool, Store, Megaphone, Rocket, BookOpen, LifeBuoy, FolderKanban, Quote, Wallet,
  Leaf, Moon, ShoppingCart, Headphones, LineChart, Users, Lock, FileText, Command, Hand, Shield
} from "lucide-react";
import { api } from "../lib/api";
import { useCart } from "../lib/cart";
import { useAuth } from "../lib/auth";

const fadeUp = {
  hidden: { opacity: 0, y: 26 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
};
const stagger = { visible: { transition: { staggerChildren: 0.08 } } };

function useApi(url, deps = []) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.get(url).then((r) => alive && setData(Array.isArray(r.data) ? r.data : r.data?.data || [])).catch(() => alive && setData([])).finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, deps);
  return { data, loading };
}

function Section({ children, className = "", id = "" }) {
  const ref = useRef(null);
  const inview = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.section ref={ref} id={id} initial="hidden" animate={inview ? "visible" : "hidden"} variants={stagger} className={"gs-section " + className}>
      {children}
    </motion.section>
  );
}

function fmtINR(n) {
  const num = Number(n || 0);
  if (!num) return "₹0";
  return "₹" + num.toLocaleString("en-IN");
}

const CATEGORIES = [
  { id: "fashion", label: "Fashion", icon: ShoppingBag },
  { id: "jewellery", label: "Jewellery", icon: Sparkle },
  { id: "beauty", label: "Beauty", icon: Wand2 },
  { id: "home-decor", label: "Home & Living", icon: Palette },
  { id: "wellness", label: "Wellness", icon: Leaf },
  { id: "content", label: "Content & Courses", icon: BookOpen },
  { id: "digital", label: "Digital & Templates", icon: Command },
  { id: "services", label: "Services", icon: Hand },
];

const MOODS = [
  { id: "calm", label: "Calm", sub: "Linen, neutrals, slow living", grad: "from-[#D7F0EE] to-[#F3E2C7]", Icon: Leaf },
  { id: "bold", label: "Bold", sub: "Pop colour & sharp tailoring", grad: "from-[#F6C9B8] to-[#E79C86]", Icon: Flame },
  { id: "festive", label: "Festive", sub: "Occasion-ready glam", grad: "from-[#F3D9C0] to-[#E7B98F]", Icon: Sparkles },
  { id: "minimal", label: "Minimal", sub: "Clean, quiet, considered", grad: "from-[#EDE6DD] to-[#FBF7F2]", Icon: Moon },
  { id: "soft", label: "Soft", sub: "Romantic & feminine", grad: "from-[#F4DDE6] to-[#F3E2C7]", Icon: Heart },
  { id: "power", label: "Power", sub: "Sharp, confident, modern", grad: "from-[#D9E4E0] to-[#C8D8D2]", Icon: Zap },
];

const PILLARS = [
  { n: "01", title: "Shop", desc: "Fashion, beauty, jewellery & home from women-led brands — physical, digital & made-to-order.", Icon: ShoppingBag },
  { n: "02", title: "Learn", desc: "Bite-sized courses on money, content, AI & business — built for busy women.", Icon: GraduationCap },
  { n: "03", title: "Build", desc: "Launch your website, store, brand & content with AI — no code, no guesswork.", Icon: PenTool },
  { n: "04", title: "Grow", desc: "Marketing, analytics & AI assistants that scale your business while you sleep.", Icon: TrendingUp },
  { n: "05", title: "Earn", desc: "Sell products, services, courses & memberships — and get paid instantly.", Icon: Wallet },
];

const EDIT_HIGHLIGHTS = [
  { label: "New Arrivals", tag: "Just in", grad: "from-[#F4DDE6] to-[#F3E2C7]" },
  { label: "Best Sellers", tag: "Loved", grad: "from-[#F6C9B8] to-[#E79C86]" },
  { label: "Under ₹999", tag: "Smart buy", grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { label: "Made by Women", tag: "Founder", grad: "from-[#EDE6DD] to-[#FBF7F2]" },
];

const BUILD_TOOLS = [
  { title: "Launch a Website", desc: "A beautiful site in minutes — no code.", Icon: Store, grad: "from-[#F3E2C7] to-[#E79C86]" },
  { title: "Build Your Brand", desc: "Logo, colours, voice & guidelines.", Icon: Palette, grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { title: "Create Content", desc: "Posts, scripts & captions that convert.", Icon: Wand2, grad: "from-[#F4DDE6] to-[#F3E2C7]" },
  { title: "Run Marketing", desc: "Emails, ads & automations on autopilot.", Icon: Megaphone, grad: "from-[#F6C9B8] to-[#E79C86]" },
  { title: "Track Growth", desc: "Analytics & AI insights, simply.", Icon: LineChart, grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { title: "Manage Projects", desc: "Plan, organise & ship with Neo.", Icon: FolderKanban, grad: "from-[#EDE6DD] to-[#FBF7F2]" },
];

const LEARN = [
  { title: "Money Made Simple", lessons: "12 lessons", Icon: BookOpen, grad: "from-[#F3E2C7] to-[#E79C86]" },
  { title: "Content that Sells", lessons: "9 lessons", Icon: Headphones, grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { title: "AI for Creators", lessons: "7 lessons", Icon: Command, grad: "from-[#F4DDE6] to-[#F3E2C7]" },
  { title: "Grow Your Biz", lessons: "10 lessons", Icon: LifeBuoy, grad: "from-[#F6C9B8] to-[#E79C86]" },
];

const GROW = [
  { title: "Marketing AI", desc: "Campaigns, copy & creatives.", Icon: Megaphone, grad: "from-[#F6C9B8] to-[#E79C86]" },
  { title: "Business AI", desc: "Ops, finance & planning.", Icon: LineChart, grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { title: "Content AI", desc: "Ideas to published, fast.", Icon: Wand2, grad: "from-[#F4DDE6] to-[#F3E2C7]" },
  { title: "Founder Tools", desc: "Templates & checklists.", Icon: FolderKanban, grad: "from-[#EDE6DD] to-[#FBF7F2]" },
];

const TRUST_PILLARS = [
  { title: "Evidence you can verify", desc: "Every AI claim links to a source, file or preview you can check.", Icon: Check },
  { title: "You stay in control", desc: "Preview, edit and approve — nothing ships without you.", Icon: Eye },
  { title: "Private by default", desc: "Your data is yours. We don't train on your business.", Icon: Lock },
];

const TESTIMONIALS = [
  { name: "Ananya R.", role: "Home decor founder", text: "I launched my store in a weekend. Neo planned the whole thing while I slept.", grad: "from-[#F4DDE6] to-[#F3E2C7]" },
  { name: "Priya M.", role: "Content creator", text: "Getszy's courses + AI tools took my side hustle to a real income.", grad: "from-[#D7F0EE] to-[#F3E2C7]" },
  { name: "Sara K.", role: "Jewellery maker", text: "I sell to customers I'd never have reached. The Edit changed everything.", grad: "from-[#F6C9B8] to-[#E79C86]" },
];

const NEEDS = [
  "Start a home bakery", "Launch a clothing brand", "Plan my content", "Build a website",
  "Learn to price my work", "Grow on Instagram", "Create a course", "Find a gift for mom",
];



function ProductCard({ product, wishlisted, onToggleWish, addToCart }) {
  const p = product;
  const price = p.price || p.base_price || 0;
  const mrp = p.mrp || p.base_mrp || 0;
  const off = mrp > price ? Math.round((1 - price / mrp) * 100) : 0;
  const img = p.image_url || p.image || "";
  return (
    <motion.div variants={fadeUp} className="group relative">
      <div className="relative overflow-hidden rounded-2xl bg-white border border-[#E7D9CE] shadow-[0_10px_30px_rgba(27,26,24,0.08)] transition-shadow duration-300 group-hover:shadow-[0_24px_60px_rgba(27,26,24,0.16)]">
        <div className="aspect-[4/5] w-full bg-gradient-to-br from-[#F1E7DD] to-[#FBF7F2] flex items-center justify-center">
          {img ? (
            <img src={img} alt={p.name} loading="lazy" className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
          ) : (
            <span className="font-display text-4xl text-[#C9B8A8]">{String(p.name || "?").charAt(0)}</span>
          )}
        </div>
        {off > 0 && <span className="absolute top-3 left-3 gs-pill bg-[#1B1A18] text-white">{off}% OFF</span>}
        <div className="absolute top-3 right-3 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition duration-300">
          <button onClick={() => onToggleWish && onToggleWish(p)} aria-label="Wishlist" className="h-9 w-9 grid place-items-center rounded-full bg-white/90 shadow hover:bg-white">
            <Heart className={"h-4 w-4 " + (wishlisted ? "fill-[#C58B7A] text-[#C58B7A]" : "text-[#1B1A18]")} />
          </button>
          <button onClick={() => addToCart && addToCart(p)} aria-label="Add to cart" className="h-9 w-9 grid place-items-center rounded-full bg-white/90 shadow hover:bg-white">
            <ShoppingCart className="h-4 w-4 text-[#1B1A18]" />
          </button>
        </div>
      </div>
      <div className="mt-3 px-1">
        <div className="flex items-center gap-1 text-[#C58B7A]"><Star className="h-3.5 w-3.5 fill-[#C58B7A]" /><span className="text-xs font-medium">{p.rating || "4.8"}</span></div>
        <h3 className="mt-1 text-[15px] font-semibold text-[#1B1A18] leading-snug line-clamp-2">{p.name}</h3>
        <div className="mt-1 flex items-center gap-2">
          <span className="font-display text-lg text-[#1B1A18]">{fmtINR(price)}</span>
          {mrp > price && <span className="text-sm text-[#9A8E82] line-through">{fmtINR(mrp)}</span>}
        </div>
      </div>
    </motion.div>
  );
}

function DiscoveryRail({ title, icon: Icon, items, wishlist, toggleWish, addToCart, viewAllTo }) {
  const navigate = useNavigate();
  return (
    <div>
      <div className="flex items-end justify-between mb-5">
        <div>
          <span className="gs-eyebrow">{title}</span>
          <h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">{title}</h2>
        </div>
        {viewAllTo && (
          <button onClick={() => navigate(viewAllTo)} className="hidden sm:inline-flex items-center gap-1 text-sm font-semibold text-[#A86B5B] hover:gap-2 transition-all">
            View all <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
      <div className="flex gap-4 overflow-x-auto pb-4 -mx-4 px-4 sm:mx-0 sm:px-0 snap-x">
        {items.map((p) => (
          <div key={p.id} className="min-w-[200px] sm:min-w-[220px] snap-start">
            <ProductCard product={p} wishlisted={wishlist.has(p.id)} onToggleWish={toggleWish} addToCart={addToCart} />
          </div>
        ))}
      </div>
    </div>
  );
}

function MobileBottomNav({ onAskNeo, navigate }) {
  const items = [
    { id: "home", label: "Home", icon: HomeIcon, to: "/" },
    { id: "search", label: "Search", icon: Search, to: "/shop" },
    { id: "neo", label: "Neo", icon: Sparkles, action: onAskNeo, special: true },
    { id: "cart", label: "Cart", icon: ShoppingBag, to: "/cart" },
    { id: "me", label: "Me", icon: User, to: "/account" },
  ];
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-[#FFFDFB]/95 backdrop-blur border-t border-[#E7D9CE]">
      <div className="gs-container flex items-center justify-between py-2">
        {items.map((it) => {
          const Icon = it.icon;
          if (it.special) {
            return (
              <button key={it.id} onClick={it.action} className="relative -mt-6 grid place-items-center h-14 w-14 rounded-full bg-[#C58B7A] text-white shadow-[0_10px_30px_rgba(197,139,122,0.5)]">
                <Icon className="h-6 w-6" />
              </button>
            );
          }
          return (
            <button key={it.id} onClick={() => navigate(it.to)} className="flex flex-col items-center gap-1 text-[#6B625B]">
              <Icon className="h-5 w-5" />
              <span className="text-[10px] font-medium">{it.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}



function NeoShowcase() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const id = setInterval(() => setStage((s) => (s < 9 ? s + 1 : s)), 850);
    return () => clearInterval(id);
  }, [inView]);

  const pipeline = [
    { label: "Founder Brief", Icon: FileText },
    { label: "Brand", Icon: Palette },
    { label: "Website", Icon: Globe },
    { label: "Preview", Icon: Eye },
    { label: "Launch", Icon: Rocket },
  ];

  const [live, setLive] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const liveRef = useRef(null);

  useEffect(() => {
    if (liveRef.current) liveRef.current.scrollTop = liveRef.current.scrollHeight;
  }, [live]);

  async function tryNeo(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    const next = [...live, { who: "you", text }];
    setLive(next);
    setDraft("");
    setBusy(true);
    try {
      const res = await api.post("/ai-tools/neo/chat", { message: text, history: [] });
      const reply = res?.data?.reply || res?.reply || "I'll map that out for you step by step.";
      setLive([...next, { who: "neo", text: reply }]);
    } catch {
      setLive([...next, { who: "neo", text: "I'm here — tell me a bit more and I'll map out the steps." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section ref={ref} className="gs-dark relative overflow-hidden">
      <div className="gs-noise" />
      <div className="gs-container relative py-16 sm:py-24">
        <div className="max-w-3xl">
          <span className="gs-eyebrow-light">Meet Neo</span>
          <h2 className="font-display text-4xl sm:text-6xl text-white mt-4 leading-[1.02]">Meet Neo. <span className="text-[#F3E2C7] italic">Your Getszy AI Guide.</span></h2>
          <p className="mt-5 text-lg text-[#D9CFC4] max-w-xl">You don't need to know which tool you need. Just tell Neo what you're trying to achieve.</p>
        </div>

        <div className="mt-12 grid lg:grid-cols-2 gap-8 items-start">
          <div className="gs-glass rounded-3xl p-6 sm:p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-[#C58B7A] to-[#A86B5B] grid place-items-center"><Bot className="h-5 w-5 text-white" /></div>
              <div><div className="text-white font-semibold">Neo</div><div className="text-xs text-[#B7AEA3]">Your guide · online</div></div>
            </div>


            <div className="space-y-4">
              {stage >= 1 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-white text-[#1B1A18] px-4 py-3 text-[15px]">I want to start a small home bakery.</div>
                </motion.div>
              )}
              {stage >= 2 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-[#241C16] border border-white/10 text-[#F1E7DD] px-4 py-3 text-[15px]">Let's turn that into a launch plan. First, I'll help you define your offer, then shape your brand and a site to take pre-orders.</div>
                </motion.div>
              )}
            </div>

            {stage >= 3 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
                <div className="text-xs uppercase tracking-[0.2em] text-[#B7AEA3] mb-3">Your path</div>
                <div className="flex flex-wrap gap-2">
                  {pipeline.map((step, i) => {
                    const on = stage >= 4 + i;
                    const Icon = step.Icon;
                    return (
                      <motion.div key={step.label} initial={false} animate={{ opacity: on ? 1 : 0.35, y: on ? 0 : 4 }} className={"flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm " + (on ? "border-[#F3E2C7]/50 bg-[#F3E2C7]/10 text-[#F3E2C7]" : "border-white/10 text-[#B7AEA3]")}>
                        <Icon className="h-4 w-4" />
                        {step.label}
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>


          <div className="gs-glass rounded-3xl p-6 sm:p-8">
            <div className="text-white font-semibold mb-1">Try Neo yourself</div>
            <p className="text-sm text-[#B7AEA3] mb-4">Ask anything — a plan, a brand, a website, a gift.</p>
            <div ref={liveRef} className="h-44 overflow-y-auto space-y-3 pr-1">
              {live.length === 0 && <div className="text-sm text-[#9A8E82]">Your conversation will appear here…</div>}
              {live.map((m, i) => (
                <div key={i} className={"flex " + (m.who === "you" ? "justify-end" : "justify-start")}>
                  <div className={"max-w-[85%] rounded-2xl px-4 py-2.5 text-[14px] " + (m.who === "you" ? "bg-white text-[#1B1A18]" : "bg-[#241C16] border border-white/10 text-[#F1E7DD]")}>{m.text}</div>
                </div>
              ))}
              {busy && (<div className="flex justify-start"><div className="rounded-2xl bg-[#241C16] border border-white/10 px-4 py-2.5 text-[14px] text-[#B7AEA3] flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> thinking…</div></div>)}
            </div>
            <form onSubmit={tryNeo} className="mt-4 flex items-center gap-2 rounded-full bg-white/90 p-1.5 pl-4">
              <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="I want to…" className="flex-1 bg-transparent outline-none text-[#1B1A18] text-sm placeholder:text-[#9A8E82]" />
              <button type="submit" disabled={busy} className="h-9 w-9 grid place-items-center rounded-full bg-[#C58B7A] text-white disabled:opacity-60"><Send className="h-4 w-4" /></button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}



function Hero({ onAskNeo }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const submit = (e) => { e.preventDefault(); if (q.trim()) onAskNeo && onAskNeo(q.trim()); };
  return (
    <section className="relative overflow-hidden">
      <div className="gs-hero-wash absolute inset-0" />
      <div className="gs-noise" />
      <div className="gs-container relative pt-14 pb-12 lg:pt-24 lg:pb-24">
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <span className="gs-eyebrow">Shop · Learn · Build · Grow · Earn</span>
            <h1 className="font-display text-[44px] sm:text-6xl lg:text-[72px] leading-[0.98] mt-5 text-[#1B1A18]">Made for women<br/>who <span className="text-[#C58B7A] italic">do it all.</span></h1>
            <p className="mt-6 text-lg text-[#5F5951] max-w-xl">One rooftop for your style, your skills and your business — shop women-led brands, learn real skills, and let Neo build the rest.</p>
            <form onSubmit={submit} className="mt-8 flex items-center gap-2 rounded-full bg-white border border-[#E7D9CE] shadow-[0_14px_40px_rgba(27,26,24,0.10)] p-2 pl-5 max-w-xl">
              <Sparkles className="h-5 w-5 text-[#C58B7A]" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask Neo to plan, build or find anything…" className="flex-1 bg-transparent outline-none text-[#1B1A18] placeholder:text-[#9A8E82]" />
              <button className="gs-btn-primary rounded-full">Go</button>
            </form>
            <div className="mt-4 flex flex-wrap gap-2">
              {["Start a business", "Plan my brand", "Find a gift", "Learn Content"].map((s) => (
                <button key={s} onClick={() => onAskNeo && onAskNeo(s)} className="gs-pill bg-white border border-[#E7D9CE] text-[#5F5951] hover:border-[#C58B7A] transition">{s}</button>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button onClick={() => navigate("/shop")} className="gs-btn-primary inline-flex items-center gap-2">Shop the Edit <ArrowRight className="h-4 w-4" /></button>
              <button onClick={() => onAskNeo && onAskNeo("What can you do for me?")} className="inline-flex items-center gap-2 font-semibold text-[#A86B5B] hover:gap-3 transition-all">Explore Neo <Sparkles className="h-4 w-4" /></button>
            </div>
            <p className="mt-7 text-sm text-[#6B625B]">Trusted by 12,000+ women creators · 4.8★ · Made by women, for women</p>
          </div>
          <div className="lg:col-span-5 relative">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }} className="gs-card relative rounded-[28px] p-5 shadow-[0_30px_80px_rgba(27,26,24,0.18)]">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[#9A8E82]">Today on Getszy</span>
                <span className="gs-pill bg-[#F3E2C7] text-[#A86B5B]"><Sparkles className="h-3 w-3" /> Neo pick</span>
              </div>
              <div className="mt-4 flex items-start gap-3 rounded-2xl bg-gradient-to-br from-[#F3E2C7] to-[#F6C9B8] p-3">
                <div className="h-9 w-9 rounded-full bg-white/70 grid place-items-center"><Bot className="h-5 w-5 text-[#A86B5B]" /></div>
                <div className="text-sm text-[#5F4535]">Tell me what you're building — I'll plan the brand, site & launch.</div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                {[{ n: "Linen Co-ord", g: "from-[#D7F0EE] to-[#F3E2C7]" }, { n: "Ceramic Mug", g: "from-[#F6C9B8] to-[#E79C86]" }, { n: "Gold Hoops", g: "from-[#F4DDE6] to-[#F3E2C7]" }].map((t) => (
                  <div key={t.n} className={"aspect-square rounded-2xl bg-gradient-to-br " + t.g + " flex items-end p-2"}><span className="text-[11px] font-semibold text-[#5F4535] leading-tight">{t.n}</span></div>
                ))}
              </div>
            </motion.div>
            <div className="absolute -bottom-6 -left-6 hidden lg:block">
              <div className="gs-card rounded-2xl px-4 py-3 shadow-[0_20px_50px_rgba(27,26,24,0.14)] flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#2F7E7A]" /> <span className="text-sm font-medium text-[#1B1A18]">12,000+ women earning</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}



export default function Home() {
  const navigate = useNavigate();
  const { add } = useCart();
  const { user } = useAuth() || {};
  const [wishlist, setWishlist] = useState(() => new Set());
  const toggleWishlist = (p) => setWishlist((prev) => { const n = new Set(prev); if (n.has(p.id)) n.delete(p.id); else n.add(p.id); return n; });
  const addToCart = (p) => add(p.id);
  const askNeo = (msg) => navigate("/dashboard");
  const [email, setEmail] = useState("");
  const [subbed, setSubbed] = useState(false);
  const subscribe = (e) => { e.preventDefault(); if (email.trim()) setSubbed(true); };
  const categories = useApi("/categories");
  const trending = useApi("/shop?sort=trending&limit=10");
  const bestsellers = useApi("/shop?sort=bestseller&limit=10");

  return (
    <div className="bg-[#FBF7F2]">
      <Hero onAskNeo={askNeo} />

      <div className="gs-container">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {(categories.data.length ? categories.data : CATEGORIES).map((c) => {
            const Icon = c.icon || ShoppingBag;
            return (
              <button key={c.id} onClick={() => navigate("/shop?category=" + c.id)} className="group flex flex-col items-center gap-2 rounded-2xl bg-white border border-[#E7D9CE] p-4 text-center hover:border-[#C58B7A] transition">
                <span className="h-11 w-11 grid place-items-center rounded-full bg-[#F1E7DD] text-[#A86B5B] group-hover:bg-[#C58B7A] group-hover:text-white transition"><Icon className="h-5 w-5" /></span>
                <span className="text-xs font-semibold text-[#1B1A18]">{c.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <Section>
        <div className="gs-container">
          <div className="max-w-2xl">
            <span className="gs-eyebrow">One rooftop</span>
            <h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">The Getszy Way</h2>
            <p className="mt-3 text-[#5F5951]">Five steps from an idea to a business that pays you — all in one place.</p>
          </div>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {PILLARS.map((p) => {
              const Icon = p.Icon;
              return (
                <motion.div key={p.n} variants={fadeUp} className="group relative rounded-3xl bg-white border border-[#E7D9CE] p-6 shadow-[0_10px_30px_rgba(27,26,24,0.06)] hover:shadow-[0_24px_60px_rgba(27,26,24,0.12)] transition">
                  <div className="font-display text-2xl text-[#D9C3B2]">{p.n}</div>
                  <div className="mt-3 h-11 w-11 grid place-items-center rounded-full bg-[#F3E2C7] text-[#A86B5B]"><Icon className="h-5 w-5" /></div>
                  <h3 className="mt-4 font-display text-xl text-[#1B1A18]">{p.title}</h3>
                  <p className="mt-2 text-sm text-[#5F5951] leading-relaxed">{p.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </Section>

      <Section>
        <div className="gs-container">
          <div className="flex items-end justify-between mb-6">
            <div><span className="gs-eyebrow">Curated</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">The Getszy Edit</h2></div>
            <button onClick={() => navigate("/shop")} className="hidden sm:inline-flex items-center gap-1 text-sm font-semibold text-[#A86B5B]">Shop all <ArrowRight className="h-4 w-4" /></button>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {EDIT_HIGHLIGHTS.map((h) => (
              <button key={h.label} onClick={() => navigate("/shop")} className={"group relative overflow-hidden rounded-3xl bg-gradient-to-br p-6 text-left min-h-[150px] flex flex-col justify-between " + h.grad}>
                <span className="gs-pill bg-white/70 text-[#A86B5B] w-fit">{h.tag}</span>
                <span className="font-display text-xl text-[#5F4535]">{h.label}</span>
              </button>
            ))}
          </div>
        </div>
      </Section>

      <Section>
        <div className="gs-container">
          <div className="max-w-2xl"><span className="gs-eyebrow">How do you feel?</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Shop Your Mood</h2></div>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {MOODS.map((m) => {
              const Icon = m.Icon;
              return (
                <button key={m.id} onClick={() => navigate("/shop?mood=" + m.id)} className={"group relative overflow-hidden rounded-3xl bg-gradient-to-br p-5 text-left min-h-[180px] flex flex-col justify-between " + m.grad}>
                  <span className="h-10 w-10 grid place-items-center rounded-full bg-white/60 text-[#A86B5B]"><Icon className="h-5 w-5" /></span>
                  <div><div className="font-display text-lg text-[#5F4535]">{m.label}</div><div className="text-xs text-[#6B5A48] mt-1">{m.sub}</div></div>
                </button>
              );
            })}
          </div>
        </div>
      </Section>



      <Section><div className="gs-container"><DiscoveryRail title="Trending Now" icon={TrendingUp} items={trending.data} wishlist={wishlist} toggleWish={toggleWishlist} addToCart={addToCart} viewAllTo="/shop?sort=trending" /></div></Section>
      <Section><div className="gs-container"><DiscoveryRail title="Best Sellers" icon={Star} items={bestsellers.data} wishlist={wishlist} toggleWish={toggleWishlist} addToCart={addToCart} viewAllTo="/shop?sort=bestseller" /></div></Section>

      <Section className="bg-[#FBF1E9]">
        <div className="gs-container">
          <div className="max-w-2xl"><span className="gs-eyebrow">Build & Grow</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">Turn the idea into income</h2><p className="mt-3 text-[#5F5951]">Neo builds the boring parts. You stay the founder.</p></div>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {BUILD_TOOLS.map((t) => {
              const Icon = t.Icon;
              return (
                <motion.div key={t.title} variants={fadeUp} className="group rounded-3xl bg-white border border-[#E7D9CE] p-6 hover:shadow-[0_24px_60px_rgba(27,26,24,0.12)] transition">
                  <div className={"h-12 w-12 grid place-items-center rounded-2xl bg-gradient-to-br text-white " + t.grad}><Icon className="h-6 w-6" /></div>
                  <h3 className="mt-4 font-display text-xl text-[#1B1A18]">{t.title}</h3>
                  <p className="mt-2 text-sm text-[#5F5951]">{t.desc}</p>
                </motion.div>
              );
            })}
          </div>
          <div className="mt-8"><button onClick={() => askNeo("Help me launch my business")} className="gs-btn-primary inline-flex items-center gap-2">Build with Neo <Sparkles className="h-4 w-4" /></button></div>
        </div>
      </Section>

      <Section><div className="gs-container">
        <div className="max-w-2xl"><span className="gs-eyebrow">Learn</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Skills that pay you back</h2></div>
        <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {LEARN.map((c) => {
            const Icon = c.Icon;
            return (
              <motion.div key={c.title} variants={fadeUp} className="group rounded-3xl bg-white border border-[#E7D9CE] overflow-hidden hover:shadow-[0_24px_60px_rgba(27,26,24,0.12)] transition">
                <div className={"h-28 bg-gradient-to-br " + c.grad} />
                <div className="p-4"><div className="flex items-center gap-2 text-[#A86B5B]"><Icon className="h-4 w-4" /><span className="text-xs font-semibold">{c.lessons}</span></div><h3 className="mt-1 font-display text-lg text-[#1B1A18]">{c.title}</h3></div>
              </motion.div>
            );
          })}
        </div>
      </div></Section>



      <Section><div className="gs-container">
        <div className="rounded-[32px] bg-gradient-to-br from-[#F3E2C7] to-[#F6C9B8] p-8 sm:p-12 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="max-w-xl"><span className="gs-eyebrow">Gift Finder</span><h2 className="font-display text-3xl sm:text-4xl text-[#5F4535] mt-2">Stuck on a gift? Ask Neo.</h2><p className="mt-3 text-[#6B5A48]">Tell us the occasion and who it's for — we'll curate from women-led brands.</p></div>
          <button onClick={() => askNeo("Help me find a gift for my mom's birthday")} className="gs-btn-primary inline-flex items-center gap-2 bg-[#1B1A18] hover:bg-[#000]">Find a gift <Gift className="h-4 w-4" /></button>
        </div>
      </div></Section>

      <Section><div className="gs-container">
        <div className="flex items-end justify-between mb-6"><div><span className="gs-eyebrow">Stylist pick</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Complete the Look</h2></div><button onClick={() => navigate("/shop")} className="hidden sm:inline-flex items-center gap-1 text-sm font-semibold text-[#A86B5B]">Shop the look <ArrowRight className="h-4 w-4" /></button></div>
        <div className="grid sm:grid-cols-3 gap-4">
          {[{ n: "The Soft Minimal", g: "from-[#F4DDE6] to-[#F3E2C7]" }, { n: "The Power Edit", g: "from-[#D7F0EE] to-[#F3E2C7]" }, { n: "The Festive Glow", g: "from-[#F6C9B8] to-[#E79C86]" }].map((t) => (
            <div key={t.n} className={"group relative overflow-hidden rounded-3xl bg-gradient-to-br p-8 min-h-[220px] flex flex-col justify-end " + t.g}>
              <div className="font-display text-2xl text-[#5F4535]">{t.n}</div>
              <div className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-[#A86B5B]">Shop set <ArrowRight className="h-4 w-4" /></div>
            </div>
          ))}
        </div>
      </div></Section>

      <NeoShowcase />

      <Section><div className="gs-container">
        <div className="max-w-2xl"><span className="gs-eyebrow">Idea → Outcome</span><h2 className="font-display text-3xl sm:text-5xl text-[#1B1A18] mt-2">From a thought to a launched thing</h2></div>
        <div className="mt-10 grid sm:grid-cols-5 gap-4">
          {[
            { n: "01", t: "Brief", d: "Tell Neo your idea", Icon: FileText },
            { n: "02", t: "Brand", d: "Identity & voice", Icon: Palette },
            { n: "03", t: "Build", d: "Site, store & content", Icon: Store },
            { n: "04", t: "Preview", d: "Review with you", Icon: Eye },
            { n: "05", t: "Launch", d: "Go live & sell", Icon: Rocket },
          ].map((s, i) => {
            const Icon = s.Icon;
            return (
              <motion.div key={s.n} variants={fadeUp} className="relative rounded-3xl bg-white border border-[#E7D9CE] p-5">
                <div className="flex items-center justify-between"><span className="font-display text-xl text-[#D9C3B2]">{s.n}</span><Icon className="h-5 w-5 text-[#A86B5B]" /></div>
                <h3 className="mt-3 font-display text-lg text-[#1B1A18]">{s.t}</h3>
                <p className="mt-1 text-sm text-[#5F5951]">{s.d}</p>
                {i < 4 && <ChevronRight className="hidden sm:block absolute -right-3 top-1/2 -translate-y-1/2 text-[#C9B8A8]" />}
              </motion.div>
            );
          })}
        </div>
      </div></Section>



      <Section><div className="gs-container">
        <div className="max-w-2xl"><span className="gs-eyebrow">Why you can trust it</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Trusted AI, not magic</h2></div>
        <div className="mt-8 grid sm:grid-cols-3 gap-5">
          {TRUST_PILLARS.map((p) => {
            const Icon = p.Icon;
            return (
              <motion.div key={p.title} variants={fadeUp} className="rounded-3xl bg-white border border-[#E7D9CE] p-6">
                <div className="h-11 w-11 grid place-items-center rounded-full bg-[#D7F0EE] text-[#2F7E7A]"><Icon className="h-5 w-5" /></div>
                <h3 className="mt-4 font-display text-xl text-[#1B1A18]">{p.title}</h3>
                <p className="mt-2 text-sm text-[#5F5951] leading-relaxed">{p.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </div></Section>

      <Section><div className="gs-container">
        <div className="max-w-2xl"><span className="gs-eyebrow">Real customers</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Stories from the rooftop</h2></div>
        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {TESTIMONIALS.map((t) => (
            <motion.div key={t.name} variants={fadeUp} className="rounded-3xl bg-white border border-[#E7D9CE] p-6 shadow-[0_10px_30px_rgba(27,26,24,0.06)]">
              <Quote className="h-7 w-7 text-[#E7C9A8]" />
              <p className="mt-3 text-[#1B1A18] leading-relaxed">"{t.text}"</p>
              <div className="mt-5 flex items-center gap-3">
                <span className={"h-11 w-11 rounded-full bg-gradient-to-br " + t.grad + " grid place-items-center font-display text-[#5F4535]"}>{t.name.charAt(0)}</span>
                <div><div className="font-semibold text-[#1B1A18] text-sm">{t.name}</div><div className="text-xs text-[#6B625B]">{t.role}</div></div>
              </div>
            </motion.div>
          ))}
        </div>
      </div></Section>

      <Section className="bg-[#FBF1E9]"><div className="gs-container">
        <div className="rounded-[32px] bg-white border border-[#E7D9CE] p-8 sm:p-12 grid lg:grid-cols-2 gap-8 items-center">
          <div><span className="gs-eyebrow">My Getszy</span><h2 className="font-display text-3xl sm:text-4xl text-[#1B1A18] mt-2">Your world, in one place</h2><p className="mt-3 text-[#5F5951]">Orders, projects, downloads and wishes — picked up right where you left them.</p></div>
          <div className="grid grid-cols-2 gap-3">
            {[{ l: "My Orders", i: Package }, { l: "My Projects", i: FolderKanban }, { l: "Downloads", i: Bookmark }, { l: "Wishlist", i: Heart }, { l: "Credits", i: CreditCard }, { l: "Support", i: Headphones }].map((q) => {
              const Icon = q.i;
              return <button key={q.l} onClick={() => navigate("/account")} className="flex items-center gap-3 rounded-2xl bg-[#FBF7F2] border border-[#E7D9CE] p-4 text-left hover:border-[#C58B7A] transition"><Icon className="h-5 w-5 text-[#A86B5B]" /><span className="text-sm font-semibold text-[#1B1A18]">{q.l}</span></button>;
            })}
          </div>
        </div>
      </div></Section>

      <Section><div className="gs-container">
        <div className="rounded-[32px] bg-gradient-to-br from-[#F3E2C7] to-[#F6C9B8] p-8 sm:p-12">
          <div className="max-w-xl"><span className="gs-eyebrow">The Edit letter</span><h2 className="font-display text-3xl sm:text-4xl text-[#5F4535] mt-2">Get the good stuff weekly</h2><p className="mt-3 text-[#6B5A48]">New drops, creator tips & Neo updates — no spam, just value.</p></div>
          {subbed ? (
            <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/70 px-4 py-2 text-[#A86B5B] font-semibold"><Check className="h-4 w-4" /> You're on the list — welcome!</p>
          ) : (
            <form onSubmit={subscribe} className="mt-6 flex flex-col sm:flex-row gap-3 max-w-md">
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required placeholder="you@email.com" className="flex-1 rounded-full border border-[#E7D9CE] bg-white px-5 py-3 outline-none focus:border-[#C58B7A]" />
              <button type="submit" className="gs-btn-primary rounded-full">Subscribe</button>
            </form>
          )}
        </div>
      </div></Section>

      <section className="gs-dark relative overflow-hidden">
        <div className="gs-noise" />
        <div className="gs-container relative py-16 sm:py-24 text-center">
          <h2 className="font-display text-4xl sm:text-6xl text-white">Ready to build something yours?</h2>
          <p className="mt-4 text-[#D9CFC4] max-w-xl mx-auto">Shop, learn, build and earn — all under one rooftop, with Neo by your side.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <button onClick={() => navigate("/shop")} className="gs-btn-primary inline-flex items-center gap-2">Shop the Edit <ArrowRight className="h-4 w-4" /></button>
            <button onClick={() => askNeo("Help me get started")} className="inline-flex items-center gap-2 rounded-full border border-white/30 px-6 py-3 font-semibold text-white hover:bg-white/10 transition">Talk to Neo <Sparkles className="h-4 w-4" /></button>
          </div>
        </div>
      </section>

      <MobileBottomNav onAskNeo={askNeo} navigate={navigate} />
    </div>
  );
}









