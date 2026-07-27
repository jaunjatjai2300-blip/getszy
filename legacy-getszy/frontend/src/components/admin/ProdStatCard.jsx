import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function ProdStatCard({ label, value, sub, icon: Icon, trend, trendLabel, color = "bg-[var(--gs-teal-soft)]", iconColor = "text-[var(--gs-teal)]", danger, pulse, onClick }) {
  const trendNum = typeof trend === 'number' ? trend : null;
  const isUp = trendNum && trendNum > 0;
  const isDown = trendNum && trendNum < 0;
  const TrendIcon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;
  const trendColor = isUp ? 'text-emerald-600 bg-emerald-50' : isDown ? 'text-rose-500 bg-rose-50' : 'text-[var(--gs-muted)] bg-gray-50';

  return (
    <Card className={`p-4 space-y-2 transition-all hover:shadow-md ${onClick ? 'cursor-pointer' : ''}`} onClick={onClick}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${danger ? "bg-rose-50" : color} ${pulse ? 'animate-pulse' : ''}`}>
          <Icon className={`h-4 w-4 ${danger ? "text-rose-500" : iconColor}`}/>
        </div>
      </div>
      <div className="flex items-end gap-2">
        <div className="text-2xl font-display tabular-nums">{value ?? "—"}</div>
        {trendNum !== null && (
          <Badge className={`text-[10px] px-1.5 py-0 ${trendColor} border-0 mb-1`}>
            <TrendIcon className="h-2.5 w-2.5 mr-0.5"/>
            {isUp ? '+' : ''}{trendNum}%
          </Badge>
        )}
      </div>
      {sub && <div className="text-[11px] text-[var(--gs-muted)]">{sub}</div>}
      {trendLabel && <div className="text-[10px] text-[var(--gs-muted)]">{trendLabel}</div>}
    </Card>
  );
}
