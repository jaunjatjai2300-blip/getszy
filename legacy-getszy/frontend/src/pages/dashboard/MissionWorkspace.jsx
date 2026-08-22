import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight, Bot, CheckCircle2, CircleDashed, Compass, FileText,
  Lightbulb, MessageCircle, Palette, Rocket, SearchCheck, ShieldCheck,
  ShoppingBag, Sparkles, Wand2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

const MISSION_STEPS = [
  { label: "Understand", icon: MessageCircle },
  { label: "Founder brief", icon: FileText },
  { label: "Brand", icon: Palette },
  { label: "Evidence", icon: ShieldCheck },
  { label: "Plan", icon: Compass },
  { label: "Build", icon: Wand2 },
  { label: "Review", icon: SearchCheck },
  { label: "Approve", icon: CheckCircle2 },
];

const QUICK_STARTS = [
  {
    id: "launch",
    title: "Launch a digital presence",
    description: "Create a credible website or launch page from an approved brief—not a blank prompt.",
    icon: Rocket,
    action: "Start Founder Brief",
    to: "/dashboard/build",
    prompt: "I want to launch a professional digital presence.",
  },
  {
    id: "content",
    title: "Create content with a plan",
    description: "Turn an approved offer into a clear content direction before creating assets.",
    icon: Sparkles,
    action: "Plan my content",
    to: "/dashboard/creator",
    prompt: "I want to create content around an approved offer.",
  },
  {
    id: "help",
    title: "Help me choose the right path",
    description: "Tell Neo what you want to achieve and get a guided, editable starting plan.",
    icon: Bot,
    action: "Talk to Neo",
    to: "/dashboard/chat",
    prompt: "I need help choosing the right Getszy digital solution.",
  },
];

function firstName(name) {
  return String(name || "there").trim().split(/\s+/)[0] || "there";
}

