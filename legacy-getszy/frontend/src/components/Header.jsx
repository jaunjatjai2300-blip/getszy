/* eslint-disable react/no-unescaped-entities */
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import {
  ShoppingBag, Search, User, Menu, Sparkle, LogOut, LayoutDashboard, X, Gift,
  ChevronDown, ArrowRight, Bot, GraduationCap, Wand2, TrendingUp, Zap,
  Store, PenTool, Megaphone, BookOpen, Rocket, Heart, Package, Download,
  FolderKanban, LifeBuoy, Palette,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { api } from "@/lib/api";
import { PlanBadge } from "@/components/PlanBadge";

const SHOP_FEATURE = [
  { name: "The Getszy Edit", desc: "Curated drops & everyday essentials", to: "/shop", icon: Sparkle },
  { name: "Shop by Mood", desc: "Find the right vibe, fast", to: "/shop", icon: Heart },
  { name: "Complete the Look", desc: "Styled sets, ready to wear", to: "/shop", icon: Palette },
];

const BUILD_GROW = {
  LEARN: [
    { name: "AI Learning", desc: "Practical AI skills", to: "/category/digital-products", icon: GraduationCap },
    { name: "Courses", desc: "Structured programs", to: "/category/digital-products", icon: BookOpen },
    { name: "eBooks", desc: "Read & apply", to: "/category/digital-products", icon: BookOpen },
    { name: "Practical Skills", desc: "Build real ability", to: "/category/digital-products", icon: Zap },
  ],
  BUILD: [
    { name: "Launch Website", desc: "Your storefront, live", to: "/dashboard/build", icon: Rocket },
    { name: "Launch Store", desc: "Sell your products", to: "/dashboard/build", icon: Store },
    { name: "Digital Presence", desc: "Brand & content", to: "/dashboard/build", icon: PenTool },
    { name: "Creator Tools", desc: "Make & publish", to: "/dashboard/creator", icon: Wand2 },
  ],
  GROW: [
    { name: "Content", desc: "Create at scale", to: "/dashboard/agents", icon: PenTool },
    { name: "Campaigns", desc: "Reach the right people", to: "/dashboard/agents", icon: Megaphone },
    { name: "Business Growth", desc: "AI workflows", to: "/dashboard/agents", icon: TrendingUp },
    { name: "Business AI", desc: "Automate the work", to: "/ai-agents", icon: Bot },
  ],
};

const MY_GETSZY = [
  { name: "Orders", to: "/account", icon: Package },
  { name: "Projects", to: "/dashboard", icon: FolderKanban },
  { name: "Digital Purchases", to: "/account", icon: Zap },
  { name: "Learning", to: "/account", icon: GraduationCap },
  { name: "Downloads", to: "/account", icon: Download },
  { name: "Wishlist", to: "/account", icon: Heart },
  { name: "Support", to: "/support", icon: LifeBuoy },
];

function MegaPanel({ children }) {
  return (
    <div className="absolute left-1/2 -translate-x-1/2 top-full pt-3 w-[min(92vw,720px)]">
      <div className="rounded-3xl bg-white shadow-[0_24px_70px_rgba(27,26,24,0.18)] border p-6 grid gap-6"
        style={{ borderColor: "var(--gs-border)" }}>
        {children}
      </div>
    </div>
  );
}

function MegaLink({ to, icon: Icon, name, desc, accent = "var(--gs-primary)" }) {
  return (
    <Link to={to} className="group flex items-start gap-3 rounded-2xl p-3 transition-colors hover:bg-[var(--gs-surface-2)]">
      <div className="h-10 w-10 shrink-0 rounded-xl grid place-items-center transition-transform group-hover:scale-105" style={{ background: `${accent}14` }}>
        <Icon className="h-5 w-5" style={{ color: accent }} />
      </div>
      <div className="min-w-0">
        <div className="text-sm font-semibold leading-tight">{name}</div>
        {desc && <div className="text-xs text-[var(--gs-muted)] mt-0.5 leading-snug">{desc}</div>}
      </div>
    </Link>
  );
}

function NavItem({ label, children, to }) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef(null);
  const enter = () => { if (closeTimer.current) clearTimeout(closeTimer.current); setOpen(true); };
  const leave = () => { closeTimer.current = setTimeout(() => setOpen(false), 120); };
  return (
    <div className="relative h-full flex items-center" onMouseEnter={enter} onMouseLeave={leave}>
      {to ? (
        <Link to={to} className="flex items-center gap-1 text-sm font-medium text-[var(--gs-ink)] hover:text-[var(--gs-primary-2)] transition-colors px-1">
          {label} <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </Link>
      ) : (
        <button className="flex items-center gap-1 text-sm font-medium text-[var(--gs-ink)] hover:text-[var(--gs-primary-2)] transition-colors px-1">
          {label} <ChevronDown className="h-3.5 w-3.5 opacity-60" />
        </button>
      )}
      {children && (
        <div className="absolute left-0 top-full h-3" style={{ width: 1 }} />
      )}
      {open && children && (
        <div className="absolute left-0 top-full pt-3 z-50" onMouseEnter={enter} onMouseLeave={leave}>
          {children}
        </div>
      )}
    </div>
  );
}

