import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle, ArrowRight, Bot, ChevronRight, Coins, Compass, FileText,
  Loader2, Package, Palette, RefreshCw, Rocket, SearchCheck, ShoppingBag,
  Sparkles, Wand2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

// The dashboard front door. Reva's command bar routes a real goal into the
// real builder/chat (handoff via sessionStorage — the key BuildStudio reads),
// and the workspace below answers, from real backend state:
//   what's happening · what needs attention · what to do next.
// No metric here is invented; every number comes from a live endpoint, and an
// endpoint that fails degrades to an honest empty/unavailable state.

const QUICK_STARTS = [
  {
    id: "launch",
    title: "Launch a digital presence",
    description: "Turn an approved brief into a credible website or launch page — reviewed privately before anything goes live.",
    icon: Rocket,
    action: "Start a build",
    to: "/dashboard/build",
    prompt: "I want to launch a professional digital presence.",
  },
  {
    id: "content",
    title: "Create content with a plan",
    description: "Shape an approved offer into a clear content direction before generating assets.",
    icon: Sparkles,
    action: "Plan content",
    to: "/dashboard/creator",
    prompt: "I want to create content around an approved offer.",
  },
  {
    id: "help",
    title: "Help me choose a path",
    description: "Tell Reva what you want to achieve and get a guided, editable starting plan.",
    icon: Bot,
    action: "Talk to Reva",
    to: "/dashboard/chat",
    prompt: "I need help choosing the right Getszy digital solution.",
  },
];

const SUGGESTIONS = ["Launch a website", "Create a campaign plan", "Build my brand", "I need guidance"];

const WEBSITE_RE = /\b(landing\s*page|website|web\s*app|store\s*front|storefront|site|page)\b/i;
const REVIEW_STATES = new Set(["needs_work", "failed", "error", "rejected", "rejected_no_charge"]);

function firstName(name) {
  return String(name || "there").trim().split(/\s+/)[0] || "there";
}

function creditStatus(credit, role) {
  if (!credit) return "unknown";
  if (credit.billing_exempt || role === "admin" || role === "founder") return "exempt";
  if (credit.credit_status) return credit.credit_status;
  const balance = Number(credit.credits ?? 0);
  if (balance <= 0) return "empty";
  if (balance <= 5) return "critical";
  if (balance <= 20) return "low";
  return "healthy";
}

// Hand the typed goal to the builder the way the builder actually reads it.
// The mismatch this replaces (localStorage vs sessionStorage) silently dropped
// every prompt a customer typed on this page.
function stashDraft(prompt, intention) {
  try {
    if (prompt) {
      sessionStorage.setItem(
        "getszy_mission_draft",
        JSON.stringify({ prompt, intention, createdAt: new Date().toISOString() }),
      );
    }
  } catch { /* a storage failure must never block navigation into the build */ }
}

