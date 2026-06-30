import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { LayoutDashboard, Package, ShoppingCart, Truck, Users, Sparkles, LogOut, Store, GraduationCap, Activity, TrendingUp, Rocket, Wand2, Layers, MessageCircle, PenTool, Film, Share2, Briefcase } from "lucide-react";
import { useAuth } from "@/lib/auth";
import CopilotSidebar from "@/components/CopilotSidebar";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/products", label: "Products", icon: Package },
  { to: "/admin/orders", label: "Orders", icon: ShoppingCart },
  { to: "/admin/suppliers", label: "Suppliers", icon: Truck },
  { to: "/admin/customers", label: "Customers", icon: Users },
  { to: "/admin/courses", label: "Courses", icon: GraduationCap },
  { to: "/admin/sourcing", label: "Sourcing", icon: TrendingUp, accent: true },
  { to: "/admin/creator", label: "Creator OS", icon: PenTool, accent: true },
  { to: "/admin/video", label: "Video Studio", icon: Film, accent: true },
  { to: "/admin/publishing", label: "Publishing", icon: Share2, accent: true },
  { to: "/admin/workforce", label: "AI Workforce", icon: Briefcase, accent: true },
  { to: "/admin/skills", label: "Skills", icon: Wand2, accent: true },
  { to: "/admin/stacks", label: "Stacks", icon: Layers, accent: true },
  { to: "/admin/deploy", label: "Deploy", icon: Rocket, accent: true },
  { to: "/admin/ai-ops", label: "AI Ops", icon: Activity, accent: true },
  { to: "/admin/chat", label: "AI Chat", icon: MessageCircle, accent: true },
];

export default function AdminLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) navigate("/login");
  }, [user, loading, navigate]);

  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;
  if (user.role !== "admin") return null;

  return (
    <div className="min-h-screen grid md:grid-cols-[260px_1fr]" style={{ background: "#F7F5F2" }}>
      <aside className="hidden md:flex flex-col border-r" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="px-6 py-5 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <div className="font-display text-2xl">getszy</div>
          <div className="text-xs text-[var(--gs-muted)] mt-0.5">Admin Console</div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={`admin-nav-${n.label.toLowerCase().replace(" ", "-")}`} className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive ? "bg-[var(--gs-surface-2)] font-semibold border-l-2 border-[var(--gs-primary)]" : "hover:bg-[var(--gs-surface-2)]"} ${n.accent ? "text-[var(--gs-teal)]" : ""}`}>
              <n.icon className="h-4 w-4"/>{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
          <button onClick={() => navigate("/")} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="admin-view-store-button"><Store className="h-4 w-4"/>View Storefront</button>
          <button onClick={() => { logout(); navigate("/"); }} className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="admin-logout-button"><LogOut className="h-4 w-4"/>Logout</button>
        </div>
      </aside>
      <div className="md:hidden flex items-center justify-between p-4 border-b" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="font-display text-xl">getszy admin</div>
      </div>
      <main className="p-4 md:p-8 overflow-x-hidden">
        <Outlet/>
      </main>
      <nav className="md:hidden fixed bottom-0 left-0 right-0 grid grid-cols-12 border-t bg-white" style={{ borderColor: "var(--gs-border)" }}>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `flex flex-col items-center py-2 text-[10px] ${isActive ? "text-[var(--gs-primary-2)]" : "text-[var(--gs-muted)]"}`}><n.icon className="h-4 w-4 mb-0.5"/>{n.label}</NavLink>
        ))}
      </nav>
      <CopilotSidebar/>
    </div>
  );
}