export default function MissionWorkspace() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [mission, setMission] = useState("");
  const [selected, setSelected] = useState(null);
  const displayName = useMemo(() => firstName(user?.name), [user?.name]);

  const begin = (choice) => {
    const draft = {
      prompt: (mission || choice?.prompt || "").trim(),
      intention: choice?.id || "guided",
      createdAt: new Date().toISOString(),
    };
    if (draft.prompt) sessionStorage.setItem("getszy_mission_draft", JSON.stringify(draft));
    navigate(choice?.to || "/dashboard/chat");
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8" data-testid="mission-workspace">
      <section
        className="relative overflow-hidden rounded-3xl border p-6 sm:p-8 lg:p-10"
        style={{ background: "linear-gradient(135deg, #183c3c 0%, #245a57 62%, #2d716c 100%)", borderColor: "rgba(255,255,255,.14)" }}
      >
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
        <div className="relative grid gap-8 lg:grid-cols-[1.3fr_.7fr] lg:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold tracking-wide text-white">
              <Sparkles className="h-3.5 w-3.5" /> NEO · YOUR GETSZY GUIDE
            </div>
            <p className="text-sm text-white/70">Welcome back, {displayName}.</p>
            <h1 className="mt-2 max-w-3xl font-display text-3xl leading-tight text-white sm:text-4xl lg:text-5xl">
              What would you like to build or grow today?
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/75 sm:text-base">
              Start with your goal. Neo will help you create an editable brief, identify what is missing, and keep every important decision visible before work begins.
            </p>

            <div className="mt-6 rounded-2xl border border-white/20 bg-white p-2 shadow-xl shadow-black/10">
              <div className="flex flex-col gap-2 sm:flex-row">
                <label className="sr-only" htmlFor="mission-input">Tell Neo what you want to achieve</label>
                <input
                  id="mission-input"
                  value={mission}
                  onChange={(event) => setMission(event.target.value)}
                  onKeyDown={(event) => { if (event.key === "Enter" && mission.trim()) begin(); }}
                  placeholder="For example: I want a professional launch page for my skincare offer"
                  className="min-w-0 flex-1 rounded-xl border-0 px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400"
                />
                <Button
                  type="button"
                  onClick={() => begin()}
                  disabled={!mission.trim()}
                  className="rounded-xl bg-[#183c3c] px-5 text-white hover:bg-[#102f2f]"
                  data-testid="mission-start-button"
                >
                  Start with Neo <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Mission suggestions">
              {["Launch a website", "Create a campaign plan", "Build my brand", "I need guidance"].map((suggestion) => (
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

          <aside className="rounded-2xl border border-white/15 bg-[#102f2f]/45 p-4 backdrop-blur-sm" aria-label="How Neo works">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[#d8f1e9] text-[#183c3c]"><Bot className="h-5 w-5" /></span>
              <div>
                <div className="font-semibold text-white">You remain in control</div>
                <div className="text-xs leading-5 text-white/70">Neo suggests. You review and approve important actions.</div>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[11px] text-white/80">
              <div className="rounded-xl bg-white/10 px-2 py-2">Brief first</div>
              <div className="rounded-xl bg-white/10 px-2 py-2">Private review</div>
              <div className="rounded-xl bg-white/10 px-2 py-2">Explicit approval</div>
            </div>
          </aside>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.45fr_.95fr]">
        <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]">Start a mission</div>
              <h2 className="mt-1 font-display text-2xl text-[var(--gs-ink)]">Choose an outcome, not a tool.</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--gs-muted)]">Getszy keeps internal tools in the background and brings in the right capability only after your goal is clear.</p>
            </div>
            <button type="button" onClick={() => navigate("/shop")} className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--gs-teal)] hover:underline">
              <ShoppingBag className="h-4 w-4" /> Shop Getszy
            </button>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {QUICK_STARTS.map((choice) => {
              const Icon = choice.icon;
              const active = selected === choice.id;
              return (
                <button
                  key={choice.id}
                  type="button"
                  onClick={() => setSelected(choice.id)}
                  className={`group min-h-[220px] rounded-2xl border p-4 text-left transition-all ${active ? "border-[#183c3c] bg-[#f0f8f5] ring-1 ring-[#183c3c]" : "border-[var(--gs-border)] bg-[var(--gs-surface)] hover:-translate-y-0.5 hover:border-[#7bb9af]"}`}
                  data-testid={`mission-choice-${choice.id}`}
                >
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#e7f4ef] text-[#183c3c]"><Icon className="h-5 w-5" /></span>
                  <h3 className="mt-5 font-display text-xl text-[var(--gs-ink)]">{choice.title}</h3>
                  <p className="mt-2 text-sm leading-5 text-[var(--gs-muted)]">{choice.description}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#183c3c]">{choice.action}<ArrowRight className="h-4 w-4" /></span>
                </button>
              );
            })}
          </div>
          {selected && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#183c3c] p-4 text-white">
              <p className="text-sm text-white/85">You can adjust the brief later. Neo will show what it understood before any plan is approved.</p>
              <Button type="button" onClick={() => begin(QUICK_STARTS.find((choice) => choice.id === selected))} className="rounded-xl bg-white text-[#183c3c] hover:bg-white/90">
                Continue <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <aside className="rounded-3xl border bg-[#fffdf9] p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]"><Compass className="h-4 w-4" /> Mission map</div>
          <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Every important step stays visible.</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Your next mission has not started yet. Once you begin, this map will show what is done, current, blocked and next.</p>
          <ol className="mt-5 space-y-2" aria-label="Mission workflow preview">
            {MISSION_STEPS.map((step, index) => {
              const Icon = step.icon;
              return (
                <li key={step.label} className="flex items-center gap-3 rounded-xl px-3 py-2">
                  <span className={`grid h-7 w-7 place-items-center rounded-full ${index === 0 ? "bg-[#183c3c] text-white" : "bg-[#efece6] text-[var(--gs-muted)]"}`}>
                    {index === 0 ? <CircleDashed className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                  </span>
                  <span className={`text-sm ${index === 0 ? "font-semibold text-[var(--gs-ink)]" : "text-[var(--gs-muted)]"}`}>{index === 0 ? "Current when you start" : step.label}</span>
                </li>
              );
            })}
          </ol>
        </aside>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border bg-white p-5" style={{ borderColor: "var(--gs-border)" }}>
          <div className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]">Trusted by design</div>
          <h3 className="mt-2 font-display text-xl">Approved facts, not invented claims.</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Neo can suggest words and structure, but public claims should come from information you review and approve.</p>
        </div>
        <div className="rounded-2xl border bg-white p-5" style={{ borderColor: "var(--gs-border)" }}>
          <div className="text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]">Private review</div>
          <h3 className="mt-2 font-display text-xl">Preview before important release.</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Use private review and mobile testing before any approved delivery or publishing step.</p>
        </div>
        <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="rounded-2xl border bg-[#e9f5ef] p-5 text-left transition-colors hover:bg-[#def0e7]" style={{ borderColor: "#b8dace" }}>
          <div className="text-xs font-semibold uppercase tracking-[.14em] text-[#216b59]">My Getszy</div>
          <h3 className="mt-2 font-display text-xl text-[#183c3c]">Orders, projects and support together.</h3>
          <p className="mt-2 text-sm leading-6 text-[#2f6056]">View what is genuinely active in your Getszy relationship.</p>
          <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#183c3c]">Open My Getszy <ArrowRight className="h-4 w-4" /></span>
        </button>
      </section>
    </div>
  );
}
