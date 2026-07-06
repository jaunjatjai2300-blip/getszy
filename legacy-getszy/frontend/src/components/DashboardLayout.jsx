import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Sparkles, LogOut, Store, GraduationCap, Rocket, Settings, ShoppingBag, FlaskConical, LayoutGrid, ChevronDown, ChevronRight, Film, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

// Customer-facing dashboard: Neo is the front door. Traditional menus are
// secondary and grouped, so users mostly stay inside the chat.
const PRIMARY = [
  { to: "/dashboard", label: "Neo", icon: Sparkles, end: true, primary: true },
  { to: "/dashboard/video-studio", label: "Video Studio", icon: Film, primary: true, badge: "NEW" },
];

const GROUPS = [
  {
    label: "Projects", icon: LayoutGrid, items: [
      { to: "/dashboard/projects", label: "All projects", icon: LayoutGrid },
      { to: "/dashboard/deployments", label: "Deployments", icon: Rocket },
    ],
  },
  {
    label: "Marketplace", icon: ShoppingBag, items: [
      { to: "/shop", label: "Store", icon: Store },
    ],
  },
  {
    label: "Account", icon: Settings, items: [
      { to: "/account", label: "Profile & billing", icon: Settings },
    ],
  },
];

export default function DashboardLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState({});
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => { if (!loading && !user) navigate("/login"); }, [user, loading, navigate]);
  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;

  const isFounder = user.role === "founder" || user.role === "admin";
  const toggle = (k) => setOpen(o => ({ ...o, [k]: !o[k] }));

  const NavContent = ({ onNavigate }) => (
    <>
      <div className="px-5 py-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
        <div className="font-display text-2xl">getszy</div>
        <div className="text-xs text-[var(--gs-muted)] mt-0.5">Workspace · {user.role || "customer"}</div>
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {PRIMARY.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} onClick={onNavigate} data-testid={`dash-nav-${n.label.toLowerCase()}`}
            className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive ? "bg-[var(--gs-teal)] text-white font-semibold shadow-sm" : "hover:bg-[var(--gs-surface-2)]"}`}>
            <n.icon className="h-4 w-4"/>{n.label}
          </NavLink>
        ))}
        {isFounder && (
          <NavLink to="/labs" onClick={onNavigate} data-testid="dash-nav-labs"
            className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${isActive ? "bg-[#7c3aed] text-white font-semibold" : "hover:bg-[var(--gs-surface-2)] text-[#7c3aed]"}`}>
            <FlaskConical className="h-4 w-4"/>Internal Labs
          </NavLink>
        )}
        <div className="h-2"/>
        {GROUPS.map((g) => {
          const isOpen = open[g.label] !== false;
          return (
            <div key={g.label}>
              <button onClick={() => toggle(g.label)} className="w-full flex items-center gap-2 px-3 py-2 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] hover:text-[var(--gs-ink)]">
                {isOpen ? <ChevronDown className="h-3 w-3"/> : <ChevronRight className="h-3 w-3"/>}
                <g.icon className="h-3.5 w-3.5"/>
                <span className="flex-1 text-left">{g.label}</span>
              </button>
              {isOpen && (
                <div className="ml-3 space-y-0.5 border-l" style={{ borderColor: "var(--gs-border)" }}>
                  {g.items.map((n) => (
                    <NavLink key={n.to} to={n.to} onClick={onNavigate}
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
        {user.role === "admin" && (
          <button onClick={() => { onNavigate?.(); navigate("/admin"); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="dash-goto-admin">
            <Settings className="h-4 w-4"/>Platform Admin
          </button>
        )}
        <button onClick={() => { onNavigate?.(); logout(); navigate("/"); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--gs-muted)] hover:text-[var(--gs-ink)]" data-testid="dash-logout">
          <LogOut className="h-4 w-4"/>Logout
        </button>
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
              <Button variant="ghost" size="icon" data-testid="dash-mobile-menu-button"><Menu className="h-5 w-5"/></Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-0 flex flex-col">
              <NavContent onNavigate={() => setMobileNavOpen(false)}/>
            </SheetContent>
          </Sheet>
          <div className="font-display text-xl">getszy</div>
        </div>
      </div>
      <main id="main-content" className="p-4 md:p-6 overflow-x-hidden" tabIndex={-1}>
        <Outlet/>
      </main>
    </div>
  );
}
