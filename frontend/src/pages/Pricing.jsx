import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, fmtINR } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Sparkles, Crown, Zap, ArrowRight } from "lucide-react";
import { toast } from "sonner";

const ICONS = { free: Zap, pro: Sparkles, elite: Crown };

export default function Pricing() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [interval, setInterval] = useState("monthly"); // monthly | yearly
  const [busy, setBusy] = useState(false);
  const [sub, setSub] = useState(null);

  useEffect(() => {
    api.get("/pricing").then(({ data }) => setPlans(data.plans));
    if (user) api.get("/me/subscription").then(({ data }) => setSub(data));
  }, [user]);

  const currentPlan = sub?.plan || "free";

  const handleCTA = async (planId) => {
    if (!user) { navigate("/login"); return; }
    if (planId === "free") return;
    setBusy(true);
    try {
      if (planId === "pro" && !sub?.trial_started_at) {
        await api.post("/me/subscription/start-trial");
        toast.success("🎉 Welcome to Pro — 7-day free trial started!");
        await refresh();
        const { data } = await api.get("/me/subscription"); setSub(data);
      } else {
        const { data } = await api.post("/me/subscription/upgrade", { plan: planId, interval });
        toast.info(data.message || "Payment activation in progress", { duration: 6000 });
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="pricing-page">
      <section className="gs-ai-glow">
        <div className="gs-container py-14 text-center">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-teal)] mb-3">Pricing</div>
          <h1 className="font-display text-4xl sm:text-5xl mb-3">Pick the plan that fits your journey</h1>
          <p className="text-[var(--gs-muted)] max-w-2xl mx-auto">Start free. Upgrade when you want Advanced courses + AI Studio. Cancel anytime.</p>
          <div className="inline-flex mt-6 p-1 rounded-full border bg-white" style={{ borderColor: "var(--gs-border)" }}>
            <button onClick={() => setInterval("monthly")} className={`px-5 py-2 text-sm rounded-full ${interval === "monthly" ? "bg-[var(--gs-ink)] text-white" : ""}`} data-testid="pricing-monthly-toggle">Monthly</button>
            <button onClick={() => setInterval("yearly")} className={`px-5 py-2 text-sm rounded-full ${interval === "yearly" ? "bg-[var(--gs-ink)] text-white" : ""}`} data-testid="pricing-yearly-toggle">Yearly <Badge className="ml-1 bg-emerald-100 text-emerald-800 hover:opacity-100">Save 17%</Badge></button>
          </div>
        </div>
      </section>
      <section className="gs-container pb-16">
        <div className="grid md:grid-cols-3 gap-5">
          {plans.map((p) => {
            const Icon = ICONS[p.id] || Sparkles;
            const price = interval === "yearly" ? p.price_yearly : p.price_monthly;
            const isCurrent = currentPlan === p.id;
            return (
              <div key={p.id} className={`gs-card p-7 relative ${p.highlight ? "border-2 border-[var(--gs-teal)]" : ""}`} data-testid={`pricing-card-${p.id}`}>
                {p.highlight && <Badge className="absolute -top-3 right-6 bg-[var(--gs-teal)] hover:opacity-100">Most popular</Badge>}
                <div className="flex items-center gap-2 mb-2"><Icon className="h-5 w-5 text-[var(--gs-teal)]"/><h3 className="font-display text-2xl">{p.name}</h3></div>
                <p className="text-sm text-[var(--gs-muted)] mb-5">{p.tagline}</p>
                <div className="mb-5">
                  <span className="font-display text-4xl">{price === 0 ? "Free" : fmtINR(price)}</span>
                  {price !== 0 && <span className="text-sm text-[var(--gs-muted)] ml-1">/{interval === "yearly" ? "year" : "month"}</span>}
                </div>
                <ul className="space-y-2 mb-6 text-sm">{p.features.map((f) => (<li key={f} className="flex items-start gap-2"><Check className="h-4 w-4 text-[var(--gs-teal)] mt-0.5 flex-shrink-0"/>{f}</li>))}</ul>
                <Button onClick={() => handleCTA(p.id)} disabled={busy || isCurrent || p.id === "free"} className={`w-full h-12 ${p.highlight ? "bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" : p.id === "elite" ? "bg-[var(--gs-ink)] hover:bg-black text-white" : "bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`} data-testid={`pricing-cta-${p.id}`}>
                  {isCurrent ? "Current plan" : p.cta} {!isCurrent && p.id !== "free" && <ArrowRight className="h-4 w-4 ml-2"/>}
                </Button>
              </div>
            );
          })}
        </div>
        <p className="text-center text-xs text-[var(--gs-muted)] mt-8">Payments processed securely. Cancel anytime. Trial requires no card.</p>
      </section>
    </div>
  );
}
