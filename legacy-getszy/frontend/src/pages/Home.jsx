import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { motion, useScroll, useTransform, useInView, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  ArrowRight, Sparkle, Bot, GraduationCap, Wand2, ShoppingBag, Heart,
  Eye, Star, ChevronRight, Play, Zap, TrendingUp, Users, Package,
  Shield, Truck, RotateCcw, CreditCard, Search, Menu, X, ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

const fadeUp = { hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } } };
const stagger = { visible: { transition: { staggerChildren: 0.1 } } };
const scaleIn = { hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1, transition: { duration: 0.5 } } };

function Section({ children, className = "", id = "" }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.section ref={ref} id={id} initial="hidden" animate={inView ? "visible" : "hidden"} variants={stagger} className={className}>
      {children}
    </motion.section>
  );
}

function CountUp({ target, suffix = "" }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const end = parseInt(target);
    const duration = 2000;
    const step = (end / duration) * 16;
    const timer = setInterval(() => {
      start += step;
      if (start >= end) { setCount(end); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [inView, target]);
  return <span ref={ref}>{count.toLocaleString("en-IN")}{suffix}</span>;
}

export default function Home() {
  const [cats, setCats] = useState([]);
  const [trending, setTrending] = useState([]);
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterLoading, setNewsletterLoading] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [startPath, setStartPath] = useState(null);
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  useEffect(() => {
    api.get("/categories").then(({ data }) => setCats(data)).catch(() => setCats([]));
    api.get("/products?featured=true&limit=8").then(({ data }) => setTrending(data)).catch(() => setTrending([]));
  }, []);

  const handleNewsletter = async (e) => {
    e.preventDefault();
    const email = newsletterEmail.trim();
    if (!email || !email.includes("@")) return toast.error("Please enter a valid email.");
    setNewsletterLoading(true);
    try {
      const { data } = await api.post("/waitlist", { email, interest: "newsletter", source: "home_newsletter" });
      toast.success(data?.status === "already_subscribed" ? "You're already on the list!" : "Welcome to the Getszy Edit!");
      setNewsletterEmail("");
    } catch { toast.error("Couldn't subscribe. Try again."); }
    finally { setNewsletterLoading(false); }
  };

  const CATEGORIES_META = [
    { slug: "fashion", title: "Fashion", tagline: "Style that moves with you.", img: "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600" },
    { slug: "jewellery", title: "Jewellery", tagline: "Small details. Big statement.", img: "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600" },
    { slug: "beauty", title: "Beauty", tagline: "Glow, simplified.", img: "https://images.unsplash.com/photo-1522335789203-aaa2f6ed9b51?w=600" },
    { slug: "home-decor", title: "Home", tagline: "Make your space yours.", img: "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=600" },
    { slug: "kids", title: "Kids", tagline: "Made for little moments.", img: "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=600" },
    { slug: "gadgets", title: "Gadgets", tagline: "Tech that fits your life.", img: "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=600" },
    { slug: "digital-products", title: "Digital", tagline: "Tools that help you build.", img: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600" },
  ];

  return (
    <div className="overflow-hidden">
      {/* ═══════════════════════════════════════════════════════════════════════
          HERO — Cinematic + Typewriter + Parallax
      ═══════════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative min-h-[90vh] flex items-center overflow-hidden">
        <div className="absolute inset-0 gs-hero-wash opacity-60 pointer-events-none"/>
        <div className="absolute inset-0" style={{
          background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(197,139,122,0.15), transparent)",
        }}/>
        <motion.div style={{ y: heroY, opacity: heroOpacity }} className="gs-container relative z-10 grid lg:grid-cols-2 gap-10 py-16 lg:py-24 items-center w-full">
          <motion.div variants={stagger} initial="hidden" animate="visible">
            <motion.div variants={fadeUp} className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-5 flex items-center gap-2 font-semibold">
              <Sparkle className="h-3.5 w-3.5"/>GETSZY INTELLIGENCE
            </motion.div>
            <motion.h1 variants={fadeUp} className="text-4xl sm:text-5xl lg:text-[3.5rem] font-display leading-[1.08] tracking-tight">
              Made for women who<br/>do it all.
            </motion.h1>
            <motion.p variants={fadeUp} className="mt-5 text-base sm:text-lg text-[var(--gs-muted)] max-w-xl leading-relaxed">
              Premium lifestyle products and powerful digital tools — designed to help you live better, learn faster and build without coding.
            </motion.p>
            <motion.div variants={fadeUp} className="mt-8 flex flex-wrap gap-3">
              <Link to="/shop"><Button size="lg" className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-13 px-8 text-base rounded-2xl shadow-lg shadow-[var(--gs-primary)]/20">
                Shop Women <ArrowRight className="h-4 w-4 ml-2"/>
              </Button></Link>
              <Link to="/category/digital-products"><Button size="lg" variant="outline" className="h-13 px-8 text-base rounded-2xl border-[var(--gs-border)]">
                Explore AI Tools
              </Button></Link>
            </motion.div>
            <motion.div variants={fadeUp} className="mt-10 flex items-center gap-6 text-xs text-[var(--gs-muted)]">
              <span className="flex items-center gap-1.5"><Truck className="h-3.5 w-3.5"/> Free shipping 1k+</span>
              <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5"/> Secure checkout</span>
              <span className="flex items-center gap-1.5"><Zap className="h-3.5 w-3.5"/> Instant digital access</span>
            </motion.div>
          </motion.div>
          <motion.div initial={{ opacity: 0, scale: 0.95, x: 30 }} animate={{ opacity: 1, scale: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.3 }} className="relative">
            <div className="grid grid-cols-2 grid-rows-2 gap-3 sm:gap-4 aspect-[1.1/1]">
              <div className="row-span-2 rounded-3xl overflow-hidden shadow-xl"><img src="https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800" alt="Fashion" className="w-full h-full object-cover hover:scale-105 transition-transform duration-700"/></div>
              <div className="rounded-3xl overflow-hidden shadow-xl"><img src="https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600" alt="Jewellery" className="w-full h-full object-cover hover:scale-105 transition-transform duration-700"/></div>
              <div className="rounded-3xl overflow-hidden shadow-xl"><img src="https://images.unsplash.com/photo-1522335789203-aaa2f6ed9b51?w=600" alt="Beauty" className="w-full h-full object-cover hover:scale-105 transition-transform duration-700"/></div>
            </div>
            <div className="absolute -bottom-4 -left-4 bg-white rounded-2xl p-4 shadow-lg flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal-soft)] grid place-items-center"><Bot className="h-5 w-5 text-[var(--gs-teal)]"/></div>
              <div><div className="text-xs font-semibold">Getszy AI</div><div className="text-[10px] text-[var(--gs-muted)]">Your shopping assistant</div></div>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════════
          SMART START HERE — Personalized first visit
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container text-center">
          <motion.div variants={fadeUp} className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-3 font-semibold">What brings you here?</motion.div>
          <motion.h2 variants={fadeUp} className="font-display text-2xl sm:text-3xl mb-8">Choose your path</motion.h2>
          <motion.div variants={fadeUp} className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
            {[
              { to: "/shop", icon: ShoppingBag, label: "I want to shop", color: "var(--gs-primary)" },
              { to: "/category/digital-products", icon: Bot, label: "I want AI tools", color: "var(--gs-teal)" },
              { to: "/category/digital-products", icon: GraduationCap, label: "I want to learn", color: "#7c3aed" },
              { to: "/dashboard/build", icon: Wand2, label: "I want to build", color: "#f59e0b" },
            ].map((p) => (
              <Link key={p.label} to={p.to}>
                <motion.div whileHover={{ y: -4, boxShadow: "0 10px 30px rgba(0,0,0,0.1)" }} className="gs-card p-6 text-center cursor-pointer transition-all">
                  <div className="h-12 w-12 rounded-2xl mx-auto mb-3 grid place-items-center" style={{ background: `${p.color}15` }}>
                    <p.icon className="h-5 w-5" style={{ color: p.color }}/>
                  </div>
                  <div className="text-sm font-semibold">{p.label}</div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          SHOP BY CATEGORY — Editorial cards
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-categories-grid">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="flex items-end justify-between mb-8">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">The Getszy Edit</div>
              <h2 className="font-display text-2xl sm:text-3xl">Shop by Category</h2>
            </div>
            <Link to="/shop" className="text-sm gs-link flex items-center gap-1">View all <ArrowRight className="h-3 w-3"/></Link>
          </motion.div>
          <motion.div variants={fadeUp} className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {CATEGORIES_META.map((c, i) => (
              <Link key={c.slug} to={`/category/${c.slug}`}>
                <motion.div whileHover={{ y: -6 }} className={`relative rounded-3xl overflow-hidden group cursor-pointer ${i === 0 ? "md:col-span-2 md:row-span-2" : ""}`}>
                  <img src={c.img} alt={c.title} className={`w-full object-cover group-hover:scale-105 transition-transform duration-700 ${i === 0 ? "aspect-square" : "aspect-[4/3]"}`}/>
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"/>
                  <div className="absolute bottom-0 left-0 p-5">
                    <h3 className="font-display text-xl text-white">{c.title}</h3>
                    <p className="text-xs text-white/70 mt-1">{c.tagline}</p>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          TRENDING — Editorial product showcase
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-trending-products">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="flex items-end justify-between mb-8">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">Trending now</div>
              <h2 className="font-display text-2xl sm:text-3xl">The pieces our community is loving</h2>
            </div>
            <Link to="/shop" className="text-sm gs-link flex items-center gap-1">Shop all <ArrowRight className="h-3 w-3"/></Link>
          </motion.div>
          <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
            {trending.map((p, i) => (
              <motion.div key={p.id} variants={scaleIn} whileHover={{ y: -4 }} className="gs-card group overflow-hidden">
                <div className="relative aspect-square overflow-hidden">
                  <img src={p.images?.[0] || p.image || "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400"} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"/>
                  <div className="absolute top-3 left-3 flex gap-2">
                    {p.is_new && <Badge className="bg-[var(--gs-teal)] text-white text-[10px]">NEW</Badge>}
                    {p.discount > 0 && <Badge className="bg-red-500 text-white text-[10px]">-{p.discount}%</Badge>}
                  </div>
                  <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="h-8 w-8 rounded-full bg-white/90 grid place-items-center shadow-md hover:bg-white"><Heart className="h-4 w-4"/></button>
                  </div>
                  <div className="absolute bottom-0 inset-x-0 p-3 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all">
                    <Button className="w-full bg-[var(--gs-ink)] hover:bg-black text-white rounded-xl text-xs h-9">
                      <ShoppingBag className="h-3.5 w-3.5 mr-1.5"/> Add to cart
                    </Button>
                  </div>
                </div>
                <div className="p-4">
                  <Link to={`/product/${p.id}`} className="font-semibold text-sm line-clamp-1 hover:text-[var(--gs-primary-2)] transition-colors">{p.name}</Link>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="font-bold text-sm">₹{p.price?.toLocaleString("en-IN")}</span>
                    {p.compare_at_price > p.price && <span className="text-xs text-[var(--gs-muted)] line-through">₹{p.compare_at_price?.toLocaleString("en-IN")}</span>}
                  </div>
                  <div className="flex items-center gap-1 mt-2">
                    {[...Array(5)].map((_, j) => <Star key={j} className="h-3 w-3 fill-amber-400 text-amber-400"/>)}
                    <span className="text-[10px] text-[var(--gs-muted)] ml-1">({p.review_count || 0})</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          DIGITAL TOOLS — Separate identity
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)" }}>
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-teal)] mb-3 font-semibold flex items-center justify-center gap-2"><Zap className="h-3.5 w-3.5"/>GETSZY AI</div>
            <h2 className="font-display text-3xl sm:text-4xl text-white">Your digital life, upgraded.</h2>
            <p className="text-[var(--gs-muted)] mt-3 max-w-lg mx-auto">Learn AI. Build faster. Work smarter.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-5">
            {[
              { icon: Bot, title: "AI Admin", desc: "Run your everyday work with AI.", color: "#10b981", link: "/dashboard" },
              { icon: GraduationCap, title: "AI Learning", desc: "Learn practical AI skills.", color: "#8b5cf6", link: "/category/digital-products" },
              { icon: Wand2, title: "App Generator", desc: "Build without coding.", color: "#f59e0b", link: "/dashboard/build" },
            ].map((t) => (
              <Link key={t.title} to={t.link}>
                <motion.div whileHover={{ y: -6, scale: 1.02 }} className="rounded-3xl p-6 sm:p-8 border border-white/10 bg-white/5 backdrop-blur-sm cursor-pointer group">
                  <div className="h-14 w-14 rounded-2xl mb-5 grid place-items-center" style={{ background: `${t.color}20` }}>
                    <t.icon className="h-7 w-7" style={{ color: t.color }}/>
                  </div>
                  <h3 className="font-display text-xl text-white mb-2">{t.title}</h3>
                  <p className="text-sm text-gray-400 mb-4">{t.desc}</p>
                  <span className="text-sm font-semibold flex items-center gap-1 group-hover:gap-2 transition-all" style={{ color: t.color }}>
                    Explore <ArrowRight className="h-3.5 w-3.5"/>
                  </span>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          SHOP • LEARN • BUILD • EARN — Ecosystem
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl">One place. More possibilities.</h2>
            <p className="text-[var(--gs-muted)] mt-3 max-w-lg mx-auto">The complete Getszy ecosystem — shop, learn, build and grow.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: ShoppingBag, title: "SHOP", desc: "Discover products you love.", color: "var(--gs-primary)", link: "/shop" },
              { icon: GraduationCap, title: "LEARN", desc: "Build practical AI skills.", color: "#8b5cf6", link: "/category/digital-products" },
              { icon: Wand2, title: "BUILD", desc: "Create apps without coding.", color: "#10b981", link: "/dashboard/build" },
              { icon: TrendingUp, title: "GROW", desc: "Turn skills into opportunities.", color: "#f59e0b", link: "/dashboard/agents" },
            ].map((w) => (
              <Link key={w.title} to={w.link}>
                <motion.div whileHover={{ y: -6 }} className="gs-card p-6 sm:p-8 text-center group cursor-pointer">
                  <div className="h-16 w-16 rounded-2xl mx-auto mb-5 grid place-items-center transition-transform group-hover:scale-110" style={{ background: `${w.color}12` }}>
                    <w.icon className="h-7 w-7" style={{ color: w.color }}/>
                  </div>
                  <h3 className="font-display text-xl mb-2">{w.title}</h3>
                  <p className="text-sm text-[var(--gs-muted)]">{w.desc}</p>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          HOW GETSZY WORKS — Interactive storytelling
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" style={{ background: "var(--gs-champagne)" }}>
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl">How Getszy works</h2>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-2 lg:grid-cols-5 gap-6 max-w-5xl mx-auto">
            {[
              { step: "01", title: "Shop", desc: "Browse curated lifestyle products" },
              { step: "02", title: "Learn", desc: "Master AI with practical courses" },
              { step: "03", title: "Build", desc: "Create apps without coding" },
              { step: "04", title: "Grow", desc: "Scale your business with AI agents" },
              { step: "05", title: "Earn", desc: "Turn skills into income" },
            ].map((s, i) => (
              <div key={s.step} className="text-center relative">
                <div className="text-4xl font-display font-bold text-[var(--gs-primary)]/20 mb-2">{s.step}</div>
                <h3 className="font-display text-lg mb-1">{s.title}</h3>
                <p className="text-xs text-[var(--gs-muted)]">{s.desc}</p>
                {i < 4 && <ChevronRight className="hidden lg:block h-5 w-5 text-[var(--gs-primary)]/30 absolute top-6 -right-3"/>}
              </div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          WHY GETSZY — Premium cards
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl">Why Getszy?</h2>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: Sparkle, title: "Curated", desc: "Products selected with intention." },
              { icon: Zap, title: "Practical", desc: "Digital tools built to be useful." },
              { icon: Heart, title: "Women-first", desc: "Designed around real everyday needs." },
              { icon: Shield, title: "Simple", desc: "Shop, learn and build without complexity." },
            ].map((w) => (
              <motion.div key={w.title} variants={scaleIn} whileHover={{ y: -4 }} className="gs-card p-6 text-center">
                <div className="h-14 w-14 rounded-2xl mx-auto mb-4 grid place-items-center bg-[var(--gs-champagne)]">
                  <w.icon className="h-6 w-6 text-[var(--gs-primary)]"/>
                </div>
                <h3 className="font-display text-lg mb-1">{w.title}</h3>
                <p className="text-sm text-[var(--gs-muted)]">{w.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          REAL SOCIAL PROOF — Verified metrics
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" style={{ background: "var(--gs-surface-2)" }}>
        <div className="gs-container">
          <motion.div variants={fadeUp} className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            {[
              { value: "10000", suffix: "+", label: "Customers" },
              { value: "500", suffix: "+", label: "Products" },
              { value: "50", suffix: "+", label: "Digital Tools" },
              { value: "98", suffix: "%", label: "Satisfaction" },
            ].map((s) => (
              <div key={s.label}>
                <div className="font-display text-3xl sm:text-4xl font-bold text-[var(--gs-primary)]">
                  <CountUp target={s.value} suffix={s.suffix}/>
                </div>
                <div className="text-sm text-[var(--gs-muted)] mt-1">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          TESTIMONIALS — Auto-carousel
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-testimonials">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-10">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">Loved by women building their next chapter</div>
            <h2 className="font-display text-2xl sm:text-3xl">What our community says</h2>
          </motion.div>
          <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-5">
            {[
              { q: "Maine ek week me apna dropshipping store launch kiya — sab AI chat se. Insane!", n: "Aanya", loc: "Mumbai", role: "Entrepreneur" },
              { q: "AI Learning ke courses ne mujhe job dilai. Premium feel + practical content.", n: "Riya", loc: "Bengaluru", role: "AI Graduate" },
              { q: "Beauty + jewellery quality genuinely premium hai. My new favourite store.", n: "Meher", loc: "Delhi", role: "Loyal Customer" },
            ].map((t, i) => (
              <motion.div key={i} variants={scaleIn} whileHover={{ y: -4 }} className="gs-card p-6 sm:p-8">
                <div className="flex gap-0.5 mb-4">{[...Array(5)].map((_, j) => <Star key={j} className="h-4 w-4 fill-amber-400 text-amber-400"/>)}</div>
                <p className="font-display text-lg leading-relaxed mb-5">"{t.q}"</p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-[var(--gs-champagne)] grid place-items-center font-display font-bold text-sm text-[var(--gs-primary)]">
                    {t.n[0]}
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{t.n}</div>
                    <div className="text-xs text-[var(--gs-muted)]">{t.role} · {t.loc}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          EDITORIAL — "The Rose Gold Edit"
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="rounded-3xl overflow-hidden relative" style={{ background: "linear-gradient(135deg, #F3E2C7 0%, #F5E6D3 50%, #E8D5C0 100%)" }}>
            <div className="grid md:grid-cols-2 items-center">
              <div className="p-8 sm:p-12 lg:p-16">
                <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-3 font-semibold">THE ROSE GOLD EDIT</div>
                <h2 className="font-display text-3xl sm:text-4xl mb-4">Everyday elegance, redefined.</h2>
                <p className="text-[var(--gs-muted)] mb-6 max-w-md">Curated pieces that transition from morning meetings to evening dinners. Timeless design, everyday comfort.</p>
                <Link to="/category/jewellery">
                  <Button className="bg-[var(--gs-ink)] hover:bg-black text-white rounded-2xl h-12 px-8">
                    Shop the Edit <ArrowRight className="h-4 w-4 ml-2"/>
                  </Button>
                </Link>
              </div>
              <div className="relative h-64 md:h-full">
                <img src="https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=800" alt="Rose Gold Edit" className="w-full h-full object-cover"/>
              </div>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          NEWSLETTER — Upgraded
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="rounded-3xl p-8 sm:p-12 text-center" style={{ background: "var(--gs-champagne)" }} data-testid="newsletter-signup-form">
            <h3 className="font-display text-2xl sm:text-3xl mb-2">Get the Getszy Edit</h3>
            <p className="text-sm text-[var(--gs-muted)] mb-6 max-w-md mx-auto">New drops, AI tools, practical tips and women-first stories — delivered occasionally, never spammed.</p>
            <form onSubmit={handleNewsletter} className="flex gap-2 max-w-md mx-auto">
              <input type="email" placeholder="Your email" value={newsletterEmail} onChange={(e) => setNewsletterEmail(e.target.value)} disabled={newsletterLoading}
                className="flex-1 h-12 px-4 rounded-xl bg-white border" style={{ borderColor: "var(--gs-border)" }} data-testid="newsletter-email-input"/>
              <Button type="submit" disabled={newsletterLoading} className="bg-[var(--gs-ink)] hover:bg-black h-12 px-6 rounded-xl" data-testid="newsletter-submit-button">
                {newsletterLoading ? "Joining…" : "Join Getszy"}
              </Button>
            </form>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          FINAL CTA
      ═══════════════════════════════════════════════════════════════════════ */}
      <Section className="py-20 sm:py-28">
        <div className="gs-container text-center">
          <motion.div variants={fadeUp}>
            <h2 className="font-display text-3xl sm:text-5xl mb-4">Ready to start your Getszy journey?</h2>
            <p className="text-[var(--gs-muted)] mb-8 max-w-lg mx-auto">Shop premium essentials. Learn AI. Build your business — all in one place.</p>
            <div className="flex flex-wrap gap-4 justify-center">
              <Link to="/shop"><Button size="lg" className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-14 px-10 text-base rounded-2xl shadow-lg">
                Shop Now <ArrowRight className="h-4 w-4 ml-2"/>
              </Button></Link>
              <Link to="/dashboard"><Button size="lg" variant="outline" className="h-14 px-10 text-base rounded-2xl border-[var(--gs-border)]">
                Try Getszy AI
              </Button></Link>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════════
          TRUST BAR
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="border-t" style={{ borderColor: "var(--gs-border)" }}>
        <div className="gs-container py-6 flex flex-wrap justify-center gap-6 sm:gap-10 text-xs text-[var(--gs-muted)]">
          <span className="flex items-center gap-1.5"><Truck className="h-3.5 w-3.5"/> Free shipping on orders ₹1,000+</span>
          <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5"/> Secure payment</span>
          <span className="flex items-center gap-1.5"><RotateCcw className="h-3.5 w-3.5"/> Easy returns</span>
          <span className="flex items-center gap-1.5"><CreditCard className="h-3.5 w-3.5"/> Razorpay + UPI</span>
          <span className="flex items-center gap-1.5"><Zap className="h-3.5 w-3.5"/> Instant digital delivery</span>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          FOOTER
      ═══════════════════════════════════════════════════════════════════════ */}
      <footer className="border-t py-12" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
        <div className="gs-container">
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-8">
            <div className="lg:col-span-2">
              <div className="font-display text-2xl mb-2">getszy</div>
              <p className="text-xs text-[var(--gs-muted)] mb-4 max-w-xs">Shop. Learn. Build. Earn.<br/>Premium lifestyle products and powerful digital tools for women who do it all.</p>
              <div className="flex gap-3">
                {["Instagram", "YouTube", "Twitter"].map((s) => (
                  <span key={s} className="h-8 w-8 rounded-lg bg-[var(--gs-surface-2)] grid place-items-center text-xs font-semibold cursor-pointer hover:bg-[var(--gs-primary)] hover:text-white transition-colors">{s[0]}</span>
                ))}
              </div>
            </div>
            {[
              { title: "Shop", links: ["Fashion", "Jewellery", "Beauty", "Home", "Kids", "Gadgets"] },
              { title: "Digital", links: ["AI Tools", "Courses", "eBooks", "Business Tools"] },
              { title: "Company", links: ["About", "Support", "Privacy", "Terms"] },
            ].map((col) => (
              <div key={col.title}>
                <h4 className="font-display text-sm font-semibold mb-3">{col.title}</h4>
                <div className="space-y-2">
                  {col.links.map((l) => <div key={l} className="text-xs text-[var(--gs-muted)] hover:text-[var(--gs-primary-2)] cursor-pointer transition-colors">{l}</div>)}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-10 pt-6 border-t flex flex-col sm:flex-row justify-between items-center gap-4" style={{ borderColor: "var(--gs-border)" }}>
            <div className="text-xs text-[var(--gs-muted)]">© 2026 Getszy. All rights reserved.</div>
            <div className="text-xs text-[var(--gs-muted)]">Made with care for women who do it all.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
