import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight, BookOpen, Bot, ChevronRight, CircleHelp, Coins, CreditCard,
  FileText, Heart, History, Loader2, Package, Sparkles, UserRound,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api, fmtINR } from "@/lib/api";

const ORDER_TONE = {
  pending: "bg-amber-100 text-amber-800",
  forwarded: "bg-sky-100 text-sky-800",
  shipped: "bg-blue-100 text-blue-800",
  delivered: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-rose-100 text-rose-800",
};

function friendlyName(name) {
  return String(name || "there").trim().split(/\s+/)[0] || "there";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function EmptyState({ title, detail, action, onClick }) {
  return (
    <div className="rounded-2xl border border-dashed p-5 text-center" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
      <div className="font-medium text-[var(--gs-ink)]">{title}</div>
      <p className="mt-1 text-sm leading-5 text-[var(--gs-muted)]">{detail}</p>
      {action && <button type="button" onClick={onClick} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">{action}<ArrowRight className="h-4 w-4" /></button>}
    </div>
  );
}

export default function MyGetszy() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: true, orders: [], enrollments: [], subscription: null, sessions: [], builderProjects: [], credits: null, creditCosts: {}, creditTransactions: [] });

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get("/orders/mine"),
      api.get("/me/enrollments"),
      api.get("/me/subscription"),
              api.get("/agents/sessions"),
        api.get("/builder/projects"),
        api.get("/credits/me"),
        api.get("/credits/me/transactions?limit=8"),
      ]).then(([orders, enrollments, subscription, sessions, builderProjects, credits, creditTransactions]) => {

      if (!active) return;
      setState({
        loading: false,
        orders: orders.status === "fulfilled" ? (orders.value.data || []) : [],
        enrollments: enrollments.status === "fulfilled" ? (enrollments.value.data || []) : [],
        subscription: subscription.status === "fulfilled" ? subscription.value.data : null,
        sessions: sessions.status === "fulfilled" ? (sessions.value.data?.sessions || []) : [],
        builderProjects: builderProjects.status === "fulfilled" ? (builderProjects.value.data || []) : [],
        credits: credits.status === "fulfilled" ? Number(credits.value.data?.credits ?? 0) : null,
        creditCosts: credits.status === "fulfilled" ? (credits.value.data?.costs || {}) : {},
        creditTransactions: creditTransactions.status === "fulfilled" ? (creditTransactions.value.data?.items || []) : [],
      });
    });
    return () => { active = false; };
  }, []);

  const activeOrders = useMemo(() => state.orders.filter((order) => !["delivered", "cancelled"].includes(String(order.status || "").toLowerCase())), [state.orders]);
  const activeLearning = useMemo(() => state.enrollments.filter((enrollment) => Number(enrollment.progress || 0) < 1), [state.enrollments]);
  const activeProjectSessions = useMemo(() => state.sessions.slice(0, 3), [state.sessions]);
  const activeBuilderProjects = useMemo(() => state.builderProjects.slice(0, 3), [state.builderProjects]);
  const builderCost = state.creditCosts.builder_website;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8" data-testid="my-getszy-page">
      <section className="rounded-3xl border bg-white p-6 sm:p-8" style={{ borderColor: "var(--gs-border)" }}>
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]">My Getszy</div>
            <h1 className="mt-2 font-display text-3xl text-[var(--gs-ink)] sm:text-4xl">Everything you have chosen with Getszy, in one place.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--gs-muted)]">Track your physical orders, continue genuine digital work, review learning and get help without moving between separate dashboards.</p>
          </div>
          <div className="rounded-2xl bg-[#eaf5f0] px-4 py-3 text-sm text-[#24584e]">
            <div className="font-semibold">Hello, {friendlyName(user?.name)}</div>
            <div className="mt-0.5 text-xs">Your account remains private and under your control.</div>
          </div>
        </div>
      </section>

      {state.loading ? (
        <div className="flex min-h-[340px] items-center justify-center text-[var(--gs-muted)]"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading your Getszy relationship…</div>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Your Getszy overview">
            <button type="button" onClick={() => navigate("/shop")} className="rounded-2xl border bg-white p-5 text-left transition-colors hover:bg-[#fcfcfb]" style={{ borderColor: "var(--gs-border)" }}>
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#fff1e6] text-[#a84816]"><Package className="h-5 w-5" /></span>
              <div className="mt-5 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-muted)]">Physical orders</div>
              <div className="mt-1 font-display text-2xl text-[var(--gs-ink)]">{state.orders.length}</div>
              <div className="mt-1 text-sm text-[var(--gs-muted)]">{activeOrders.length ? `${activeOrders.length} currently active` : "Shop Getszy products"}</div>
            </button>
            <button type="button" onClick={() => navigate("/dashboard")} className="rounded-2xl border bg-white p-5 text-left transition-colors hover:bg-[#fcfcfb]" style={{ borderColor: "var(--gs-border)" }}>
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#1e6c5d]"><Sparkles className="h-5 w-5" /></span>
              <div className="mt-5 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-muted)]">Digital activity</div>
              <div className="mt-1 font-display text-2xl text-[var(--gs-ink)]">{state.builderProjects.length}</div>
              <div className="mt-1 text-sm text-[var(--gs-muted)]">{state.builderProjects.length ? "Professional project(s) in your workspace" : "Start a mission with Neo"}</div>
            </button>
            <button type="button" onClick={() => document.getElementById("credit-activity")?.scrollIntoView({ behavior: "smooth" })} className="rounded-2xl border bg-white p-5 text-left transition-colors hover:bg-[#fcfcfb]" style={{ borderColor: "var(--gs-border)" }}>
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#fff5d8] text-[#a66a00]"><Coins className="h-5 w-5" /></span>
              <div className="mt-5 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-muted)]">Available credits</div>
              <div className="mt-1 font-display text-2xl text-[var(--gs-ink)]">{state.credits === null ? "—" : state.credits}</div>
              <div className="mt-1 text-sm text-[var(--gs-muted)]">{builderCost ? `Custom website build: ${builderCost} credits` : "See real usage history"}</div>
            </button>
            <button type="button" onClick={() => navigate("/account")} className="rounded-2xl border bg-white p-5 text-left transition-colors hover:bg-[#fcfcfb]" style={{ borderColor: "var(--gs-border)" }}>
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#eeeaff] text-[#6444a7]"><UserRound className="h-5 w-5" /></span>
              <div className="mt-5 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-muted)]">Plan & profile</div>
              <div className="mt-1 font-display text-2xl text-[var(--gs-ink)]">{String(state.subscription?.plan || "free").replace(/^./, (letter) => letter.toUpperCase())}</div>
              <div className="mt-1 text-sm text-[var(--gs-muted)]">{state.subscription?.status || "Manage account settings"}</div>
            </button>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.25fr_.95fr]">
            <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><Package className="h-4 w-4" /> Physical orders</div>
                  <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Your order journey</h2>
                </div>
                <button type="button" onClick={() => navigate("/shop")} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Shop products <ArrowRight className="h-4 w-4" /></button>
              </div>
              <div className="mt-5 space-y-3">
                {state.orders.length === 0 ? <EmptyState title="No physical orders yet" detail="When you shop Getszy products, your confirmed orders and support path will appear here." action="Explore Shop" onClick={() => navigate("/shop")} /> : state.orders.slice(0, 5).map((order) => (
                  <div key={order.id || order.order_number} className="flex flex-wrap items-center gap-3 rounded-2xl border p-4" style={{ borderColor: "var(--gs-border)" }}>
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#fff1e6] text-[#a84816]"><Package className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-[var(--gs-ink)]">{order.order_number || "Getszy order"}</div>
                      <div className="mt-1 text-xs text-[var(--gs-muted)]">{formatDate(order.created_at)} · {order.items?.length || 0} item(s){order.tracking_number ? ` · Tracking ${order.tracking_number}` : ""}</div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${ORDER_TONE[String(order.status || "").toLowerCase()] || "bg-slate-100 text-slate-700"}`}>{order.status || "processing"}</span>
                    <div className="font-semibold text-sm text-[var(--gs-ink)]">{fmtINR(order.total || 0)}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl border bg-[#fffdf9] p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><CreditCard className="h-4 w-4" /> Your Getszy services</div>
              <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Plans, learning and account.</h2>
              <div className="mt-5 space-y-3">
                <div className="rounded-2xl border bg-white p-4" style={{ borderColor: "var(--gs-border)" }}>
                  <div className="text-sm font-semibold text-[var(--gs-ink)]">Your plan</div>
                  <p className="mt-1 text-sm text-[var(--gs-muted)]">{state.subscription ? `${String(state.subscription.plan || "free").replace(/^./, (letter) => letter.toUpperCase())} · ${state.subscription.status || "active"}` : "Plan details are available in your account."}{state.subscription?.current_period_end ? ` · Renews ${formatDate(state.subscription.current_period_end)}` : ""}</p>
                  <div className="mt-3 rounded-xl bg-[#fff7df] px-3 py-2 text-xs text-[#80570c]">Available credits: <strong>{state.credits === null ? "—" : state.credits}</strong>{builderCost ? ` · A custom website build costs ${builderCost} credits` : ""}</div>
                  <Link to="/account" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Manage plan & profile <ArrowRight className="h-4 w-4" /></Link>
                </div>
                <div className="rounded-2xl border bg-white p-4" style={{ borderColor: "var(--gs-border)" }}>
                  <div className="text-sm font-semibold text-[var(--gs-ink)]">Learning</div>
                  <p className="mt-1 text-sm text-[var(--gs-muted)]">{state.enrollments.length ? `${activeLearning.length} item(s) in progress and ${state.enrollments.length - activeLearning.length} completed.` : "Learning purchases and progress appear here when available."}</p>
                  <Link to="/account" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Open learning <ArrowRight className="h-4 w-4" /></Link>
                </div>
              </div>
            </div>
          </section>

          <section id="credit-activity" className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
            <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
              <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><History className="h-4 w-4" /> Credit activity</div><h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Every grant, spend and refund is visible.</h2><p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Credits are added and deducted only by the server-side ledger. Getszy never relies on a browser balance to authorize paid work.</p></div><span className="rounded-full bg-[#fff5d8] px-3 py-1.5 text-sm font-semibold text-[#80570c]">{state.credits === null ? "—" : state.credits} credits</span></div>
              <div className="mt-5 space-y-2">{state.creditTransactions.length === 0 ? <EmptyState title="No credit activity yet" detail="Subscription grants, approved top-ups, builds, refinements and refunds will appear here with their real balance." /> : state.creditTransactions.map((transaction, index) => <div key={transaction.id || index} className="flex flex-wrap items-center gap-3 rounded-2xl border p-4" style={{ borderColor: "var(--gs-border)" }}><span className={`grid h-9 w-9 place-items-center rounded-xl ${Number(transaction.amount || 0) >= 0 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}><Coins className="h-4 w-4" /></span><div className="min-w-0 flex-1"><div className="text-sm font-semibold text-[var(--gs-ink)]">{String(transaction.action || transaction.type || "credit activity").replaceAll("_", " ")}</div><div className="mt-1 text-xs text-[var(--gs-muted)]">{formatDate(transaction.created_at)}{transaction.reason ? ` · ${transaction.reason}` : ""}</div></div><div className={`text-sm font-bold ${Number(transaction.amount || 0) >= 0 ? "text-emerald-700" : "text-amber-700"}`}>{Number(transaction.amount || 0) >= 0 ? "+" : ""}{transaction.amount ?? 0}</div><div className="text-xs text-[var(--gs-muted)]">Balance {transaction.balance_after ?? "—"}</div></div>)}</div>
            </div>
            <aside className="rounded-3xl border bg-[#fffdf9] p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><CreditCard className="h-4 w-4" /> Before you build</div><h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Costs are visible before paid work starts.</h2><p className="mt-3 text-sm leading-6 text-[var(--gs-muted)]">A custom website build uses {builderCost ?? "the configured"} credits. A professional starter template does not consume generation credits. The backend performs the final balance check and atomic deduction when you confirm a build.</p><button type="button" onClick={() => navigate("/dashboard/build")} className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Open Build with Neo <ArrowRight className="h-4 w-4" /></button></aside>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
            <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><Bot className="h-4 w-4" /> Digital projects</div>
                  <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Continue with clarity.</h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Existing guided conversations are shown here. Dedicated Founder Briefs, approvals, evidence and versions will appear here only when their corresponding project records are live.</p>
                </div>
                <button type="button" onClick={() => navigate("/dashboard")} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Start a mission <ArrowRight className="h-4 w-4" /></button>
              </div>
              <div className="mt-5 space-y-2">
                {activeBuilderProjects.length > 0 && activeBuilderProjects.map((builderProject) => (
                  <Link key={builderProject.id} to={`/dashboard/projects/${builderProject.id}`} className="flex items-center gap-3 rounded-2xl border p-4 transition-colors hover:bg-[#fbfdfc]" style={{ borderColor: "var(--gs-border)" }}>
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#1e6c5d]"><Sparkles className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-sm text-[var(--gs-ink)]">{builderProject.name || "Getszy digital project"}</div>
                      <div className="mt-1 truncate text-xs text-[var(--gs-muted)]">{builderProject.quality_report?.status ? `Quality: ${String(builderProject.quality_report.status).replaceAll("_", " ")}` : "Open mission controls"}</div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-[var(--gs-muted)]" />
                  </Link>
                ))}
                {activeBuilderProjects.length === 0 && activeProjectSessions.length === 0 && <EmptyState title="No digital mission has started" detail="Start with Neo when you are ready. Getszy will show what it understands before you approve a plan." action="Talk to Neo" onClick={() => navigate("/dashboard")} />}
                {activeBuilderProjects.length === 0 && activeProjectSessions.map((session) => (
                  <Link key={session.session_id} to={`/dashboard/chat/${session.session_id}`} className="flex items-center gap-3 rounded-2xl border p-4 transition-colors hover:bg-[#fbfdfc]" style={{ borderColor: "var(--gs-border)" }}>
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#1e6c5d]"><Bot className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1"><div className="font-semibold text-sm text-[var(--gs-ink)]">{session.agent_name || "Neo conversation"}</div><div className="mt-1 truncate text-xs text-[var(--gs-muted)]">{session.last_message || "Continue your guided conversation"}</div></div>
                    <ChevronRight className="h-4 w-4 text-[var(--gs-muted)]" />
                  </Link>
                ))}
              </div>
            </div>

            <aside className="rounded-3xl border bg-[#183c3c] p-5 text-white sm:p-6" style={{ borderColor: "rgba(255,255,255,.12)" }}>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[#bde8dc]"><Heart className="h-4 w-4" /> You stay in control</div>
              <h2 className="mt-2 font-display text-2xl">Private by default. Clear at every step.</h2>
              <p className="mt-3 text-sm leading-6 text-white/75">Your orders, project information and preferences are kept in their own customer contexts. Important external actions should always show the result, the reason and the approval required.</p>
              <div className="mt-6 space-y-2">
                <button type="button" onClick={() => navigate("/account")} className="flex w-full items-center justify-between rounded-xl bg-white/10 px-4 py-3 text-left text-sm transition-colors hover:bg-white/15"><span className="inline-flex items-center gap-2"><UserRound className="h-4 w-4" /> Profile & preferences</span><ChevronRight className="h-4 w-4" /></button>
                <button type="button" onClick={() => navigate("/support")} className="flex w-full items-center justify-between rounded-xl bg-white/10 px-4 py-3 text-left text-sm transition-colors hover:bg-white/15"><span className="inline-flex items-center gap-2"><CircleHelp className="h-4 w-4" /> Get support</span><ChevronRight className="h-4 w-4" /></button>
                <button type="button" onClick={() => navigate("/account")} className="flex w-full items-center justify-between rounded-xl bg-white/10 px-4 py-3 text-left text-sm transition-colors hover:bg-white/15"><span className="inline-flex items-center gap-2"><FileText className="h-4 w-4" /> Account details</span><ChevronRight className="h-4 w-4" /></button>
              </div>
            </aside>
          </section>
        </>
      )}
    </div>
  );
}