export function Header() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [cats, setCats] = useState([]);
  const [credits, setCredits] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  useEffect(() => {
    api.get("/categories").then(({ data }) => setCats(Array.isArray(data) ? data : [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (user) api.get("/credits/me").then(({ data }) => setCredits(data?.credits ?? null)).catch(() => {});
    else setCredits(null);
  }, [user]);

  const submitSearch = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/shop?search=${encodeURIComponent(q.trim())}`);
  };

  return (
    <header className="sticky top-0 z-40 border-b" style={{ background: "rgba(251,247,242,0.85)", backdropFilter: "blur(12px)", borderColor: "var(--gs-border)" }}>
      <div className="gs-container flex items-center gap-3 h-16">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden" data-testid="header-mobile-menu-button"><Menu className="h-5 w-5" /></Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80 p-0">
            <div className="p-6">
              <div className="font-display text-2xl mb-6">getszy</div>
              <nav className="flex flex-col gap-1 text-sm">
                <Link to="/shop" className="py-2.5 hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>Shop</Link>
                {cats.map((c) => (
                  <Link key={c.slug} to={`/category/${c.slug}`} className="py-2.5 pl-3 text-[var(--gs-muted)] hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>{c.name}</Link>
                ))}
                <Link to="/dashboard/build" className="py-2.5 hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>Build &amp; Grow</Link>
                <Link to="/category/digital-products" className="py-2.5 hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>Learn</Link>
                <Link to="/account" className="py-2.5 hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>My Getszy</Link>
                <Link to="/pricing" className="py-2.5 hover:text-[var(--gs-primary-2)]" onClick={() => setMobileOpen(false)}>Pricing</Link>
                <Link to="/ai-agents" className="py-2.5 text-[var(--gs-teal)] font-medium" onClick={() => setMobileOpen(false)}>AI Agents</Link>
              </nav>
            </div>
          </SheetContent>
        </Sheet>

        <Link to="/" className="font-display text-2xl tracking-tight" data-testid="header-logo-link">getszy</Link>

        <nav className="hidden lg:flex items-center gap-1 h-full ml-4">
          <NavItem label="SHOP" to="/shop">
            <MegaPanel>
              <div className="grid sm:grid-cols-3 gap-2">
                {cats.slice(0, 6).map((c) => (
                  <MegaLink key={c.slug} to={`/category/${c.slug}`} name={c.name} desc="Explore now" icon={ShoppingBag} />
                ))}
              </div>
              <div className="border-t pt-4 grid sm:grid-cols-3 gap-2" style={{ borderColor: "var(--gs-border)" }}>
                {SHOP_FEATURE.map((f) => (
                  <MegaLink key={f.name} to={f.to} name={f.name} desc={f.desc} icon={f.icon} accent="var(--gs-teal)" />
                ))}
              </div>
            </MegaPanel>
          </NavItem>

          <NavItem label="BUILD & GROW" to="/dashboard/build">
            <MegaPanel>
              <div className="grid sm:grid-cols-3 gap-5">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[var(--gs-primary-2)] mb-2">Learn</div>
                  <div className="space-y-0.5">{BUILD_GROW.LEARN.map((i) => <MegaLink key={i.name} {...i} accent="#8b5cf6" />)}</div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[var(--gs-primary-2)] mb-2">Build</div>
                  <div className="space-y-0.5">{BUILD_GROW.BUILD.map((i) => <MegaLink key={i.name} {...i} accent="var(--gs-teal)" />)}</div>
                </div>
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[var(--gs-primary-2)] mb-2">Grow</div>
                  <div className="space-y-0.5">{BUILD_GROW.GROW.map((i) => <MegaLink key={i.name} {...i} accent="#f59e0b" />)}</div>
                </div>
              </div>
              <div className="border-t pt-4 flex items-center justify-between" style={{ borderColor: "var(--gs-border)" }}>
                <span className="text-xs text-[var(--gs-muted)]">Start something of your own.</span>
                <Link to="/dashboard/build" className="text-sm font-semibold text-[var(--gs-primary-2)] flex items-center gap-1 hover:gap-2 transition-all">Talk to Neo <ArrowRight className="h-3.5 w-3.5" /></Link>
              </div>
            </MegaPanel>
          </NavItem>

          <NavItem label="MY GETSZY" to="/account">
            <MegaPanel>
              <div className="grid sm:grid-cols-2 gap-1 w-[360px]">
                {MY_GETSZY.map((i) => <MegaLink key={i.name} {...i} />)}
              </div>
            </MegaPanel>
          </NavItem>

          <Link to="/pricing" className="text-sm font-medium text-[var(--gs-ink)] hover:text-[var(--gs-primary-2)] px-1" data-testid="header-pricing-link">Pricing</Link>
          <Link to="/ai-agents" className="text-sm font-medium text-[var(--gs-teal)] hover:opacity-80 px-1" data-testid="header-ai-agents-link">AI Agents</Link>
        </nav>

        <form onSubmit={submitSearch} className="flex-1 hidden lg:flex justify-center max-w-md mx-4">
          <div className="relative w-full">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gs-muted)]" />
            <Input data-testid="header-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search dresses, jewellery, gifts, AI tools…" className="pl-9 h-10 rounded-full bg-[var(--gs-surface)]" />
          </div>
        </form>

        <div className="ml-auto flex items-center gap-1.5">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileSearchOpen((v) => !v)} data-testid="header-mobile-search-button">
            {mobileSearchOpen ? <X className="h-5 w-5" /> : <Search className="h-5 w-5" />}
          </Button>
          {user ? (
            <div className="flex items-center gap-1.5">
              {credits !== null && (
                <Link to="/pricing" className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]" data-testid="header-credit-balance">
                  <Sparkle className="h-3 w-3" />{credits} credits
                </Link>
              )}
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" data-testid="header-user-menu-button"><User className="h-5 w-5" /></Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-72">
                  <div className="p-6">
                    <div className="font-display text-xl mb-1">{user.name}</div>
                    <div className="text-xs text-[var(--gs-muted)] mb-4">{user.email}</div>
                    <div className="flex items-center gap-2 mb-4">
                      <PlanBadge plan={user.subscription?.plan || "free"} status={user.subscription?.status} />
                      {credits !== null && <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]"><Sparkle className="h-3 w-3" />{credits}</span>}
                    </div>
                    <div className="space-y-1">
                      <button onClick={() => navigate("/account")} className="w-full text-left py-2.5 px-2 rounded-lg hover:bg-[var(--gs-surface-2)] text-sm flex items-center gap-2"><User className="h-4 w-4" />My Account</button>
                      <button onClick={() => navigate("/referrals")} className="w-full text-left py-2.5 px-2 rounded-lg hover:bg-[var(--gs-surface-2)] text-sm flex items-center gap-2"><Gift className="h-4 w-4" />Refer &amp; Earn</button>
                      <button onClick={() => navigate("/dashboard")} className="w-full text-left py-2.5 px-2 rounded-lg hover:bg-[var(--gs-surface-2)] text-sm flex items-center gap-2"><LayoutDashboard className="h-4 w-4" />Dashboard</button>
                      {user.role === "admin" && <button onClick={() => navigate("/admin")} className="w-full text-left py-2.5 px-2 rounded-lg hover:bg-[var(--gs-surface-2)] text-sm flex items-center gap-2"><LayoutDashboard className="h-4 w-4" />Admin</button>}
                      <button onClick={() => { logout(); navigate("/"); }} className="w-full text-left py-2.5 px-2 rounded-lg hover:bg-[var(--gs-surface-2)] text-sm flex items-center gap-2 text-red-600"><LogOut className="h-4 w-4" />Logout</button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          ) : (
            <Button variant="ghost" onClick={() => navigate("/login")} data-testid="header-login-button" className="text-sm">Login</Button>
          )}
          <Link to="/cart" className="relative" data-testid="header-cart-link">
            <Button variant="ghost" size="icon"><ShoppingBag className="h-5 w-5" /></Button>
            {cart.count > 0 && (
              <span className="absolute -top-0.5 -right-0.5 bg-[var(--gs-primary)] text-white text-[10px] rounded-full h-5 w-5 flex items-center justify-center font-semibold">{cart.count}</span>
            )}
          </Link>
        </div>
      </div>
      {mobileSearchOpen && (
        <div className="lg:hidden px-4 pb-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
          <form onSubmit={(e) => { submitSearch(e); setMobileSearchOpen(false); }} className="pt-3">
            <div className="relative w-full">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gs-muted)]" />
              <Input autoFocus data-testid="header-mobile-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search dresses, jewellery, gifts…" className="pl-9 h-10 rounded-full bg-[var(--gs-surface)]" />
            </div>
          </form>
        </div>
      )}
    </header>
  );
}
