import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { AlertTriangle, Bot, Coins, LogOut, Menu, Settings, ShoppingBag, UserRound, FlaskConical, CircleHelp } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { api } from "@/lib/api";

const PRIMARY = [
  { to: "/dashboard", label: "Build with Neo", icon: Bot, end: true },
  { to: "/shop", label: "Shop Getszy", icon: ShoppingBag },
  { to: "/dashboard/my-getszy", label: "My Getszy", icon: UserRound },
];

function firstName(name) {
  return String(name || "").trim().split(/\s+/)[0] || "Customer";
}

function creditMessage(credit) {
  const status = credit?.credit_status;
  if (status === "empty") return "No paid credits left — choose a prepaid top-up to continue digital work.";
  if (status === "critical") return `Only ${credit.credits} paid credits remain. Top up soon.`;
  if (status === "low") return `${credit.credits} paid credits remain. Consider topping up.`;
  return "Your paid credit balance is healthy.";
}

export default function DashboardLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [credit, setCredit] = useState(null);

  useEffect(() => { if (!loading && !user) navigate("/login"); }, [user, loading, navigate]);
  useEffect(() => {
    if (!user) return undefined;
    let active = true;
    api.get("/credits/me").then((response) => { if (active) setCredit(response.data); }).catch(() => { if (active) setCredit(null); });
    return () => { active = false; };
  }, [user]);
  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;

  const closeAndNavigate = (to) => {
    setMobileNavOpen(false);
    navigate(to);
  };

  const NavContent = ({ onNavigate }) => (
    <>
      <div className="border-b px-5 py-5" style={{ borderColor: "var(--gs-border)" }}>
        <div className="font-display text-2xl tracking-tight">getszy</div>
        <div className="mt-1 text-xs text-[var(--gs-muted)]">Your products, projects & support</div>
      </div>

      <nav className="flex-1 space-y-1 p-3" aria-label="Customer workspace navigation">
        <div className="px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-[.16em] text-[var(--gs-muted)]">Your Getszy</div>
        {PRIMARY.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              data-testid={`customer-nav-${item.label.toLowerCase().replaceAll(" ", "-")}`}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-colors ${isActive ? "bg-[#183c3c] font-semibold text-white" : "text-[var(--gs-ink)] hover:bg-[var(--gs-surface-2)]"}`}
            >
              <Icon className="h-4 w-4" />{item.label}
            </NavLink>
          );
        })}

        {credit && <button type="button" onClick={() => { onNavigate?.(); navigate("/dashboard/my-getszy"); }} className="mx-2 mt-3 w-[calc(100%-1rem)] rounded-xl border p-3 text-left transition-colors hover:bg-[#fffdf7]" style={{ borderColor: credit.credit_status === "healthy" || credit.credit_status === "exempt" ? "var(--gs-border)" : "#efc777", background: credit.credit_status === "healthy" || credit.credit_status === "exempt" ? "var(--gs-surface-2)" : "#fff7df" }}><div className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--gs-ink)]"><Coins className="h-4 w-4 text-[#a66a00]" />Paid credits</span><span className="text-sm font-bold text-[var(--gs-ink)]">{credit.billing_exempt ? "Included" : credit.credits}</span></div>{!credit.billing_exempt && <div className="mt-1.5 text-[11px] leading-4 text-[var(--gs-muted)]">{creditMessage(credit)}</div>}{credit.access_model === "prepaid_credits_only" && <div className="mt-1 text-[11px] text-[var(--gs-muted)]">Prepaid access · Digital work requires credits</div>}</button>}
        <div className="my-4 border-t" style={{ borderColor: "var(--gs-border)" }} />
        <button type="button" onClick={() => { onNavigate?.(); navigate("/support"); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-[var(--gs-ink)] transition-colors hover:bg-[var(--gs-surface-2)]">
          <CircleHelp className="h-4 w-4" />Help & support
        </button>
        {user.role === "admin" && (
          <>
            <button type="button" onClick={() => { onNavigate?.(); navigate("/admin"); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-[var(--gs-ink)] transition-colors hover:bg-[var(--gs-surface-2)]">
              <Settings className="h-4 w-4" />Platform Admin
            </button>
            <button type="button" onClick={() => { onNavigate?.(); navigate("/labs"); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-[#6b3fa0] transition-colors hover:bg-[#f3edff]">
              <FlaskConical className="h-4 w-4" />Internal Labs
            </button>
          </>
        )}
      </nav>

      <div className="border-t p-3" style={{ borderColor: "var(--gs-border)" }}>
        <div className="mb-3 rounded-xl bg-[var(--gs-surface-2)] px-3 py-2.5">
          <div className="truncate text-sm font-semibold text-[var(--gs-ink)]">{firstName(user.name)}</div>
          <div className="truncate text-xs text-[var(--gs-muted)]">{user.email}</div>
        </div>
        <button type="button" onClick={() => { onNavigate?.(); logout(); navigate("/"); }} className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-xs text-[var(--gs-muted)] transition-colors hover:bg-[var(--gs-surface-2)] hover:text-[var(--gs-ink)]" data-testid="dash-logout">
          <LogOut className="h-4 w-4" />Log out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[#f7f5f2] md:grid md:grid-cols-[246px_1fr]">
      <aside className="hidden min-h-screen flex-col border-r bg-[var(--gs-surface)] md:flex" style={{ borderColor: "var(--gs-border)" }}>
        <NavContent />
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b bg-[rgba(247,245,242,.92)] px-4 py-3 backdrop-blur md:hidden" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2">
            <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Open Getszy navigation" data-testid="dash-mobile-menu-button"><Menu className="h-5 w-5" /></Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex w-72 max-w-[85vw] flex-col p-0">
                <NavContent onNavigate={() => setMobileNavOpen(false)} />
              </SheetContent>
            </Sheet>
            <button type="button" onClick={() => navigate("/dashboard")} className="font-display text-xl">getszy</button>
          </div>
          <button type="button" onClick={() => closeAndNavigate("/dashboard/my-getszy")} className="rounded-full bg-[#e7f4ef] px-3 py-1.5 text-xs font-semibold text-[#183c3c]">My Getszy</button>
        </header>
        <main id="main-content" className="min-w-0 overflow-x-hidden p-4 md:p-6 lg:p-8" tabIndex={-1}>
          {credit && !credit.billing_exempt && ["empty", "critical", "low"].includes(credit.credit_status) && <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className={`mb-5 flex w-full items-start gap-3 rounded-2xl border p-4 text-left ${credit.credit_status === "empty" || credit.credit_status === "critical" ? "border-rose-200 bg-rose-50 text-rose-950" : "border-amber-200 bg-amber-50 text-amber-950"}`}><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" /><span><strong>{credit.credit_status === "empty" ? "Paid credits are empty." : "Low paid-credit balance."}</strong><span className="mt-0.5 block text-sm">{creditMessage(credit)} Open My Getszy to see your balance, usage and available plan options.</span></span></button>}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
