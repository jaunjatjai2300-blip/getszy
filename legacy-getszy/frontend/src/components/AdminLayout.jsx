import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, FolderOpen, Layers, Bot, ShoppingBag, Users, BarChart3,
  Zap, Rocket, Monitor, Shield, Settings, LogOut, Store, Menu, ChevronDown,
  ChevronRight, Sparkles, Wand2, Film, PenTool, Briefcase, Package, ShoppingCart,
  Truck, TrendingUp, GraduationCap, Globe, Smartphone, Code2, Workflow,
  CalendarClock, Webhook, Activity, Server, Lock, Key, AlertTriangle,
  Bell, Search, Share2, Database, Image, Mic, MessageCircle, Cpu, Building2
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import CopilotSidebar from "@/components/CopilotSidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

const NAV = [
  {
    label: "🏠 Dashboard",
    to: "/admin",
    icon: LayoutDashboard,
    end: true,
    single: true,
  },
  {
    label: "📁 Projects",
    to: "/admin/projects",
    icon: FolderOpen,
    single: true,
  },
  {
    label: "🛠 Builders",
    icon: Layers,
    items: [
      { to: "/admin/build",        label: "App Builder",      icon: Wand2 },
      { to: "/admin/build-web",    label: "Website Builder",  icon: Globe },
      { to: "/admin/build-mobile", label: "Mobile Builder",   icon: Smartphone },
      { to: "/admin/build-api",    label: "API Builder",      icon: Code2 },
      { to: "/admin/build-db",     label: "Database Builder", icon: Database },
    ],
  },
  {
    label: "🤖 AI Platform",
    icon: Bot,
    items: [
      { to: "/admin/chat",      label: "Neo AI",           icon: Sparkles },
      { to: "/admin/video",     label: "Video Studio",     icon: Film },
      { to: "/admin/creator",   label: "Creator OS",       icon: PenTool },
      { to: "/admin/avatar",    label: "Avatar Studio",    icon: Image },
      { to: "/admin/workforce", label: "AI Workforce",     icon: Briefcase },
      { to: "/admin/ai-models", label: "AI Models",        icon: Cpu },
      { to: "/admin/voice",     label: "Voice",            icon: Mic },
    ],
  },
  {
    label: "🛒 Commerce",
    icon: ShoppingBag,
    items: [
      { to: "/admin/products",  label: "Products",     icon: Package },
      { to: "/admin/orders",    label: "Orders",       icon: ShoppingCart },
      { to: "/admin/customers", label: "Customers",    icon: Users },
      { to: "/admin/suppliers", label: "Suppliers",    icon: Truck },
      { to: "/admin/sourcing",  label: "Sourcing",     icon: TrendingUp },
      { to: "/admin/courses",   label: "Courses",      icon: GraduationCap },
      { to: "/admin/publishing",label: "Publishing",   icon: Share2 },
    ],
  },
  {
    label: "👥 Users",
    icon: Users,
    items: [
      { to: "/admin/users",          label: "All Users",    icon: Users },
      { to: "/admin/users/credits",  label: "Credits",      icon: Zap },
      { to: "/admin/users/subs",     label: "Subscriptions",icon: Building2 },
      { to: "/admin/users/sessions", label: "Sessions",     icon: Monitor },
    ],
  },
  {
    label: "📈 Analytics",
    icon: BarChart3,
    items: [
      { to: "/admin/analytics",         label: "Overview",      icon: BarChart3 },
      { to: "/admin/analytics/revenue", label: "Revenue",       icon: TrendingUp },
      { to: "/admin/analytics/ai",      label: "AI Usage",      icon: Bot },
      { to: "/admin/analytics/content", label: "Content",       icon: Film },
    ],
  },
  {
    label: "⚡ Automation",
    icon: Zap,
    items: [
      { to: "/admin/skills",    label: "Skills",      icon: Wand2 },
      { to: "/admin/stacks",    label: "Stacks",      icon: Layers },
      { to: "/admin/workflows", label: "Workflows",   icon: Workflow },
      { to: "/admin/scheduler", label: "Scheduler",   icon: CalendarClock },
      { to: "/admin/webhooks",  label: "Webhooks",    icon: Webhook },
    ],
  },
  {
    label: "🚀 Deploy",
    icon: Rocket,
    items: [
      { to: "/admin/deploy",    label: "Deployments", icon: Rocket },
    ],
  },
  {
    label: "🖥 Operations",
    icon: Monitor,
    items: [
      { to: "/admin/ai-ops",    label: "AI Ops",      icon: Activity },
      { to: "/admin/servers",   label: "Servers",     icon: Server },
      { to: "/admin/ai-chat",   label: "Legacy Chat", icon: MessageCircle },
    ],
  },
  {
    label: "🔒 Security",
    icon: Shield,
    items: [
      { to: "/admin/security",        label: "Overview",   icon: Shield },
      { to: "/admin/security/logs",   label: "Audit Logs", icon: Lock },
      { to: "/admin/security/keys",   label: "API Keys",   icon: Key },
      { to: "/admin/security/alerts", label: "Alerts",     icon: AlertTriangle },
    ],
  },
  {
    label: "⚙ Settings",
    icon: Settings,
    items: [
      { to: "/admin/settings",           label: "Workspace",  icon: Building2 },
      { to: "/admin/settings/branding",  label: "Branding",   icon: Wand2 },
      { to: "/admin/settings/billing",   label: "Billing",    icon: ShoppingBag },
      { to: "/admin/settings/integrations", label: "Integrations", icon: Webhook },
    ],
  },
];

