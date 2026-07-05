import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtINR } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Check, Sparkles, Crown, Zap, ArrowRight, Loader2, Info } from "lucide-react";
import { toast } from "sonner";

const ICONS = { free: Zap, pro: Sparkles, elite: Crown };
const RAZORPAY_SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = RAZORPAY_SCRIPT;
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

export default function Pricing() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState("");
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.get("/billing/pricing").then(({ data }) => setPlans(data.plans || []));
    if (user) {
      api.get("/billing/status").then(({ data }) => setStatus(data)).catch(() => {});
    }
  }, [user]);

  const currentPlan = status?.current?.plan || "free";

  const handleCTA = async (planId) => {
    if (!user) { navigate("/login"); return; }
    if (planId === "free" || planId === currentPlan) return;
    setBusy(planId);
    try {
      const { data } = await api.post("/billing/subscribe", { plan: planId });
      if (!data.configured) {
        toast.info(data.message || "Payments coming soon — plan preview only", { duration: 6000 });
        return;
      }
      const ok = await loadRazorpayScript();
      if (!ok) { toast.error("Could not load Razorpay checkout"); return; }
      const rzp = new window.Razorpay({
        key: data.key_id,
        subscription_id: data.subscription_id,
        name: "Getszy",
        description: `${planId.toUpperCase()} monthly subscription`,
        theme: { color: "#0d9488" },
        prefill: { name: user.name, email: user.email },
        handler: async (resp) => {
          try {
            await api.post("/billing/verify", {
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_subscription_id: resp.razorpay_subscription_id,
              razorpay_signature: resp.razorpay_signature,
            });
            toast.success(`Welcome to ${planId.toUpperCase()} 🎉`);
            await refresh();
            const s = await api.get("/billing/status");
            setStatus(s.data);
          } catch (e) { toast.error("Payment verification failed"); }
        },
        modal: { ondismiss: () => toast.message("Checkout closed") },
      });
      rzp.open();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Subscribe failed");
    } finally { setBusy(""); }
  };

  const cancel = async () => {
    if (!confirm("Cancel your subscription? You'll be moved to Free at the end of the period.")) return;
    try {
      await api.post("/billing/cancel");
      toast.success("Cancelled");
      const s = await api.get("/billing/status");
      setStatus(s.data);
      await refresh();
    } catch (e) { toast.error("Cancel failed"); }
  };

  const notConfigured = user && status && status.configured === false;

  return (
    <div data-testid="pricing-page">
      <section className="gs-ai-glow">
        <div className="gs-container py-14 text-center">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-teal)] mb-3">Pricing</div>
          <h1 className="font-display text-4xl sm:text-5xl mb-3">Pick the plan that fits your journey</h1>
          <p className="text-[var(--gs-muted)] max-w-2xl mx-auto">Start free. Upgrade for AI Studio + unlimited Neo builds. Monthly billing, cancel anytime.</p>
          <div className="inline-flex mt-6 px-4 py-2 rounded-full border bg-white text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>
            Monthly · INR · GST included
          </div>
        </div>
      </section>

      {notConfigured && (
        <div className="gs-container">
          <div className="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 p-3 text-xs flex items-start gap-2" data-testid="billing-unconfigured-banner">
            <Info className="h-4 w-4 mt-0.5 shrink-0"/>
            <div>
              <b>Payments not yet enabled.</b> Plan previews are live; billing activates once Razorpay keys are added.
            </div>
          </div>
        </div>
      )}

      <section className="gs-container pb-16 pt-6">
        <div className="grid md:grid-cols-3 gap-5">
          {plans.map((p) => {
            const Icon = ICONS[p.id] || Sparkles;
            const price = p.price_monthly;
            const isCurrent = currentPlan === p.id;
            const priceLabel = price === 0 ? "Free" : (price == null ? "TBD" : fmtINR(price));
            return (
              <div key={p.id} className={`gs-card p-7 relative ${p.highlight ? "border-2 border-[var(--gs-teal)]" : ""}`} data-testid={`pricing-card-${p.id}`}>
                {p.highlight && <Badge className="absolute -top-3 right-6 bg-[var(--gs-teal)] hover:opacity-100">Most popular</Badge>}
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="h-5 w-5 text-[var(--gs-teal)]"/>
                  <h3 className="font-display text-2xl">{p.name}</h3>
                </div>
                <p className="text-sm text-[var(--gs-muted)] mb-5">{p.tagline}</p>
                <div className="mb-5">
                  <span className="font-display text-4xl">{priceLabel}</span>
                  {price !== 0 && price != null && <span className="text-sm text-[var(--gs-muted)] ml-1">/month</span>}
                  {price == null && <div className="text-[10px] text-[var(--gs-muted)] mt-1">Final pricing coming soon</div>}
                </div>
                <ul className="space-y-2 mb-6 text-sm">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2"><Check className="h-4 w-4 text-[var(--gs-teal)] mt-0.5 flex-shrink-0"/>{f}</li>
                  ))}
                </ul>
                <Button
                  onClick={() => handleCTA(p.id)}
                  disabled={busy === p.id || isCurrent || p.id === "free"}
                  className={`w-full h-12 ${p.highlight ? "bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" : p.id === "elite" ? "bg-[var(--gs-ink)] hover:bg-black text-white" : "bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`}
                  data-testid={`pricing-cta-${p.id}`}
                >
                  {busy === p.id ? <Loader2 className="h-4 w-4 animate-spin"/> :
                   isCurrent ? "Current plan" :
                   p.cta} {!isCurrent && p.id !== "free" && busy !== p.id && <ArrowRight className="h-4 w-4 ml-2"/>}
                </Button>
              </div>
            );
          })}
        </div>

        {currentPlan !== "free" && user && (
          <div className="mt-8 text-center">
            <button onClick={cancel} className="text-xs text-[var(--gs-muted)] hover:text-rose-600 underline" data-testid="pricing-cancel-link">
              Cancel my {currentPlan.toUpperCase()} subscription
            </button>
          </div>
        )}

        <p className="text-center text-xs text-[var(--gs-muted)] mt-8">Payments processed securely by Razorpay · GST invoice on request · Cancel anytime</p>
      </section>
    </div>
  );
}
