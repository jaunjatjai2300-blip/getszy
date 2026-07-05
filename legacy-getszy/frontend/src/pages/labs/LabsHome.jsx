import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { FlaskConical, ArrowUp, Loader2, Beaker } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";

// Founder-only Labs. Renders the same underlying ChatHome workspace but with a
// distinct visual identity + a persistent "labs_experiment" bias in the intro.
export default function LabsHome() {
  const { user, loading } = useAuth();
  const nav = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) return nav("/login");
    if (user.role !== "founder" && user.role !== "admin") nav("/dashboard");
  }, [user, loading, nav]);

  const startExperiment = async () => {
    const t = prompt.trim();
    if (t.length < 4) return toast.error("Prompt too short");
    setBusy(true);
    try {
      const r = await api.post("/chat/session", { first_message: `Run a labs experiment: ${t}`, title: t.slice(0, 60) });
      nav(`/dashboard/chat/${r.data.id}`);
    } catch (e) { toast.error("Could not start"); }
    finally { setBusy(false); }
  };

  if (loading || !user || (user.role !== "founder" && user.role !== "admin")) return null;

  return (
    <div className="max-w-3xl mx-auto py-10" data-testid="labs-home">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-12 w-12 rounded-2xl grid place-items-center bg-[#7c3aed]/15">
          <FlaskConical className="h-6 w-6 text-[#7c3aed]"/>
        </div>
        <div>
          <h1 className="font-display text-3xl">Internal Labs</h1>
          <p className="text-xs text-[var(--gs-muted)] mt-1">Founder-only — experimental Neo capabilities, private prompts, secret templates. Not visible to customers.</p>
        </div>
      </div>

      <Card className="p-5">
        <div className="text-sm font-semibold mb-2 flex items-center gap-2"><Beaker className="h-4 w-4"/>Free-form experiment</div>
        <p className="text-[11px] text-[var(--gs-muted)] mb-3">Any prompt — will invoke the `labs_experiment` capability directly, bypassing customer routing.</p>
        <div className="relative">
          <Textarea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Draft a private-agent architecture that indexes our support tickets…"
            className="pr-14" data-testid="labs-input"/>
          <button onClick={startExperiment} disabled={busy || prompt.trim().length < 4}
            className="absolute right-3 bottom-3 h-9 w-9 rounded-xl bg-[#7c3aed] text-white grid place-items-center disabled:opacity-40"
            data-testid="labs-send">
            {busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <ArrowUp className="h-4 w-4"/>}
          </button>
        </div>
      </Card>

      <div className="mt-6 grid md:grid-cols-2 gap-3" data-testid="labs-suggestions">
        {[
          "Design a plugin system for third-party AI agents",
          "Draft a Getszy Enterprise pricing tier and feature matrix",
          "Propose a moat vs. Bolt/v0/Lovable given our Indian-first thesis",
          "Sketch a WhatsApp-first onboarding funnel for Tier-2 creators",
        ].map((s, i) => (
          <button key={i} onClick={() => setPrompt(s)} className="gs-card p-3 text-left text-xs hover:bg-[var(--gs-surface-2)]">
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