export default function AdminLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState({ "🤖 AI Platform": true, "🛒 Commerce": true });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) navigate("/login");
  }, [user, loading, navigate]);

  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;
  if (user.role !== "admin") return null;

  const toggle = (k) => setOpen(o => ({ ...o, [k]: !o[k] }));

  const NavContent = ({ onNavigate }) => (
    <>
      <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: "var(--gs-border)" }}>
        <div>
          <div className="font-display text-xl">getszy</div>
          <div className="text-[10px] text-[var(--gs-muted)]">Admin Console</div>
        </div>
        <div className="h-7 w-7 rounded-full bg-[var(--gs-teal)] grid place-items-center text-white text-[10px] font-bold">
          {user?.name?.[0]?.toUpperCase() || "A"}
        </div>
      </div>

      <div className="px-3 py-2 border-b" style={{ borderColor: "var(--gs-border)" }}>
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-[var(--gs-surface-2)] text-xs text-[var(--gs-muted)]">
          <Search className="h-3 w-3"/>
          <span>Search… (⌘K)</span>
        </div>
      </div>

      <nav className="flex-1 p-2 overflow-y-auto space-y-0.5">
        {NAV.map((n) => {
          if (n.single) {
            return (
              <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors
                  ${isActive ? "bg-[var(--gs-teal)] text-white font-semibold" : "hover:bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`}>
                <n.icon className="h-4 w-4 shrink-0"/>
                {n.label}
              </NavLink>
            );
          }
          const isOpen = open[n.label] !== false;
          return (
            <div key={n.label}>
              <button onClick={() => toggle(n.label)}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-[10px] uppercase tracking-wider font-semibold text-[var(--gs-muted)] hover:text-[var(--gs-ink)] mt-1">
                {isOpen ? <ChevronDown className="h-3 w-3 shrink-0"/> : <ChevronRight className="h-3 w-3 shrink-0"/>}
                <span>{n.label}</span>
              </button>
              {isOpen && (
                <div className="ml-2 pl-2 border-l space-y-0.5 mb-1" style={{ borderColor: "var(--gs-border)" }}>
                  {n.items.map((item) => (
                    <NavLink key={item.to} to={item.to} onClick={onNavigate}
                      className={({ isActive }) =>
                        `flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors
                        ${isActive ? "bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] font-semibold" : "hover:bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`}>
                      <item.icon className="h-3.5 w-3.5 shrink-0"/>
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="p-2 border-t space-y-0.5" style={{ borderColor: "var(--gs-border)" }}>
        <button onClick={() => { onNavigate?.(); navigate("/"); }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-[var(--gs-muted)] hover:bg-[var(--gs-surface-2)]">
          <Store className="h-3.5 w-3.5"/>View Storefront
        </button>
        <button onClick={() => { onNavigate?.(); logout(); navigate("/"); }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-rose-500 hover:bg-rose-50">
          <LogOut className="h-3.5 w-3.5"/>Logout
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen grid md:grid-cols-[220px_1fr]" style={{ background: "#F7F5F2" }}>
      <aside className="hidden md:flex flex-col border-r h-screen sticky top-0 overflow-hidden" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <NavContent/>
      </aside>

      <div className="md:hidden flex items-center justify-between p-3 border-b sticky top-0 z-30" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="flex items-center gap-2">
          <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8"><Menu className="h-4 w-4"/></Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0 flex flex-col">
              <NavContent onNavigate={() => setMobileNavOpen(false)}/>
            </SheetContent>
          </Sheet>
          <div className="font-display text-lg">getszy admin</div>
        </div>
        <div className="flex items-center gap-2">
          <NavLink to="/admin/notifications" className="relative">
            <Bell className="h-4 w-4 text-[var(--gs-muted)]"/>
          </NavLink>
          <NavLink to="/admin/chat" className="text-xs px-3 py-1.5 rounded-lg bg-[var(--gs-teal)] text-white flex items-center gap-1">
            <Sparkles className="h-3 w-3"/>Neo
          </NavLink>
        </div>
      </div>

      <main id="main-content" className="p-4 md:p-6 overflow-x-hidden min-h-screen" tabIndex={-1}>
        <Outlet/>
      </main>
      <CopilotSidebar/>
    </div>
  );
}
