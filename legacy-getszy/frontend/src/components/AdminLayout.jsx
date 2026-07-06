import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { LayoutDashboard, Package, ShoppingCart, Truck, Users, Sparkles, LogOut, Store, GraduationCap, Activity, TrendingUp, Rocket, Wand2, Layers, MessageCircle, PenTool, Film, Share2, Briefcase, ChevronDown, ChevronRight, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";
import CopilotSidebar from "@/components/CopilotSidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

// PRIMARY nav — Admin is management-first; Neo is a utility not the front door.
const PRIMARY = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard, end: true, primary: true },
  { to: "/admin/chat", label: "Ask Neo", icon: Sparkles },
];

// GROUPED nav — everything else lives behind conversational access from Neo,
// but power-users can still open modules directly.
const GROUPS = [
  {
    label: "Store", icon: Store, items: [
      { to: "/admin/products", label: "Products", icon: Package },
      { to: "/admin/orders", label: "Orders", icon: ShoppingCart },
      { to: "/admin/suppliers", label: "Suppliers", icon: Truck },
      { to: "/admin/customers", label: "Customers", icon: Users },
      { to: "/admin/sourcing", label: "Sourcing", icon: TrendingUp },
    ],
  },
  {
    label: "AI Studio", icon: Wand2, items: [
      { to: "/admin/build", label: "Build Studio", icon: Wand2 },
      { to: "/admin/creator", label: "Creator OS", icon: PenTool },
      { to: "/admin/video", label: "Video Studio", icon: Film },
      { to: "/admin/workforce", label: "AI Workforce", icon: Briefcase },
      { to: "/admin/publishing", label: "Publishing", icon: Share2 },
    ],
  },
  {
    label: "Learning", icon: GraduationCap, items: [
      { to: "/admin/courses", label: "Courses", icon: GraduationCap },
    ],
  },
  {
    label: "Automation", icon: Layers, items: [
      { to: "/admin/skills", label: "Skills", icon: Wand2 },
      { to: "/admin/stacks", label: "Stacks", icon: Layers },
    ],
  },
  {
    label: "Operations", icon: Activity, items: [
      { to: "/admin/deploy", label: "Deploy", icon: Rocket },
      { to: "/admin/ai-ops", label: "AI Ops", icon: Activity },
      { to: "/admin/ai-chat", label: "Legacy Chat", icon: MessageCircle },
    ],
  },
];

export default function AdminLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState({});
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) navigate("/login");
  }, [user, loading, navigate]);

  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;
  if (user.role !== "admin") return null;

  const toggle = (k) => setOpen(o => ({ ...o, [k]: !o[k] }));

  const NavContent = ({ onNavigate }) => (
    <>
      <div className="px-5 py-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
        <div className="font-display text-2xl">getszy</div>
        <div className="text-xs text-[var(--gs-muted)] mt-0.5">Admin \u00b7 Neo Console</div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {PRIMARY.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate}
            data-testid={`admin-nav-${n.label.toLowerCase().replace(" ", "-")}`}
            className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive ? "bg-[var(--gs-teal)] text-white font-semibold" : "hover:bg-[var(--gs-surface-2)]"} ${n.primary ? "shadow-sm" : ""}`}>
            <n.icon className="h-4 w-4"/>{n.label}
          </NavLink>
        ))}
        <div className="h-2"/>
        {GROUPS.map((g) => {
          const isOpen = open[g.label] !== false; // default expanded
          return (
            <div key={g.label}>
              <button onClick={() => toggle(g.label)} className="w-full flex items-center gap-2 px-3 py-2 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid={`nav-group-${g.label.toLowerCase()}`}>
                {isOpen ? <ChevronDown className="h-3 w-3"/> : <ChevronRight className="h-3 w-3"/>}
                <g.icon className="h-3.5 w-3.5"/>
                <span className="flex-1 text-left">{g.label}</span>
              </button>
              {isOpen && (
                <div className="ml-3 space-y-0.5 border-l" style={{ borderColor: "var(--gs-border)" }}>
                  {g.items.map((n) => (
                    <NavLink key={n.to} to={n.to} onClick={onNavigate} data-testid={`admin-nav-${n.label.toLowerCase().replace(/\s+/g, "-")}`}
                      className={({ isActive }) => `flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${isActive ? "bg-[var(--gs-surface-2)] text-[var(--gs-teal)] font-semibold" : "hover:bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`}>
                      <n.icon className="h-3.5 w-3.5"/>{n.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <div className="p-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
        <button onClick={() => { onNavigate?.(); navigate("/"); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="admin-view-store-button"><Store className="h-4 w-4"/>View Storefront</button>
        <button onClick={() => { onNavigate?.(); logout(); navigate("/"); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="admin-logout-button"><LogOut className="h-4 w-4"/>Logout</button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen grid md:grid-cols-[240px_1fr]" style={{ background: "#F7F5F2" }}>
      <aside className="hidden md:flex flex-col border-r" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <NavContent/>
      </aside>
      <div className="md:hidden flex items-center justify-between p-4 border-b" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="flex items-center gap-2">
          <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" data-testid="admin-mobile-menu-button"><Menu className="h-5 w-5"/></Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-0 flex flex-col">
              <NavContent onNavigate={() => setMobileNavOpen(false)}/>
            </SheetContent>
          </Sheet>
          <div className="font-display text-xl">getszy admin</div>
        </div>
        <NavLink to="/admin/chat" className="text-xs px-3 py-1.5 rounded-lg bg-[var(--gs-teal)] text-white flex items-center gap-1"><Sparkles className="h-3 w-3"/>Neo</NavLink>
      </div>
      <main id="main-content" className="p-4 md:p-6 overflow-x-hidden" tabIndex={-1}>
        <Outlet/>
      </main>
      <CopilotSidebar/>
    </div>
  );
}
