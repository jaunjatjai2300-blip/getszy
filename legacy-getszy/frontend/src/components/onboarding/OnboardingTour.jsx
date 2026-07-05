import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Sparkles, PenTool, Film, Globe, Youtube, Rocket, Layers, ArrowRight, Check } from "lucide-react";

const STEPS = [
  {
    key: "welcome",
    icon: Sparkles,
    title: "Welcome to Getszy — meet Neo",
    body: "Neo is your AI Builder. Just tell it what to build — a reel script, faceless video, landing page, or channel plan — and it orchestrates the whole stack for you.",
    primary: { label: "Show me around", next: true },
  },
  {
    key: "chat",
    icon: PenTool,
    title: "1) Chat is the front door",
    body: "Everything starts with a chat. Ek plain-English request bhejo — Neo automatically decides whether to call the video studio, webapp builder, publishing agent, or trend forecaster.",
    highlights: [
      "Write a Hinglish reel script on personal finance",
      "Build a landing page for a Kathak academy",
      "Predict trending topics for Indian food creators",
    ],
    primary: { label: "Next", next: true },
  },
  {
    key: "workspace",
    icon: Layers,
    title: "2) Workspace = your project OS",
    body: "The right pane organizes Neo's outputs into 7 tabs — Preview, Plan, Tasks, Files, Timeline, Versions, and Deploy. Ek jagah full project context.",
    primary: { label: "Next", next: true },
  },
  {
    key: "deploy",
    icon: Rocket,
    title: "3) Deploy to *.getszy.com in one click",
    body: "Built a webapp? Open the Deploy tab, choose a subdomain, hit Deploy — Neo hosts it live at yourslug.getszy.com. Copy, share, iterate.",
    primary: { label: "Start building", next: false, cta: "chat" },
  },
];

export default function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const seen = localStorage.getItem("getszy.onboarding.v1");
    if (!seen) {
      // Small delay so it doesn't collide with initial render
      const t = setTimeout(() => setOpen(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const finish = () => {
    localStorage.setItem("getszy.onboarding.v1", new Date().toISOString());
    setOpen(false);
    setIdx(0);
  };

  const step = STEPS[idx];
  const Icon = step.icon;

  const next = () => {
    if (idx < STEPS.length - 1) setIdx(i => i + 1);
    else finish();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) finish(); }}>
      <DialogContent className="sm:max-w-lg" data-testid="onboarding-modal">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-11 w-11 rounded-2xl bg-[var(--gs-teal)]/15 grid place-items-center">
              <Icon className="h-5 w-5 text-[var(--gs-teal)]"/>
            </div>
            <div className="flex-1">
              <DialogTitle className="text-left text-xl font-display" data-testid="onboarding-title">{step.title}</DialogTitle>
              <div className="text-[10px] text-[var(--gs-muted)] tracking-wider uppercase mt-1">Step {idx + 1} of {STEPS.length}</div>
            </div>
          </div>
        </DialogHeader>

        <DialogDescription className="text-sm text-[var(--gs-muted)] leading-relaxed">
          {step.body}
        </DialogDescription>

        {step.highlights && (
          <ul className="space-y-1.5 mt-3" data-testid="onboarding-highlights">
            {step.highlights.map((h, i) => (
              <li key={i} className="text-xs flex items-start gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
                <Check className="h-3.5 w-3.5 text-[var(--gs-teal)] mt-0.5 shrink-0"/>
                <span>{h}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-1.5 mt-3">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === idx ? "w-6 bg-[var(--gs-teal)]" : i < idx ? "w-1.5 bg-[var(--gs-teal)]" : "w-1.5 bg-[var(--gs-border)]"}`}/>
          ))}
        </div>

        <DialogFooter className="mt-4 flex-row sm:flex-row justify-between gap-2">
          <button onClick={finish} className="text-xs text-[var(--gs-muted)] hover:text-[var(--gs-ink)] underline" data-testid="onboarding-skip">
            Skip tour
          </button>
          <Button
            onClick={() => {
              if (step.primary.cta === "chat") {
                finish();
                navigate("/dashboard");
              } else if (step.primary.next) {
                next();
              } else finish();
            }}
            className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
            data-testid="onboarding-next"
          >
            {step.primary.label}
            <ArrowRight className="h-4 w-4 ml-1"/>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
