import { Crown, Sparkles, Zap } from "lucide-react";
import { Link } from "react-router-dom";

const CFG = {
  free: { label: "Free", icon: Zap, bg: "bg-[var(--gs-surface-2)]", color: "text-[var(--gs-muted)]" },
  pro: { label: "Pro", icon: Sparkles, bg: "bg-[var(--gs-teal-soft)]", color: "text-[var(--gs-teal)]" },
  elite: { label: "Elite", icon: Crown, bg: "bg-[var(--gs-champagne)]", color: "text-[var(--gs-ink)]" },
};

export function PlanBadge({ plan = "free", status, asLink = true, size = "sm" }) {
  const cfg = CFG[plan] || CFG.free;
  const Icon = cfg.icon;
  const inner = (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${cfg.bg} ${cfg.color}`} data-testid={`plan-badge-${plan}`}>
      <Icon className="h-3 w-3"/>{cfg.label}{status === "trial" ? " • Trial" : ""}
    </span>
  );
  return asLink ? <Link to="/pricing">{inner}</Link> : inner;
}
