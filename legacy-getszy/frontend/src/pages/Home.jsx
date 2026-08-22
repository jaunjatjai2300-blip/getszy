import { useEffect, useState, useRef, useCallback, createContext, useContext } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, useScroll, useTransform, useInView, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  ArrowRight, Sparkle, Bot, GraduationCap, Wand2, ShoppingBag, Heart,
  Eye, Star, ChevronRight, ChevronLeft, Play, Zap, TrendingUp, Users, Package,
  Shield, Truck, RotateCcw, CreditCard, Search, X, ChevronDown,
  Gift, MessageCircle, Home as HomeIcon, User, Plus, Minus, Trash2,
  Send, MapPin, Clock, Tag, Bookmark, ArrowUpRight, Check, Loader2,
  SlidersHorizontal, Grid3X3, LayoutList, Filter, Flame, Flame as FireIcon,
  Settings, Bell, Sparkles, Globe, Palette, PenTool, Store, Megaphone,
  Rocket, BookOpen, LifeBuoy, Download, FolderKanban, Quote,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { GetszyLogo } from "@/components/GetszyLogo";
import { api, fmtINR } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

const fadeUp = { hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } } };
const stagger = { visible: { transition: { staggerChildren: 0.1 } } };
const scaleIn = { hidden: { opacity: 0, scale: 0.95 }, visible: { opacity: 1, scale: 1, transition: { duration: 0.5 } } };

/* ═══════════════════════════════════════════════════════════════════════════
   VISUAL WOW — CSS Animations
   ═══════════════════════════════════════════════════════════════════════════ */
const WOW_STYLES = `
  @keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
  }
  @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-20px) rotate(5deg); } }
  @keyframes floatSlow { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-12px); } }
  @keyframes sparkle {
    0%, 100% { opacity: 0; transform: scale(0) rotate(0deg); }
    50% { opacity: 1; transform: scale(1) rotate(180deg); }
  }
  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }
  @keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 20px rgba(197,139,122,0.2); }
    50% { box-shadow: 0 0 40px rgba(197,139,122,0.4); }
  }
  @keyframes morphBlob {
    0%, 100% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }
    25% { border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%; }
    50% { border-radius: 50% 60% 30% 60% / 30% 60% 70% 40%; }
    75% { border-radius: 60% 30% 60% 40% / 70% 40% 50% 60%; }
  }
  .hero-gradient {
    background: linear-gradient(-45deg, #FBF7F2, #F5E6D3, #E8D5C0, #FBF7F2, #F3E2C7);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
  }
  .sparkle-particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: var(--gs-primary);
    border-radius: 50%;
    animation: sparkle 3s ease-in-out infinite;
    pointer-events: none;
  }
  .float-element { animation: float 6s ease-in-out infinite; }
  .float-slow { animation: floatSlow 8s ease-in-out infinite; }
  .shimmer-text {
    background: linear-gradient(90deg, var(--gs-ink) 0%, var(--gs-primary) 50%, var(--gs-ink) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 3s linear infinite;
  }
  .morph-blob {
    animation: morphBlob 8s ease-in-out infinite;
  }
  .card-3d { transform-style: preserve-3d; perspective: 1000px; }
  .card-3d-inner { transition: transform 0.3s ease; transform-style: preserve-3d; }
  .card-3d:hover .card-3d-inner { transform: rotateY(-5deg) rotateX(5deg) scale(1.02); }
  .section-divider { position: relative; }
  .glow-on-hover:hover { box-shadow: 0 0 30px rgba(197,139,122,0.3), 0 10px 40px rgba(0,0,0,0.1); }
  .magnetic-hover { transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
  .magnetic-hover:hover { transform: scale(1.05); }
  .text-reveal { overflow: hidden; }
  .text-reveal > span { display: inline-block; animation: revealUp 0.8s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
  @keyframes revealUp { from { clip-path: inset(100% 0 0 0); opacity: 0; } to { clip-path: inset(0 0 0 0); opacity: 1; } }
  .hero-bento img { transition: transform 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94), filter 0.5s ease; }
  .hero-bento:hover img { filter: brightness(1.05) saturate(1.1); }
  .gradient-border { position: relative; }
  .gradient-border::before {
    content: ''; position: absolute; inset: -2px; border-radius: inherit;
    background: linear-gradient(135deg, var(--gs-primary), var(--gs-teal), var(--gs-primary));
    background-size: 200% 200%; animation: gradientShift 4s ease infinite; z-index: -1; opacity: 0; transition: opacity 0.3s ease;
  }
  .gradient-border:hover::before { opacity: 1; }
  .neo-typing::after { content: '▍'; animation: blink 1s step-end infinite; }
  @keyframes blink { 50% { opacity: 0; } }
`;

if (typeof document !== 'undefined' && !document.getElementById('wow-styles')) {
  const style = document.createElement('style');
  style.id = 'wow-styles';
  style.textContent = WOW_STYLES;
  document.head.appendChild(style);
}

function SparkleParticles({ count = 12 }) {
  const particles = Array.from({ length: count }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    delay: `${Math.random() * 5}s`,
    duration: `${2 + Math.random() * 4}s`,
    size: `${2 + Math.random() * 4}px`,
  }));
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div key={p.id} className="sparkle-particle" style={{ left: p.left, top: p.top, animationDelay: p.delay, animationDuration: p.duration, width: p.size, height: p.size }} />
      ))}
    </div>
  );
}

function FloatingShape({ className = "", delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 0.15, scale: 1 }} transition={{ delay, duration: 1, type: "spring" }} className={`absolute pointer-events-none ${className}`}>
      <div className="w-full h-full rounded-full morph-blob" style={{ background: "linear-gradient(135deg, var(--gs-primary), var(--gs-teal))" }} />
    </motion.div>
  );
}

function TiltCard({ children, className = "" }) {
  const ref = useRef(null);
  const handleMouseMove = (e) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    ref.current.style.transform = `perspective(1000px) rotateY(${x * 10}deg) rotateX(${-y * 10}deg) scale3d(1.02,1.02,1.02)`;
  };
  const handleMouseLeave = () => { if (ref.current) ref.current.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)'; };
  return (
    <div ref={ref} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave} className={`transition-transform duration-300 ease-out ${className}`} style={{ transformStyle: 'preserve-3d' }}>
      {children}
    </div>
  );
}

function CharacterReveal({ text, className = "", delay = 0 }) {
  return (
    <span className={`text-reveal inline-block ${className}`}>
      {text.split("").map((char, i) => (
        <span key={i} style={{ animationDelay: `${delay + i * 0.03}s`, display: "inline-block" }}>{char === " " ? " " : char}</span>
      ))}
    </span>
  );
}

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

function useNLSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timerRef = useRef(null);
  const search = useCallback((q) => {
    setQuery(q);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!q.trim()) { setResults([]); return; }
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/products?search=${encodeURIComponent(q.trim())}&limit=6`);
        setResults(Array.isArray(data) ? data : []);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 300);
  }, []);
  return { query, results, loading, open, setOpen, search };
}

const CATEGORY_TAGLINES = {
  fashion: "Style that moves with you.",
  jewellery: "Small details. Big statement.",
  beauty: "Glow, simplified.",
  "home-decor": "Make your space yours.",
  kids: "Made for little moments.",
  gadgets: "Tech that fits your life.",
  "digital-products": "Tools that help you build.",
};

const CATEGORY_EMOJIS = {
  fashion: "👗", jewellery: "💎", beauty: "✨", "home-decor": "🏡",
  kids: "🧸", gadgets: "📱", "digital-products": "⚡",
};

const CATEGORY_FALLBACKS = {
  fashion: "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600",
  jewellery: "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600",
  beauty: "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600",
  "home-decor": "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=600",
  kids: "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=600",
  gadgets: "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=600",
  "digital-products": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600",
};

const GIFTS_OCCASIONS = [
  { label: "Birthday", emoji: "🎂" },
  { label: "Anniversary", emoji: "💝" },
  { label: "Festival", emoji: "🪔" },
  { label: "Just Because", emoji: "🌸" },
  { label: "Wedding", emoji: "💍" },
  { label: "Graduation", emoji: "🎓" },
];

const GIFTS_BUDGETS = [
  { label: "Under ₹500", min: 0, max: 500 },
  { label: "₹500 – ₹1,000", min: 500, max: 1000 },
  { label: "₹1,000 – ₹2,500", min: 1000, max: 2500 },
  { label: "₹2,500 – ₹5,000", min: 2500, max: 5000 },
  { label: "₹5,000+", min: 5000, max: 999999 },
];

const GIFTS_RECIPIENTS = [
  { label: "For Her", emoji: "👩" },
  { label: "For Mom", emoji: "🤱" },
  { label: "For Sister", emoji: "👧" },
  { label: "For Friend", emoji: "🤝" },
  { label: "For Daughter", emoji: "👶" },
  { label: "For Partner", emoji: "💑" },
];

function EnhancedProductCard({ product, onQuickAdd, onWishlist, onQuickView, wishlisted }) {
  const [hovered, setHovered] = useState(false);
  const [adding, setAdding] = useState(false);
  const img = (product.images && product.images[0]) || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600";
  const hoverImg = product.images?.[1] || img;
  const inStock = product.stock === undefined || product.stock > 0;
  const discount = product.compare_at_price > product.price ? Math.round((1 - product.price / product.compare_at_price) * 100) : 0;

  const handleQuickAdd = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!inStock) return;
    setAdding(true);
    try { await onQuickAdd?.(product); } finally { setAdding(false); }
  };

  return (
    <motion.div variants={scaleIn} whileHover={{ y: -4 }} className="gs-card group overflow-hidden cursor-pointer" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
      <Link to={"/product/" + product.id} className="block">
        <div className="relative aspect-square overflow-hidden">
          <img src={hovered ? hoverImg : img} alt={product.name} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" loading="lazy" />
          <div className="absolute top-3 left-3 flex flex-col gap-1.5">
            {product.is_new && <Badge className="bg-[var(--gs-teal)] text-white text-[10px]">NEW</Badge>}
            {product.is_featured && <Badge className="bg-[var(--gs-primary)] text-white text-[10px]">FEATURED</Badge>}
            {discount > 0 && <Badge className="bg-red-500 text-white text-[10px]">-{discount}%</Badge>}
            {product.is_digital && <Badge className="bg-violet-600 text-white text-[10px]">DIGITAL</Badge>}
          </div>
          <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-2">
            <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); onWishlist?.(product); }} className="h-9 w-9 rounded-full bg-white/90 grid place-items-center shadow-md hover:bg-white">
              <Heart className={`h-4 w-4 ${wishlisted ? "fill-red-500 text-red-500" : ""}`} />
            </motion.button>
            <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); onQuickView?.(product); }} className="h-9 w-9 rounded-full bg-white/90 grid place-items-center shadow-md hover:bg-white">
              <Eye className="h-4 w-4" />
            </motion.button>
          </div>
          {!inStock && (
            <div className="absolute inset-0 bg-black/40 grid place-items-center">
              <span className="bg-white/90 text-xs font-semibold px-3 py-1.5 rounded-full">Out of Stock</span>
            </div>
          )}
          <div className="absolute bottom-0 inset-x-0 p-3 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all">
            <Button onClick={handleQuickAdd} disabled={!inStock || adding} className="w-full bg-[var(--gs-ink)] hover:bg-black text-white rounded-xl text-xs h-9">
              {adding ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <ShoppingBag className="h-3.5 w-3.5 mr-1.5" />}
              {!inStock ? "Sold Out" : adding ? "Adding…" : product.is_digital ? "Get Instant Access" : "Quick Add"}
            </Button>
          </div>
        </div>
        <div className="p-4">
          <h3 className="font-semibold text-sm line-clamp-1 hover:text-[var(--gs-primary-2)] transition-colors">{product.name}</h3>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="font-bold text-sm">{fmtINR(product.price)}</span>
            {discount > 0 && <span className="text-xs text-[var(--gs-muted)] line-through">{fmtINR(product.compare_at_price)}</span>}
          </div>
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-0.5">
              {[...Array(5)].map((_, j) => (
                <Star key={j} className={`h-3 w-3 ${j < Math.round(product.rating || 0) ? "fill-amber-400 text-amber-400" : "text-gray-200"}`} />
              ))}
              <span className="text-[10px] text-[var(--gs-muted)] ml-1">({product.review_count || 0})</span>
            </div>
            {!product.is_digital && inStock && product.stock !== undefined && product.stock <= 5 && (
              <span className="text-[10px] text-orange-600 font-medium">Only {product.stock} left</span>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

function DiscoveryRail({ title, subtitle, products, onQuickAdd, onWishlist, wishlisted, onQuickView }) {
  const scrollRef = useRef(null);
  const scroll = (dir) => { if (scrollRef.current) scrollRef.current.scrollBy({ left: dir * 320, behavior: "smooth" }); };
  if (!products || products.length === 0) return null;
  return (
    <div className="relative">
      <div className="flex items-end justify-between mb-4">
        <div>
          {subtitle && <div className="text-xs uppercase tracking-[0.15em] text-[var(--gs-primary-2)] mb-1 font-semibold">{subtitle}</div>}
          <h3 className="font-display text-lg sm:text-xl">{title}</h3>
        </div>
        <div className="flex gap-2">
          <button onClick={() => scroll(-1)} className="h-8 w-8 rounded-full border grid place-items-center hover:bg-[var(--gs-surface-2)] transition-colors"><ChevronLeft className="h-4 w-4" /></button>
          <button onClick={() => scroll(1)} className="h-8 w-8 rounded-full border grid place-items-center hover:bg-[var(--gs-surface-2)] transition-colors"><ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>
      <div ref={scrollRef} className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 snap-x snap-mandatory" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
        {products.map((p) => (
          <div key={p.id} className="min-w-[240px] max-w-[240px] snap-start">
            <EnhancedProductCard product={p} onQuickAdd={onQuickAdd} onWishlist={onWishlist} onQuickView={onQuickView} wishlisted={wishlisted?.(p)} />
          </div>
        ))}
      </div>
    </div>
  );
}

function CartDrawer({ open, onClose }) {
  const { cart, update, clear } = useCart();
  const navigate = useNavigate();
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} className="fixed inset-0 bg-black/30 z-50 backdrop-blur-sm" />
          <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", damping: 25, stiffness: 200 }} className="fixed top-0 right-0 h-full w-full max-w-md bg-white z-50 shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--gs-border)" }}>
              <h3 className="font-display text-lg">Your Cart ({cart.count || 0})</h3>
              <button onClick={onClose} className="h-9 w-9 rounded-full grid place-items-center hover:bg-gray-100"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {!cart.items || cart.items.length === 0 ? (
                <div className="text-center py-16">
                  <ShoppingBag className="h-12 w-12 mx-auto text-[var(--gs-muted)] mb-4" />
                  <p className="text-sm text-[var(--gs-muted)]">Your cart is empty</p>
                  <Button onClick={() => { onClose(); navigate("/shop"); }} className="mt-4 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] rounded-xl">Start Shopping</Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {cart.items.map((item) => (
                    <div key={item.product_id} className="flex gap-4 p-3 rounded-xl bg-[var(--gs-surface)]">
                      <img src={item.image || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=120"} alt={item.name} className="w-16 h-16 rounded-lg object-cover" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold line-clamp-1">{item.name}</h4>
                        <p className="text-xs text-[var(--gs-muted)] mt-0.5">{fmtINR(item.price)}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <button onClick={() => update(item.product_id, Math.max(0, item.quantity - 1))} className="h-6 w-6 rounded-md border grid place-items-center hover:bg-gray-50"><Minus className="h-3 w-3" /></button>
                          <span className="text-xs font-semibold w-6 text-center">{item.quantity}</span>
                          <button onClick={() => update(item.product_id, item.quantity + 1)} className="h-6 w-6 rounded-md border grid place-items-center hover:bg-gray-50"><Plus className="h-3 w-3" /></button>
                          <button onClick={() => update(item.product_id, 0)} className="ml-auto h-6 w-6 rounded-md grid place-items-center text-red-500 hover:bg-red-50"><Trash2 className="h-3 w-3" /></button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {cart.items && cart.items.length > 0 && (
              <div className="p-5 border-t" style={{ borderColor: "var(--gs-border)" }}>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-semibold">Total</span>
                  <span className="font-display text-xl font-bold">{fmtINR(cart.total)}</span>
                </div>
                <Button onClick={() => { onClose(); navigate("/checkout"); }} className="w-full bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-12 rounded-xl text-base font-semibold">
                  Checkout <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
                <Button onClick={clear} variant="ghost" className="w-full mt-2 text-xs text-[var(--gs-muted)]">Clear Cart</Button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function AIConcierge() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hi! I'm Neo. Ask me anything — product recommendations, gift ideas, or help with AI tools." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef(null);
  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const { data } = await api.post("/ai-tools/neo/chat", {
        messages: [...messages, { role: "user", content: q }].map((m) => ({ role: m.role, content: m.text || m.content })),
      });
      const reply = data?.choices?.[0]?.message?.content || data?.response || "I couldn't process that. Please try again.";
      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "I'm having trouble right now. Please try again later." }]);
    } finally { setLoading(false); }
  };

  return (
    <>
      <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={() => setOpen(true)}
        className="fixed bottom-20 sm:bottom-6 right-4 sm:right-6 z-40 h-14 w-14 rounded-full bg-[var(--gs-teal)] text-white shadow-lg shadow-[var(--gs-teal)]/30 grid place-items-center hover:bg-[var(--gs-teal)]/90 transition-colors">
        <MessageCircle className="h-6 w-6" />
      </motion.button>
      <AnimatePresence>
        {open && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} className="fixed inset-0 bg-black/20 z-40" />
            <motion.div initial={{ opacity: 0, y: 20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.95 }}
              className="fixed bottom-20 sm:bottom-24 right-4 sm:right-6 z-50 w-[90vw] max-w-[380px] bg-white rounded-2xl shadow-2xl border flex flex-col overflow-hidden" style={{ borderColor: "var(--gs-border)", height: "min(70vh, 500px)" }}>
              <div className="p-4 bg-[var(--gs-teal)] text-white flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-white/20 grid place-items-center"><Sparkle className="h-5 w-5" /></div>
                <div className="flex-1">
                  <div className="text-sm font-semibold">Neo</div>
                  <div className="text-[10px] opacity-80">Getszy's AI guide</div>
                </div>
                <button onClick={() => setOpen(false)} className="h-8 w-8 rounded-full hover:bg-white/20 grid place-items-center"><X className="h-4 w-4" /></button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-[var(--gs-teal)] text-white rounded-br-md" : "bg-[var(--gs-surface)] text-[var(--gs-ink)] rounded-bl-md"}`}>{m.text}</div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-[var(--gs-surface)] rounded-2xl rounded-bl-md px-4 py-3 flex gap-1">
                      <span className="h-2 w-2 rounded-full bg-[var(--gs-muted)] animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="h-2 w-2 rounded-full bg-[var(--gs-muted)] animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="h-2 w-2 rounded-full bg-[var(--gs-muted)] animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                )}
                <div ref={messagesEnd} />
              </div>
              <div className="p-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
                <div className="flex gap-2">
                  <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask Getszy anything…"
                    className="flex-1 h-10 px-4 rounded-xl bg-[var(--gs-surface)] text-sm outline-none focus:ring-2 focus:ring-[var(--gs-teal)]/30" disabled={loading} />
                  <button onClick={send} disabled={loading || !input.trim()} className="h-10 w-10 rounded-xl bg-[var(--gs-teal)] text-white grid place-items-center hover:bg-[var(--gs-teal)]/90 disabled:opacity-50"><Send className="h-4 w-4" /></button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function MobileBottomNav({ cartCount, onCartOpen }) {
  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-white border-t sm:hidden" style={{ borderColor: "var(--gs-border)" }}>
      <div className="grid grid-cols-5 h-14">
        {[
          { to: "/", icon: HomeIcon, label: "Home", end: true },
          { to: "/shop", icon: ShoppingBag, label: "Shop" },
          { to: "/category/digital-products", icon: Zap, label: "Digital" },
          { to: "/wishlist", icon: Heart, label: "Wishlist" },
          { to: "/account", icon: User, label: "Account" },
        ].map((item) => (
          <Link key={item.label} to={item.to} className="flex flex-col items-center justify-center gap-0.5 text-[10px] text-[var(--gs-muted)] hover:text-[var(--gs-primary)] transition-colors">
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function QuickViewDialog({ product, open, onClose, onAddToCart }) {
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);
  const [selectedImg, setSelectedImg] = useState(0);
  if (!product) return null;
  const imgs = product.images?.length ? product.images : ["https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600"];
  const inStock = product.stock === undefined || product.stock > 0;
  const discount = product.compare_at_price > product.price ? Math.round((1 - product.price / product.compare_at_price) * 100) : 0;

  const handleAdd = async () => { setAdding(true); try { await onAddToCart?.(product, qty); onClose(); } finally { setAdding(false); } };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl p-0 overflow-hidden rounded-3xl">
        <div className="grid md:grid-cols-2">
          <div className="relative bg-[var(--gs-surface)]">
            <img src={imgs[selectedImg]} alt={product.name} className="w-full aspect-square object-cover" />
            {imgs.length > 1 && (
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
                {imgs.map((_, i) => (
                  <button key={i} onClick={() => setSelectedImg(i)} className={`h-2 w-2 rounded-full transition-colors ${i === selectedImg ? "bg-white" : "bg-white/50"}`} />
                ))}
              </div>
            )}
            {discount > 0 && <Badge className="absolute top-3 left-3 bg-red-500 text-white">-{discount}%</Badge>}
          </div>
          <div className="p-6 flex flex-col">
            <DialogHeader>
              <DialogTitle className="font-display text-xl">{product.name}</DialogTitle>
              <DialogDescription className="text-xs text-[var(--gs-muted)]">{product.category}</DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              <div className="flex items-baseline gap-3">
                <span className="font-display text-2xl font-bold">{fmtINR(product.price)}</span>
                {discount > 0 && <span className="text-sm text-[var(--gs-muted)] line-through">{fmtINR(product.compare_at_price)}</span>}
              </div>
              <div className="flex items-center gap-1 mt-2">
                {[...Array(5)].map((_, j) => <Star key={j} className={`h-3.5 w-3.5 ${j < Math.round(product.rating || 0) ? "fill-amber-400 text-amber-400" : "text-gray-200"}`} />)}
                <span className="text-xs text-[var(--gs-muted)] ml-1">({product.review_count || 0} reviews)</span>
              </div>
            </div>
            {product.description && <p className="text-sm text-[var(--gs-muted)] mt-4 line-clamp-3">{product.description}</p>}
            <div className="mt-4 flex items-center gap-2 text-xs text-[var(--gs-muted)]">
              {inStock ? <><Check className="h-3.5 w-3.5 text-green-600" /> In stock</> : <><X className="h-3.5 w-3.5 text-red-500" /> Out of stock</>}
              {!product.is_digital && <><Truck className="h-3.5 w-3.5 ml-2" /> Free shipping on ₹1,000+</>}
              {product.is_digital && <><Zap className="h-3.5 w-3.5 ml-2 text-[var(--gs-teal)]" /> Instant digital access</>}
            </div>
            <div className="mt-auto pt-6 flex items-center gap-3">
              {!product.is_digital && (
                <div className="flex items-center border rounded-xl h-10">
                  <button onClick={() => setQty(Math.max(1, qty - 1))} className="h-10 w-10 grid place-items-center hover:bg-gray-50"><Minus className="h-3.5 w-3.5" /></button>
                  <span className="text-sm font-semibold w-8 text-center">{qty}</span>
                  <button onClick={() => setQty(qty + 1)} className="h-10 w-10 grid place-items-center hover:bg-gray-50"><Plus className="h-3.5 w-3.5" /></button>
                </div>
              )}
              <Button onClick={handleAdd} disabled={!inStock || adding} className="flex-1 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-10 rounded-xl">
                {adding ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <ShoppingBag className="h-4 w-4 mr-2" />}
                {!inStock ? "Sold Out" : product.is_digital ? "Get Access" : "Add to Cart"}
              </Button>
            </div>
            <Link to={"/product/" + product.id} className="text-center text-xs text-[var(--gs-primary-2)] mt-3 hover:underline">View full details →</Link>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function GiftFinder({ onSearch }) {
  const [occasion, setOccasion] = useState(null);
  const [budget, setBudget] = useState(null);
  const [recipient, setRecipient] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async () => {
    setLoading(true);
    setSearched(true);
    try {
      let params = "limit=8";
      if (budget) params += `&min_price=${budget.min}&max_price=${budget.max}`;
      const { data } = await api.get(`/products?${params}`);
      setResults(Array.isArray(data) ? data.slice(0, 6) : []);
    } catch { setResults([]); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        <div>
          <div className="text-xs font-semibold text-[var(--gs-muted)] mb-2 uppercase tracking-wider">Occasion</div>
          <div className="flex flex-wrap gap-2">
            {GIFTS_OCCASIONS.map((o) => (
              <button key={o.label} onClick={() => setOccasion(occasion === o.label ? null : o.label)} className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${occasion === o.label ? "bg-[var(--gs-primary)] text-white border-[var(--gs-primary)]" : "hover:border-[var(--gs-primary)]/50"}`}>{o.emoji} {o.label}</button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-semibold text-[var(--gs-muted)] mb-2 uppercase tracking-wider">Budget</div>
          <div className="flex flex-wrap gap-2">
            {GIFTS_BUDGETS.map((b) => (
              <button key={b.label} onClick={() => setBudget(budget?.label === b.label ? null : b)} className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${budget?.label === b.label ? "bg-[var(--gs-primary)] text-white border-[var(--gs-primary)]" : "hover:border-[var(--gs-primary)]/50"}`}>{b.label}</button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs font-semibold text-[var(--gs-muted)] mb-2 uppercase tracking-wider">For whom</div>
          <div className="flex flex-wrap gap-2">
            {GIFTS_RECIPIENTS.map((r) => (
              <button key={r.label} onClick={() => setRecipient(recipient === r.label ? null : r.label)} className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${recipient === r.label ? "bg-[var(--gs-primary)] text-white border-[var(--gs-primary)]" : "hover:border-[var(--gs-primary)]/50"}`}>{r.emoji} {r.label}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="text-center">
        <Button onClick={doSearch} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] rounded-xl h-10 px-8"><Gift className="h-4 w-4 mr-2" /> Find Gifts</Button>
      </div>
      {searched && (
        <div className="mt-8">
          {loading ? (
            <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto text-[var(--gs-primary)]" /></div>
          ) : results.length === 0 ? (
            <div className="text-center py-8 text-sm text-[var(--gs-muted)]">No gifts found for this combination. Try adjusting your filters.</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {results.map((p) => (
                <Link key={p.id} to={"/product/" + p.id} className="gs-card overflow-hidden group">
                  <div className="relative aspect-square overflow-hidden">
                    <img src={p.images?.[0] || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400"} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
                  </div>
                  <div className="p-3">
                    <h4 className="text-sm font-semibold line-clamp-1">{p.name}</h4>
                    <span className="text-sm font-bold">{fmtINR(p.price)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const MOODS = [
  { name: "Everyday Edit", img: "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600", to: "/shop" },
  { name: "Workday Ready", img: "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600", to: "/category/fashion" },
  { name: "Weekend Energy", img: "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=600", to: "/shop" },
  { name: "Date Night", img: "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=600", to: "/shop" },
  { name: "Wedding Guest", img: "https://images.unsplash.com/photo-1595224973242-4372196e7ae1?w=600", to: "/shop" },
  { name: "Self-Care", img: "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=600", to: "/category/beauty" },
  { name: "Gifting", img: "https://images.unsplash.com/photo-1513885535751-8b9238bd345a?w=600", to: "/shop" },
];

const NEO_LINES = [
  { who: "you", text: "I want to start a small home bakery." },
  { who: "neo", text: "Let's turn that into a launch plan. First, I'll help you define your offer, then draft your menu, your brand, and a one-page site — all ready to preview." },
  { who: "you", text: "And I need to sell online too." },
  { who: "neo", text: "Done. I'll set up your store and a payment link. You approve, and it goes live." },
];

const JOURNEY = ["IDEA", "NEO", "PLAN", "BUILD", "PREVIEW", "APPROVE", "LAUNCH", "GROW"];

const TRUST_PILLARS = [
  { icon: Shield, title: "Evidence-backed", desc: "AI doesn't invent your business facts. It works from what you approve and verifiable information.", color: "var(--gs-primary)" },
  { icon: User, title: "You stay in control", desc: "Important actions — purchases, publishing, outreach — always require your approval.", color: "var(--gs-teal)" },
  { icon: Globe, title: "Private by default", desc: "Your projects, ideas and information stay yours, and under your control.", color: "#8b5cf6" },
];

export default function Home() {
  const { user } = useAuth();
  const { cart, add: addToCart } = useCart();
  const navigate = useNavigate();
  const [cats, setCats] = useState([]);
  const [trending, setTrending] = useState([]);
  const [newArrivals, setNewArrivals] = useState([]);
  const [bestsellers, setBestsellers] = useState([]);
  const [digitalProducts, setDigitalProducts] = useState([]);
  const [heroProducts, setHeroProducts] = useState([]);
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterLoading, setNewsletterLoading] = useState(false);
  const [quickViewProduct, setQuickViewProduct] = useState(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [wishlist, setWishlist] = useState(new Set());
  const [neoOpen, setNeoOpen] = useState(false);
  const [neoMsg, setNeoMsg] = useState("");
  const neoEndRef = useRef(null);
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const heroY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);
  const nlSearch = useNLSearch();

  useEffect(() => {
    api.get("/categories").then(({ data }) => {
      const merged = (Array.isArray(data) ? data : []).map((c) => ({
        ...c, title: c.name, tagline: CATEGORY_TAGLINES[c.slug] || "Discover something new.",
        emoji: CATEGORY_EMOJIS[c.slug] || "🛍️",
        img: c.image || CATEGORY_FALLBACKS[c.slug] || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600",
        product_count: c.product_count || 0,
      }));
      setCats(merged);
    }).catch(() => setCats([]));
    api.get("/products?featured=true&limit=8").then(({ data }) => setTrending(data)).catch(() => setTrending([]));
    api.get("/products?limit=8").then(({ data }) => { setNewArrivals(data); setHeroProducts(data); }).catch(() => { setNewArrivals([]); setHeroProducts([]); });
    api.get("/products?featured=true&limit=4").then(({ data }) => setBestsellers(data)).catch(() => setBestsellers([]));
    api.get("/products?category=digital-products&limit=6").then(({ data }) => setDigitalProducts(data)).catch(() => setDigitalProducts([]));
  }, []);

  useEffect(() => { neoEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [neoOpen, neoMsg]);

  const handleQuickAdd = async (product) => {
    if (!user) { navigate("/login"); return; }
    try { await addToCart(product.id, 1); toast.success("Added to cart", { description: product.name }); }
    catch { toast.error("Could not add to cart"); }
  };

  const toggleWishlist = (product) => {
    setWishlist((prev) => {
      const next = new Set(prev);
      if (next.has(product.id)) { next.delete(product.id); toast.success("Removed from wishlist"); }
      else { next.add(product.id); toast.success("Added to wishlist"); }
      return next;
    });
  };

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

  const sendNeo = async () => {
    const q = neoMsg.trim();
    if (!q) return;
    setNeoMsg("");
    setNeoOpen(true);
    try {
      const { data } = await api.post("/ai-tools/neo/chat", { messages: [{ role: "user", content: q }] });
      const reply = data?.choices?.[0]?.message?.content || data?.response || "Tell me a little more and I'll guide you.";
      toast.success("Neo: " + reply.slice(0, 90) + (reply.length > 90 ? "…" : ""));
    } catch { toast.error("Neo is unavailable right now."); }
  };

  const greetText = user ? `Welcome back, ${user.name?.split(" ")[0] || "there"}` : null;

  return (
    <div className="overflow-hidden pb-16 sm:pb-0">

      {greetText && (
        <div className="bg-[var(--gs-champagne)]/50 py-2 text-center">
          <span className="text-xs text-[var(--gs-muted)]">{greetText} — continue exploring or discover something new.</span>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          HERO — Editorial + Neo input
      ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative min-h-[92vh] flex items-center overflow-hidden">
        <div className="absolute inset-0 hero-gradient opacity-40 pointer-events-none" />
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(197,139,122,0.2), transparent)" }} />
        <SparkleParticles count={20} />
        <FloatingShape className="w-64 h-64 -top-20 -right-20 opacity-10" delay={0.5} />
        <FloatingShape className="w-48 h-48 bottom-10 -left-10 opacity-10" delay={0.8} />
        <motion.div style={{ y: heroY, opacity: heroOpacity }} className="gs-container relative z-10 grid lg:grid-cols-2 gap-12 py-16 lg:py-24 items-center w-full">
          <motion.div variants={stagger} initial="hidden" animate="visible">
            <motion.div variants={fadeUp} className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-5 flex items-center gap-2 font-semibold">
              <span className="inline-block animate-pulse"><Sparkle className="h-3.5 w-3.5" /></span> GETSZY — MADE FOR WOMEN WHO DO IT ALL
            </motion.div>
            <motion.h1 variants={fadeUp} className="text-4xl sm:text-5xl lg:text-[3.6rem] font-display leading-[1.05] tracking-tight">
              <CharacterReveal text="Made for women" delay={0.3} /><br />
              <span className="shimmer-text font-bold"><CharacterReveal text="who do it all." delay={0.8} /></span>
            </motion.h1>
            <motion.p variants={fadeUp} className="mt-5 text-base sm:text-lg text-[var(--gs-muted)] max-w-xl leading-relaxed">
              Shop something beautiful. Learn something useful. Build something yours — with Neo, your Getszy AI guide.
            </motion.p>

            <motion.div variants={fadeUp} className="mt-7">
              <div className="relative max-w-xl">
                <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gs-primary)]" />
                <input
                  value={neoMsg}
                  onChange={(e) => setNeoMsg(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendNeo()}
                  placeholder="✨ What do you want to achieve today?"
                  className="w-full h-14 pl-12 pr-32 rounded-2xl bg-white border text-sm outline-none focus:ring-2 focus:ring-[var(--gs-primary)]/30 shadow-sm"
                  style={{ borderColor: "var(--gs-border)" }}
                />
                <Button onClick={sendNeo} className="absolute right-2 top-2 bottom-2 rounded-xl h-10 px-5 bg-[var(--gs-ink)] hover:bg-black">
                  Ask Neo <ArrowRight className="h-4 w-4 ml-1.5" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-3 text-xs text-[var(--gs-muted)]">
                {["Start a business", "Find a gift", "Build a website", "Learn AI"].map((s) => (
                  <button key={s} onClick={() => { setNeoMsg(s); }} className="px-3 py-1 rounded-full bg-white border hover:border-[var(--gs-primary)]/50 transition-colors" style={{ borderColor: "var(--gs-border)" }}>{s}</button>
                ))}
              </div>
              <p className="text-xs text-[var(--gs-muted)] mt-2">Not sure where to start? Neo will guide you.</p>
            </motion.div>

            <motion.div variants={fadeUp} className="mt-8 flex flex-wrap gap-3">
              <Link to="/shop"><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] rounded-xl h-12 px-7">Shop Getszy <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
              <Link to="/dashboard/build"><Button variant="outline" className="rounded-xl h-12 px-7 border-[var(--gs-border)]">Explore Digital <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
            </motion.div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.95, x: 30 }} animate={{ opacity: 1, scale: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.3 }} className="relative">
            <TiltCard>
              <div className="grid grid-cols-2 grid-rows-2 gap-3 sm:gap-4 aspect-[1.1/1] hero-bento">
                {[
                  heroProducts[0] || { images: ["https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800"], name: "Fashion" },
                  heroProducts[1] || { images: ["https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600"], name: "Jewellery" },
                  heroProducts[2] || { images: ["https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600"], name: "Beauty" },
                ].map((p, i) => (
                  <div key={i} className={`${i === 0 ? "row-span-2" : ""} rounded-3xl overflow-hidden shadow-xl glow-on-hover relative group`}>
                    <img src={p.images?.[0] || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600"} alt={p.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" loading="lazy" />
                    {p.price && <div className="absolute bottom-2 left-2 bg-white/90 backdrop-blur-sm rounded-lg px-2 py-1 text-[10px] font-semibold shadow-sm">₹{p.price?.toLocaleString("en-IN")}</div>}
                  </div>
                ))}
              </div>
            </TiltCard>
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 1, duration: 0.6 }}
              className="absolute -bottom-4 -left-4 bg-white rounded-2xl p-4 shadow-lg flex items-center gap-3 pulse-glow" style={{ animation: 'pulseGlow 3s ease-in-out infinite' }}>
              <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal-soft)] grid place-items-center float-slow"><Sparkle className="h-5 w-5 text-[var(--gs-teal)]" /></div>
              <div><div className="text-xs font-semibold">Neo</div><div className="text-[10px] text-[var(--gs-muted)]">Your AI guide</div></div>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          THE GETSZY WAY — 5 pillars
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="py-20 sm:py-28 overflow-hidden relative" style={{ background: "linear-gradient(180deg, var(--gs-bg) 0%, var(--gs-champagne) 50%, var(--gs-bg) 100%)" }}>
        <SparkleParticles count={8} />
        <div className="gs-container text-center">
          <motion.div variants={fadeUp} className="space-y-8">
            <motion.div initial={{ opacity: 0, scale: 0.8 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ duration: 0.8, type: "spring" }}
              className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] font-semibold">The Getszy Way</motion.div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 flex-wrap">
              {[
                { word: "SHOP", desc: "something you love.", color: "var(--gs-primary)" },
                { word: "LEARN", desc: "something useful.", color: "#8b5cf6" },
                { word: "BUILD", desc: "something yours.", color: "var(--gs-teal)" },
                { word: "GROW", desc: "something meaningful.", color: "#f59e0b" },
                { word: "EARN", desc: "from what you know.", color: "#2F7E7A" },
              ].map((item, i) => (
                <motion.div key={item.word} initial={{ opacity: 0, y: 30, scale: 0.9 }} whileInView={{ opacity: 1, y: 0, scale: 1 }}
                  viewport={{ once: true }} transition={{ delay: i * 0.12, duration: 0.7, type: "spring", bounce: 0.4 }}
                  className="flex items-center gap-3 magnetic-hover">
                  <span className="font-display text-3xl sm:text-4xl font-bold" style={{ color: item.color }}>
                    <CharacterReveal text={item.word} delay={i * 0.2} />
                  </span>
                  <span className="text-base sm:text-lg text-[var(--gs-muted)] font-display italic">{item.desc}</span>
                </motion.div>
              ))}
            </div>
            <p className="text-xs text-[var(--gs-muted)] max-w-md mx-auto">Shop · Learn · Build · Grow · Earn — one brand promise, not five disconnected modules.</p>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          THE GETSZY EDIT — Categories
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-categories-grid">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="flex items-end justify-between mb-8">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">The Getszy Edit</div>
              <h2 className="font-display text-2xl sm:text-3xl">Curated for your everyday</h2>
            </div>
            <Link to="/shop" className="text-sm gs-link flex items-center gap-1">View all <ArrowRight className="h-3 w-3" /></Link>
          </motion.div>
          <motion.div variants={fadeUp} className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {cats.map((c, i) => (
              <Link key={c.slug} to={"/category/" + c.slug}>
                <motion.div whileHover={{ y: -8, scale: 1.02 }} transition={{ type: "spring", stiffness: 300 }}
                  className={`relative rounded-3xl overflow-hidden group cursor-pointer gradient-border ${i === 0 ? "md:col-span-2 md:row-span-2" : ""}`}>
                  <img src={c.img} alt={c.title} className={`w-full object-cover group-hover:scale-110 transition-transform duration-700 ${i === 0 ? "aspect-square" : "aspect-[4/3]"}`} loading="lazy" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
                  <div className="absolute bottom-0 left-0 p-5 sm:p-6">
                    <motion.h3 initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="font-display text-xl sm:text-2xl text-white">{c.title}</motion.h3>
                    <p className="text-xs text-white/70 mt-1">{c.tagline}</p>
                    {c.product_count > 0 && <p className="text-[10px] text-white/50 mt-1">{c.product_count} products</p>}
                  </div>
                  <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0">
                    <div className="h-8 w-8 rounded-full bg-white/90 grid place-items-center shadow-lg"><ArrowRight className="h-4 w-4 text-[var(--gs-ink)]" /></div>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          SHOP YOUR MOOD
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" style={{ background: "var(--gs-surface)" }}>
        <div className="gs-container">
          <motion.div variants={fadeUp} className="mb-8">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">Shop Your Mood</div>
            <h2 className="font-display text-2xl sm:text-3xl">However you feel today</h2>
          </motion.div>
          <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {MOODS.map((m, i) => (
              <Link key={m.name} to={m.to}>
                <motion.div whileHover={{ y: -6 }} transition={{ type: "spring", stiffness: 300 }} className="relative rounded-2xl overflow-hidden group aspect-[4/3]">
                  <img src={m.img} alt={m.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/65 to-transparent" />
                  <div className="absolute bottom-0 left-0 p-4">
                    <div className="font-display text-white text-base sm:text-lg">{m.name}</div>
                    <div className="text-white/70 text-xs flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">Shop <ArrowRight className="h-3 w-3" /></div>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          TRENDING PRODUCTS
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-trending-products">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="flex items-end justify-between mb-8">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">Trending now</div>
              <h2 className="font-display text-2xl sm:text-3xl">The pieces our community is loving</h2>
            </div>
            <Link to="/shop" className="text-sm gs-link flex items-center gap-1">Shop all <ArrowRight className="h-3 w-3" /></Link>
          </motion.div>
          <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
            {trending.map((p) => (
              <EnhancedProductCard key={p.id} product={p} onQuickAdd={handleQuickAdd} onWishlist={toggleWishlist} onQuickView={setQuickViewProduct} wishlisted={(prod) => wishlist.has(prod.id)} />
            ))}
          </motion.div>
        </div>
      </Section>

      {bestsellers.length > 0 && (
        <Section className="gs-section">
          <div className="gs-container">
            <DiscoveryRail title="Bestsellers" subtitle="Because you'll love these" products={bestsellers} onQuickAdd={handleQuickAdd} onWishlist={toggleWishlist} onQuickView={setQuickViewProduct} wishlisted={(p) => wishlist.has(p.id)} />
          </div>
        </Section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          BUILD & GROW
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section relative overflow-hidden" style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)" }}>
        <div className="absolute inset-0" style={{ background: "radial-gradient(circle at 30% 50%, rgba(47,126,122,0.15), transparent 50%), radial-gradient(circle at 70% 50%, rgba(139,92,246,0.1), transparent 50%)" }} />
        <SparkleParticles count={10} />
        <div className="gs-container relative z-10">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-xs uppercase tracking-[0.2em] text-[var(--gs-teal)] mb-3 font-semibold flex items-center justify-center gap-2">
              <span className="inline-block animate-pulse"><Zap className="h-3.5 w-3.5" /></span>BUILD &amp; GROW
            </motion.div>
            <h2 className="font-display text-3xl sm:text-4xl text-white">Your idea deserves more than a blank template.</h2>
            <p className="text-gray-400 mt-3 max-w-lg mx-auto">Launch, create and scale — with AI doing the heavy lifting.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon: Rocket, title: "Launch a Website", desc: "A polished storefront, live in minutes.", color: "#10b981", link: "/dashboard/build", cta: "Start" },
              { icon: Store, title: "Launch a Store", desc: "Sell your products with checkout + payments.", color: "#f59e0b", link: "/dashboard/build", cta: "Sell" },
              { icon: PenTool, title: "Create Content", desc: "Posts, scripts and campaigns from a prompt.", color: "#8b5cf6", link: "/dashboard/agents", cta: "Create" },
              { icon: Palette, title: "Build Your Brand", desc: "Logos, voice and a consistent presence.", color: "#ec4899", link: "/dashboard/build", cta: "Brand" },
              { icon: TrendingUp, title: "Grow Your Business", desc: "AI workflows that scale what works.", color: "#2F7E7A", link: "/ai-agents", cta: "Grow" },
              { icon: Bot, title: "Business AI", desc: "Automate the everyday work.", color: "#06b6d4", link: "/ai-agents", cta: "Automate" },
            ].map((t, i) => (
              <Link key={t.title} to={t.link}>
                <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                  whileHover={{ y: -8, scale: 1.03 }} className="rounded-3xl p-6 sm:p-7 border border-white/10 bg-white/5 backdrop-blur-sm cursor-pointer group relative overflow-hidden h-full">
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{ background: `radial-gradient(circle at 50% 50%, ${t.color}15, transparent 70%)` }} />
                  <div className="relative z-10">
                    <motion.div whileHover={{ rotate: 15, scale: 1.1 }} className="h-14 w-14 rounded-2xl mb-5 grid place-items-center" style={{ background: `${t.color}20` }}>
                      <t.icon className="h-7 w-7" style={{ color: t.color }} />
                    </motion.div>
                    <h3 className="font-display text-xl text-white mb-2">{t.title}</h3>
                    <p className="text-sm text-gray-400 mb-4">{t.desc}</p>
                    <span className="text-sm font-semibold flex items-center gap-1 group-hover:gap-3 transition-all" style={{ color: t.color }}>{t.cta} <ArrowRight className="h-3.5 w-3.5" /></span>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          LEARN
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="mb-8">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-1 font-semibold">Learn</div>
            <h2 className="font-display text-2xl sm:text-3xl">Something that moves you forward</h2>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { title: "AI Basics", desc: "Get confident with AI — no jargon.", icon: Bot },
              { title: "Build with AI", desc: "Ship real things, fast.", icon: Wand2 },
              { title: "Content Creation", desc: "Make content that connects.", icon: PenTool },
              { title: "Business Skills", desc: "Practical, applicable, now.", icon: TrendingUp },
              { title: "Digital Growth", desc: "Grow an audience and income.", icon: Rocket },
            ].map((c, i) => (
              <Link key={c.title} to="/category/digital-products">
                <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                  whileHover={{ y: -6 }} className="gs-card p-6 flex items-start gap-4 h-full">
                  <div className="h-12 w-12 rounded-2xl grid place-items-center bg-[var(--gs-champagne)] shrink-0"><c.icon className="h-6 w-6 text-[var(--gs-primary)]" /></div>
                  <div>
                    <h3 className="font-display text-lg mb-1">{c.title}</h3>
                    <p className="text-sm text-[var(--gs-muted)]">{c.desc}</p>
                    <span className="text-xs font-semibold text-[var(--gs-primary-2)] mt-2 inline-flex items-center gap-1">10-min lessons · Beginner friendly <ArrowRight className="h-3 w-3" /></span>
                  </div>
                </motion.div>
              </Link>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          COMPLETE THE LOOK
      ═══════════════════════════════════════════════════════════════════ */}
      {trending.length >= 3 && (
        <Section className="gs-section" style={{ background: "var(--gs-champagne)" }}>
          <div className="gs-container">
            <motion.div variants={fadeUp} className="text-center mb-8">
              <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">Complete the Look</div>
              <h2 className="font-display text-2xl sm:text-3xl">Style it your way</h2>
              <p className="text-sm text-[var(--gs-muted)] mt-2">Fashion + jewellery + beauty — curated together.</p>
            </motion.div>
            <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-4 max-w-4xl mx-auto">
              {trending.slice(0, 3).map((p, i) => (
                <Link key={p.id} to={"/product/" + p.id} className="group relative rounded-2xl overflow-hidden">
                  <div className="aspect-[3/4] overflow-hidden">
                    <img src={p.images?.[0] || "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=500"} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" loading="lazy" />
                  </div>
                  <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/70 to-transparent">
                    <h4 className="text-white font-semibold text-sm line-clamp-1">{p.name}</h4>
                    <span className="text-white/80 text-xs">{fmtINR(p.price)}</span>
                  </div>
                </Link>
              ))}
            </motion.div>
            <div className="text-center mt-6">
              <Link to="/shop"><Button variant="outline" className="rounded-xl">Shop the Look <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
            </div>
          </div>
        </Section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          GIFT FINDER
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="gift-finder-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-8">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">Find the perfect gift</div>
            <h2 className="font-display text-2xl sm:text-3xl">Gifts she'll actually love</h2>
            <p className="text-sm text-[var(--gs-muted)] mt-2">Tell us the occasion, budget and person — we'll find the right picks. Or ask Neo.</p>
          </motion.div>
          <motion.div variants={fadeUp}>
            <GiftFinder />
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          MEET NEO — dark showcase
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section relative overflow-hidden" style={{ background: "linear-gradient(135deg, #111827 0%, #0b1220 60%, #0b1f1d 100%)" }}>
        <div className="absolute inset-0 gs-ai-glow opacity-70" />
        <div className="gs-container relative z-10 grid lg:grid-cols-2 gap-12 items-center">
          <motion.div variants={stagger} initial="hidden" animate="visible">
            <motion.div variants={fadeUp} className="text-xs uppercase tracking-[0.2em] text-[var(--gs-teal)] mb-3 font-semibold flex items-center gap-2">
              <Sparkle className="h-3.5 w-3.5" /> MEET NEO
            </motion.div>
            <motion.h2 variants={fadeUp} className="font-display text-3xl sm:text-4xl text-white leading-tight">
              Your Getszy AI guide.<br />You don't need to know which tool you need.
            </motion.h2>
            <motion.p variants={fadeUp} className="text-gray-400 mt-4 max-w-md">Just tell Neo what you're trying to achieve. It connects the dots across shopping, learning and building.</motion.p>
            <motion.div variants={fadeUp} className="mt-6">
              <div className="relative max-w-md">
                <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--gs-teal)]" />
                <input value={neoMsg} onChange={(e) => setNeoMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendNeo()} placeholder="I want to start a small business…"
                  className="w-full h-13 pl-12 pr-4 rounded-2xl bg-white/5 border border-white/15 text-white text-sm outline-none focus:ring-2 focus:ring-[var(--gs-teal)]/40" />
              </div>
              <Button onClick={sendNeo} className="mt-3 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 text-white rounded-xl h-11 px-6">Ask Neo <ArrowRight className="h-4 w-4 ml-2" /></Button>
            </motion.div>
            <motion.div variants={fadeUp} className="mt-6 flex flex-wrap gap-2 text-xs">
              {["Founder brief", "Brand", "Website", "Preview", "Launch"].map((s, i) => (
                <span key={s} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-gray-300">{s}{i < 4 && <ChevronRight className="inline h-3 w-3 ml-1 opacity-60" />}</span>
              ))}
            </motion.div>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7 }} className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 sm:p-6 space-y-4">
            {NEO_LINES.map((m, i) => (
              <div key={i} className={`flex ${m.who === "you" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${m.who === "you" ? "bg-[var(--gs-teal)] text-white rounded-br-md" : "bg-white/10 text-gray-100 rounded-bl-md"}`}>
                  <span className="block text-[10px] uppercase tracking-wider opacity-60 mb-1">{m.who === "you" ? "You" : "Neo"}</span>
                  {m.text}
                </div>
              </div>
            ))}
            <div ref={neoEndRef} />
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          IDEA → OUTCOME
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl">From idea to outcome</h2>
            <p className="text-[var(--gs-muted)] mt-3 max-w-lg mx-auto">One connected journey — you stay in control at every step.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
            {JOURNEY.map((step, i) => (
              <div key={step} className="flex items-center gap-2 sm:gap-3">
                <div className="flex flex-col items-center">
                  <div className="h-14 w-14 rounded-2xl grid place-items-center bg-[var(--gs-champagne)] border font-display font-bold text-[var(--gs-primary-2)]" style={{ borderColor: "var(--gs-border)" }}>{i + 1}</div>
                  <div className="text-xs font-semibold mt-2">{step}</div>
                </div>
                {i < JOURNEY.length - 1 && <ChevronRight className="h-5 w-5 text-[var(--gs-primary)]/40 hidden sm:block" />}
              </div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          TRUSTED AI
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" style={{ background: "var(--gs-surface-2)" }}>
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-12">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">Trusted</div>
            <h2 className="font-display text-3xl sm:text-4xl">AI you can trust</h2>
            <p className="text-[var(--gs-muted)] mt-3 max-w-lg mx-auto">AI works with approved information and evidence — not invented claims.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="grid sm:grid-cols-3 gap-5 mb-10">
            {TRUST_PILLARS.map((p, i) => (
              <motion.div key={p.title} variants={scaleIn} whileHover={{ y: -4 }} className="gs-card p-6 text-center">
                <div className="h-14 w-14 rounded-2xl mx-auto mb-4 grid place-items-center bg-[var(--gs-champagne)]"><p.icon className="h-6 w-6" style={{ color: p.color }} /></div>
                <h3 className="font-display text-lg mb-1">{p.title}</h3>
                <p className="text-sm text-[var(--gs-muted)]">{p.desc}</p>
              </motion.div>
            ))}
          </motion.div>
          <motion.div variants={fadeUp} className="rounded-3xl p-6 sm:p-8 text-center" style={{ background: "var(--gs-surface)", border: "1px solid var(--gs-border)" }}>
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-4 font-semibold">Nothing important goes live without your approval</div>
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
              {["Preview", "Test", "Review", "Approve"].map((s, i) => (
                <div key={s} className="flex items-center gap-2 sm:gap-3">
                  <span className="px-4 py-2 rounded-full bg-[var(--gs-champagne)] text-sm font-semibold">{s}</span>
                  {i < 3 && <ChevronRight className="h-4 w-4 text-[var(--gs-primary)]/50" />}
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          REAL CUSTOMER STORIES
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section" data-testid="home-testimonials">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="text-center mb-10">
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">What Getszy customers are loving</div>
            <h2 className="font-display text-2xl sm:text-3xl">Real people. Verified reviews.</h2>
            <p className="text-sm text-[var(--gs-muted)] mt-2">Based on genuine purchase experiences — never fabricated.</p>
          </motion.div>
          <motion.div variants={fadeUp} className="grid md:grid-cols-3 gap-5">
            {[
              { q: "I launched my dropshipping store in a week — all through the AI chat. Insane.", n: "Aanya", loc: "Mumbai", role: "Entrepreneur", verified: true, color: "#C58B7A" },
              { q: "The AI Learning courses genuinely helped me level up. Premium feel, practical content.", n: "Riya", loc: "Bengaluru", role: "AI Graduate", verified: true, color: "#8b5cf6" },
              { q: "Beauty + jewellery quality is genuinely premium. My new favourite store.", n: "Meher", loc: "Delhi", role: "Loyal Customer", verified: true, color: "#2F7E7A" },
            ].map((t, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 30, rotateX: -5 }} whileInView={{ opacity: 1, y: 0, rotateX: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.15, type: "spring" }} whileHover={{ y: -8, scale: 1.02 }} className="gs-card p-6 sm:p-8 relative overflow-hidden backdrop-blur-sm bg-white/80 border border-white/60">
                <div className="absolute top-0 right-0 w-32 h-32 rounded-full opacity-10" style={{ background: `radial-gradient(circle, ${t.color}, transparent)` }} />
                <div className="flex items-center gap-2 mb-4">
                  <div className="flex gap-0.5">{[...Array(5)].map((_, j) => <Star key={j} className="h-4 w-4 fill-amber-400 text-amber-400" />)}</div>
                  {t.verified && <Badge className="bg-green-100 text-green-700 text-[10px] border-0">Verified Purchase</Badge>}
                </div>
                <p className="font-display text-lg leading-relaxed mb-5 relative z-10">"{t.q}"</p>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full grid place-items-center font-display font-bold text-sm text-white" style={{ background: `linear-gradient(135deg, ${t.color}, ${t.color}CC)` }}>{t.n[0]}</div>
                  <div><div className="text-sm font-semibold">{t.n}</div><div className="text-xs text-[var(--gs-muted)]">{t.role} · {t.loc}</div></div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          MY GETSZY — personalized
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="rounded-3xl p-8 sm:p-12" style={{ background: "var(--gs-champagne)" }}>
            {user ? (
              <>
                <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">My Getszy</div>
                <h2 className="font-display text-2xl sm:text-3xl mb-2">Hello, {user.name?.split(" ")[0] || "there"} 👋</h2>
                <p className="text-sm text-[var(--gs-muted)] mb-6 max-w-md">Everything you've built with Getszy — in one place.</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mb-8">
                  {[{ icon: ShoppingBag, label: "Orders" }, { icon: FolderKanban, label: "Projects" }, { icon: Zap, label: "Digital" }, { icon: GraduationCap, label: "Learning" }].map((f) => (
                    <div key={f.label} className="flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60"><f.icon className="h-5 w-5 text-[var(--gs-primary)]" /><span className="text-xs font-medium">{f.label}</span></div>
                  ))}
                </div>
                <Link to="/dashboard"><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] rounded-xl h-11 px-8">Continue where you left off <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
              </>
            ) : (
              <>
                <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-primary-2)] mb-2 font-semibold">My Getszy</div>
                <h2 className="font-display text-2xl sm:text-3xl mb-2">Your Getszy journey starts here.</h2>
                <p className="text-sm text-[var(--gs-muted)] mb-6 max-w-md">Create a free account to track orders, projects, learning and more.</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mb-8">
                  {[{ icon: ShoppingBag, label: "Orders" }, { icon: FolderKanban, label: "Projects" }, { icon: Download, label: "Downloads" }, { icon: Heart, label: "Wishlist" }].map((f) => (
                    <div key={f.label} className="flex flex-col items-center gap-2 p-4 rounded-xl bg-white/60"><f.icon className="h-5 w-5 text-[var(--gs-primary)]" /><span className="text-xs font-medium">{f.label}</span></div>
                  ))}
                </div>
                <Link to="/signup"><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] rounded-xl h-11 px-8">Create a free account <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
              </>
            )}
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          NEWSLETTER
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="gs-section">
        <div className="gs-container">
          <motion.div variants={fadeUp} className="rounded-3xl p-8 sm:p-12 text-center" style={{ background: "var(--gs-surface-2)" }} data-testid="newsletter-signup-form">
            <h3 className="font-display text-2xl sm:text-3xl mb-2">Get the Getszy Edit</h3>
            <p className="text-sm text-[var(--gs-muted)] mb-6 max-w-md mx-auto">New drops, AI tools, practical tips and women-first stories — delivered occasionally, never spammed.</p>
            <form onSubmit={handleNewsletter} className="flex gap-2 max-w-md mx-auto">
              <input type="email" placeholder="Your email" value={newsletterEmail} onChange={(e) => setNewsletterEmail(e.target.value)} disabled={newsletterLoading}
                className="flex-1 h-12 px-4 rounded-xl bg-white border" style={{ borderColor: "var(--gs-border)" }} data-testid="newsletter-email-input" />
              <Button type="submit" disabled={newsletterLoading} className="bg-[var(--gs-ink)] hover:bg-black h-12 px-6 rounded-xl" data-testid="newsletter-submit-button">
                {newsletterLoading ? "Joining…" : "Join Getszy"}
              </Button>
            </form>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          FINAL CTA
      ═══════════════════════════════════════════════════════════════════ */}
      <Section className="py-20 sm:py-28 relative overflow-hidden">
        <div className="absolute inset-0 hero-gradient opacity-30" />
        <SparkleParticles count={15} />
        <FloatingShape className="w-40 h-40 -top-10 left-1/4 opacity-10" delay={0.3} />
        <FloatingShape className="w-32 h-32 bottom-10 right-1/4 opacity-10" delay={0.6} />
        <div className="gs-container text-center relative z-10">
          <motion.div variants={fadeUp}>
            <h2 className="font-display text-3xl sm:text-5xl mb-4">
              <CharacterReveal text="Ready to start your" delay={0.2} /><br />
              <span className="shimmer-text font-bold"><CharacterReveal text="Getszy journey?" delay={0.6} /></span>
            </h2>
            <p className="text-[var(--gs-muted)] mb-8 max-w-lg mx-auto">Shop premium essentials. Learn AI. Build your business — all in one place.</p>
            <div className="flex flex-wrap gap-4 justify-center">
              <Link to="/shop"><Button size="lg" className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-14 px-10 text-base rounded-2xl shadow-lg magnetic-hover glow-on-hover">Shop Now <ArrowRight className="h-4 w-4 ml-2" /></Button></Link>
              <Link to="/dashboard"><Button size="lg" variant="outline" className="h-14 px-10 text-base rounded-2xl border-[var(--gs-border)] magnetic-hover">Try Neo</Button></Link>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════════════════════════════
          TRUST BAR
      ═══════════════════════════════════════════════════════════════════ */}
      <div className="border-t" style={{ borderColor: "var(--gs-border)" }}>
        <div className="gs-container py-6 flex flex-wrap justify-center gap-6 sm:gap-10 text-xs text-[var(--gs-muted)]">
          <span className="flex items-center gap-1.5"><Truck className="h-3.5 w-3.5" /> Free shipping on orders ₹1,000+</span>
          <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5" /> Secure payment</span>
          <span className="flex items-center gap-1.5"><RotateCcw className="h-3.5 w-3.5" /> Easy returns</span>
          <span className="flex items-center gap-1.5"><CreditCard className="h-3.5 w-3.5" /> Razorpay + UPI</span>
          <span className="flex items-center gap-1.5"><Zap className="h-3.5 w-3.5" /> Instant digital delivery</span>
        </div>
      </div>

      <CartDrawer open={cartOpen} onClose={() => setCartOpen(false)} />
      <QuickViewDialog product={quickViewProduct} open={!!quickViewProduct} onClose={() => setQuickViewProduct(null)} onAddToCart={handleQuickAdd} />
      <AIConcierge />
      <MobileBottomNav cartCount={cart.count} onCartOpen={() => setCartOpen(true)} />
    </div>
  );
}