export default function MissionWorkspace() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [mission, setMission] = useState("");
  const [data, setData] = useState({
    loading: true, failed: false,
    credit: null, projects: [], sessions: [], orders: [],
  });
  const displayName = useMemo(() => firstName(user?.name), [user?.name]);

  const load = () => {
    setData((d) => ({ ...d, loading: true, failed: false }));
    Promise.allSettled([
      api.get("/credits/me"),
      api.get("/builder/projects"),
      api.get("/agents/sessions"),
      api.get("/orders/mine"),
    ]).then(([credit, projects, sessions, orders]) => {
      const anyOk = [credit, projects, sessions, orders].some((r) => r.status === "fulfilled");
      setData({
        loading: false,
        failed: !anyOk,
        credit: credit.status === "fulfilled" ? credit.value.data : null,
        projects: projects.status === "fulfilled" ? (projects.value.data || []) : [],
        sessions: sessions.status === "fulfilled" ? (sessions.value.data?.sessions || []) : [],
        orders: orders.status === "fulfilled" ? (orders.value.data || []) : [],
      });
    });
  };

  useEffect(() => { load(); }, []);

  const status = creditStatus(data.credit, user?.role);
  const credits = data.credit ? Number(data.credit.credits ?? 0) : null;
  const buildCost = data.credit?.costs?.builder_website;

  const projectsNeedingReview = useMemo(
    () => data.projects.filter((p) => REVIEW_STATES.has(String(p.quality_report?.status || p.status || "").toLowerCase())),
    [data.projects],
  );
  const activeOrders = useMemo(
    () => data.orders.filter((o) => ["pending", "forwarded"].includes(String(o.status || "").toLowerCase())),
    [data.orders],
  );
  const recentProjects = useMemo(() => data.projects.slice(0, 3), [data.projects]);
  const recentSessions = useMemo(() => data.sessions.slice(0, 2), [data.sessions]);

  // "What needs attention" — real, actionable, ordered by urgency. Empty when clear.
  const attention = useMemo(() => {
    const items = [];
    if (["empty", "critical"].includes(status)) {
      items.push({
        id: "credits", tone: "urgent", icon: Coins,
        title: status === "empty" ? "You're out of credits" : `Only ${credits} credits left`,
        detail: "Digital work needs prepaid credits. Top up to keep building.",
        cta: "Top up", onClick: () => navigate("/pricing"),
      });
    } else if (status === "low") {
      items.push({
        id: "credits", tone: "warn", icon: Coins,
        title: `${credits} credits remaining`,
        detail: "A little low — consider topping up before your next build.",
        cta: "View plans", onClick: () => navigate("/pricing"),
      });
    }
    projectsNeedingReview.slice(0, 2).forEach((p) => {
      items.push({
        id: `proj-${p.id}`, tone: "warn", icon: SearchCheck,
        title: `${p.name || "Your draft"} needs review`,
        detail: "The quality check flagged this build. Open it to review or rebuild.",
        cta: "Open", onClick: () => navigate(`/dashboard/projects/${p.id}`),
      });
    });
    activeOrders.slice(0, 1).forEach((o) => {
      items.push({
        id: `order-${o.id || o.order_number}`, tone: "info", icon: Package,
        title: `Order ${o.order_number || ""} is ${o.status}`.trim(),
        detail: "Track progress and support for your Getszy order.",
        cta: "Track", onClick: () => navigate("/dashboard/my-getszy"),
      });
    });
    return items;
  }, [status, credits, projectsNeedingReview, activeOrders, navigate]);

  const begin = (choice) => {
    const prompt = (mission || choice?.prompt || "").trim();
    const website = WEBSITE_RE.test(prompt);
    const intention = choice?.id || (website ? "website" : "guided");
    const destination = choice?.to || (website ? "/dashboard/build" : "/dashboard/chat");
    stashDraft(prompt, intention);
    navigate(destination);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8" data-testid="mission-workspace">
      {/* ── Reva command bar ── */}
      <section
        className="relative overflow-hidden rounded-3xl border p-6 sm:p-8 lg:p-10"
        style={{ background: "linear-gradient(135deg, #183c3c 0%, #245a57 62%, #2d716c 100%)", borderColor: "rgba(255,255,255,.14)" }}
      >
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
        <div className="relative grid gap-8 lg:grid-cols-[1.35fr_.65fr] lg:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold tracking-wide text-white">
              <Sparkles className="h-3.5 w-3.5" /> REVA · YOUR GETSZY CO-PILOT
            </div>
            <p className="text-sm text-white/70">Welcome back, {displayName}.</p>
            <h1 className="mt-2 max-w-3xl font-display text-3xl leading-tight text-white sm:text-4xl lg:text-5xl">
              What would you like to build or grow today?
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/75 sm:text-base">
              Tell Reva your goal. A website request opens the builder with your brief already in place; every finished build gets its own private project workspace and preview.
            </p>

            <div className="mt-6 rounded-2xl border border-white/20 bg-white p-2 shadow-xl shadow-black/10">
              <div className="flex flex-col gap-2 sm:flex-row">
                <label className="sr-only" htmlFor="mission-input">Tell Reva what you want to achieve</label>
                <input
                  id="mission-input"
                  value={mission}
                  onChange={(event) => setMission(event.target.value)}
                  onKeyDown={(event) => { if (event.key === "Enter" && mission.trim()) begin(); }}
                  placeholder="For example: I want a professional launch page for my skincare offer"
                  className="min-w-0 flex-1 rounded-xl border-0 px-4 py-3 text-sm text-[var(--gs-ink)] outline-none ring-0 placeholder:text-[var(--gs-muted)]"
                />
                <button
                  type="button"
                  onClick={() => begin()}
                  disabled={!mission.trim()}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#183c3c] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#102f2f] disabled:opacity-50"
                  data-testid="mission-start-button"
                >
                  Start with Reva <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Mission suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setMission(suggestion)}
                  className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs text-white transition-colors hover:bg-white/20"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* live state, not decoration */}
          <aside className="rounded-2xl border border-white/15 bg-[#102f2f]/45 p-4 backdrop-blur-sm" aria-label="Your workspace at a glance">
            <div className="text-[11px] font-semibold uppercase tracking-[.16em] text-white/60">At a glance</div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="rounded-xl bg-white/10 px-2 py-3 transition-colors hover:bg-white/15">
                <div className="font-display text-2xl text-white">{data.loading ? "—" : status === "exempt" ? "∞" : credits ?? "—"}</div>
                <div className="mt-0.5 text-[11px] text-white/70">Credits</div>
              </button>
              <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="rounded-xl bg-white/10 px-2 py-3 transition-colors hover:bg-white/15">
                <div className="font-display text-2xl text-white">{data.loading ? "—" : data.projects.length}</div>
                <div className="mt-0.5 text-[11px] text-white/70">Projects</div>
              </button>
              <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="rounded-xl bg-white/10 px-2 py-3 transition-colors hover:bg-white/15">
                <div className="font-display text-2xl text-white">{data.loading ? "—" : data.orders.length}</div>
                <div className="mt-0.5 text-[11px] text-white/70">Orders</div>
              </button>
            </div>
            <div className="mt-3 flex items-center gap-2 text-[11px] leading-4 text-white/60">
              <Bot className="h-3.5 w-3.5 shrink-0" /> Reva suggests. You review and approve important actions.
            </div>
          </aside>
        </div>
      </section>

      {/* ── Needs attention (only when there is something real) ── */}
      {!data.loading && attention.length > 0 && (
        <section aria-label="What needs your attention" className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-muted)]">
            <AlertTriangle className="h-4 w-4 text-[#b4783f]" /> Needs your attention
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {attention.map((item) => {
              const Icon = item.icon;
              const ring = item.tone === "urgent" ? "border-rose-200 bg-rose-50" : item.tone === "warn" ? "border-amber-200 bg-amber-50" : "border-sky-200 bg-sky-50";
              const chip = item.tone === "urgent" ? "bg-rose-100 text-rose-700" : item.tone === "warn" ? "bg-amber-100 text-amber-700" : "bg-sky-100 text-sky-700";
              return (
                <div key={item.id} className={`flex flex-col rounded-2xl border p-4 ${ring}`}>
                  <div className="flex items-start gap-3">
                    <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${chip}`}><Icon className="h-4 w-4" /></span>
                    <div className="min-w-0">
                      <div className="font-semibold text-[var(--gs-ink)]">{item.title}</div>
                      <p className="mt-0.5 text-sm leading-5 text-[var(--gs-muted)]">{item.detail}</p>
                    </div>
                  </div>
                  <button type="button" onClick={item.onClick} className="mt-3 inline-flex items-center gap-1 self-start text-sm font-semibold text-[var(--gs-ink)] hover:underline">
                    {item.cta} <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Failed-to-load: honest, recoverable ── */}
      {!data.loading && data.failed && (
        <section className="flex flex-col items-center gap-3 rounded-3xl border border-dashed p-8 text-center" style={{ borderColor: "var(--gs-border)" }}>
          <div className="grid h-12 w-12 place-items-center rounded-full bg-[var(--gs-surface-2)]"><RefreshCw className="h-5 w-5 text-[var(--gs-muted)]" /></div>
          <div className="font-semibold text-[var(--gs-ink)]">We couldn't reach your workspace</div>
          <p className="max-w-md text-sm leading-6 text-[var(--gs-muted)]">Your data is safe on the server — this is only a connection issue. You can still start something new below, or retry.</p>
          <button type="button" onClick={load} className="inline-flex items-center gap-2 rounded-xl bg-[#183c3c] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#102f2f]">
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        </section>
      )}

      <section className="grid gap-4 xl:grid-cols-[1.15fr_.85fr]">
        {/* ── Continue where you left off (what's happening) ── */}
        <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]"><Compass className="h-4 w-4" /> Continue</div>
              <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Pick up where you left off.</h2>
            </div>
            <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">All projects <ArrowRight className="h-4 w-4" /></button>
          </div>

          <div className="mt-5 space-y-2">
            {data.loading ? (
              <>
                <div className="h-16 animate-pulse rounded-2xl bg-[var(--gs-surface-2)]" />
                <div className="h-16 animate-pulse rounded-2xl bg-[var(--gs-surface-2)]" />
              </>
            ) : recentProjects.length === 0 && recentSessions.length === 0 ? (
              <div className="rounded-2xl border border-dashed p-6 text-center" style={{ borderColor: "var(--gs-border)" }}>
                <div className="font-medium text-[var(--gs-ink)]">No mission started yet</div>
                <p className="mx-auto mt-1 max-w-sm text-sm leading-5 text-[var(--gs-muted)]">Tell Reva a goal above, or choose a starting point. Your work will appear here so you can return to it anytime.</p>
              </div>
            ) : (
              <>
                {recentProjects.map((p) => {
                  const s = String(p.quality_report?.status || p.status || "").toLowerCase();
                  const needsReview = REVIEW_STATES.has(s);
                  return (
                    <button key={p.id} type="button" onClick={() => navigate(`/dashboard/projects/${p.id}`)} className="flex w-full items-center gap-3 rounded-2xl border p-4 text-left transition-colors hover:bg-[#fbfdfc]" style={{ borderColor: "var(--gs-border)" }}>
                      <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#1e6c5d]"><Wand2 className="h-5 w-5" /></span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-semibold text-sm text-[var(--gs-ink)]">{p.name || "Getszy digital project"}</div>
                        <div className="mt-1 text-xs text-[var(--gs-muted)]">{s ? `Quality: ${s.replaceAll("_", " ")}` : "Open project workspace"}</div>
                      </div>
                      {needsReview
                        ? <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">Review</span>
                        : <ChevronRight className="h-4 w-4 text-[var(--gs-muted)]" />}
                    </button>
                  );
                })}
                {recentProjects.length === 0 && recentSessions.map((session) => (
                  <button key={session.session_id} type="button" onClick={() => navigate(`/dashboard/chat/${session.session_id}`)} className="flex w-full items-center gap-3 rounded-2xl border p-4 text-left transition-colors hover:bg-[#fbfdfc]" style={{ borderColor: "var(--gs-border)" }}>
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#1e6c5d]"><Bot className="h-5 w-5" /></span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-semibold text-sm text-[var(--gs-ink)]">{session.agent_name || "Reva conversation"}</div>
                      <div className="mt-1 truncate text-xs text-[var(--gs-muted)]">{session.last_message || "Continue your guided conversation"}</div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-[var(--gs-muted)]" />
                  </button>
                ))}
              </>
            )}
          </div>
        </div>

        {/* ── Start something new ── */}
        <aside className="rounded-3xl border bg-[#fffdf9] p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]"><Sparkles className="h-4 w-4" /> Start something new</div>
          <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Choose an outcome.</h2>
          <div className="mt-4 space-y-2">
            {QUICK_STARTS.map((choice) => {
              const Icon = choice.icon;
              return (
                <button key={choice.id} type="button" onClick={() => begin(choice)} className="flex w-full items-center gap-3 rounded-2xl border bg-white p-4 text-left transition-all hover:-translate-y-0.5 hover:border-[#7bb9af]" style={{ borderColor: "var(--gs-border)" }} data-testid={`mission-choice-${choice.id}`}>
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e7f4ef] text-[#183c3c]"><Icon className="h-5 w-5" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm text-[var(--gs-ink)]">{choice.title}</div>
                    <p className="mt-0.5 text-xs leading-5 text-[var(--gs-muted)]">{choice.description}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-[var(--gs-muted)]" />
                </button>
              );
            })}
          </div>
          <button type="button" onClick={() => navigate("/shop")} className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[var(--gs-teal)] hover:underline">
            <ShoppingBag className="h-4 w-4" /> Or shop Getszy products
          </button>
          {buildCost != null && (
            <div className="mt-4 flex items-start gap-2 rounded-xl bg-[var(--gs-surface-2)] px-3 py-2.5 text-xs leading-5 text-[var(--gs-muted)]">
              <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              A custom website build costs <strong className="mx-1 text-[var(--gs-ink)]">{buildCost}</strong> credits. Cost is shown again before anything is charged.
            </div>
          )}
        </aside>
      </section>
    </div>
  );
}
