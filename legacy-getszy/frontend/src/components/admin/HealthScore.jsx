import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function HealthScore({ score = 0, label = "Business Health" }) {
  const getColor = (s) => {
    if (s >= 80) return { bg: 'from-emerald-500 to-emerald-600', ring: 'text-emerald-600', label: 'Excellent', icon: Shield };
    if (s >= 60) return { bg: 'from-blue-500 to-blue-600', ring: 'text-blue-600', label: 'Good', icon: CheckCircle2 };
    if (s >= 40) return { bg: 'from-amber-500 to-amber-600', ring: 'text-amber-600', label: 'Needs Work', icon: AlertTriangle };
    return { bg: 'from-rose-500 to-rose-600', ring: 'text-rose-600', label: 'Critical', icon: AlertTriangle };
  };
  const c = getColor(score);
  const Icon = c.icon;
  const circumference = 2 * Math.PI * 36;
  const offset = circumference - (score / 100) * circumference;

  return (
    <Card className="p-5 flex items-center gap-5">
      <div className="relative w-20 h-20 flex-shrink-0">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="36" stroke="#e5e7eb" strokeWidth="6" fill="none"/>
          <circle cx="40" cy="40" r="36" stroke="url(#healthGrad)" strokeWidth="6" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} style={{ transition: 'stroke-dashoffset 1s ease' }}/>
          <defs>
            <linearGradient id="healthGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={score >= 60 ? '#10b981' : score >= 40 ? '#f59e0b' : '#ef4444'}/>
              <stop offset="100%" stopColor={score >= 60 ? '#059669' : score >= 40 ? '#d97706' : '#dc2626'}/>
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <span className="text-lg font-display font-bold">{score}</span>
        </div>
      </div>
      <div className="flex-1">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`text-lg font-semibold ${c.ring}`}>{c.label}</div>
        <div className="text-[11px] text-[var(--gs-muted)] mt-0.5">
          {score >= 80 ? "Everything running smoothly" : score >= 60 ? "Good foundation, room to grow" : score >= 40 ? "Some areas need attention" : "Critical issues need fixing"}
        </div>
      </div>
      <Badge className={`${c.bg} text-white border-0 text-[10px]`}>{score}/100</Badge>
    </Card>
  );
}
