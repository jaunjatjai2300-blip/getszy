import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Activity, RefreshCw, TrendingUp, AlertTriangle, Gauge } from "lucide-react";
import { toast } from "sonner";

export default function Observability() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/observability/summary");
      setData(data);
    } catch (e) {
      toast.error("Failed to load observability");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sla = data?.sla;
  const health = sla ? (sla.uptime_pct >= 99 ? "Healthy" : sla.uptime_pct >= 95 ? "Degraded" : "Critical") : "—";
  const healthColor = health === "Healthy" ? "text-emerald-600" : health === "Degraded" ? "text-amber-600" : "text-rose-600";

  return (
    <div className="space-y-6" data-testid="admin-observability-page">
      <div className="flex items-center gap-2">
        <Activity className="h-6 w-6 text-[var(--gs-teal)]" />
        <h1 className="text-2xl font-semibold">Observability & SLA</h1>
        <Button size="sm" variant="outline" className="ml-auto" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /></Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-[var(--gs-muted)] text-xs"><Gauge className="h-4 w-4" />Health</div>
          <div className={`text-2xl font-bold mt-1 ${healthColor}`}>{health}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-[var(--gs-muted)] text-xs"><TrendingUp className="h-4 w-4" />Uptime (24h)</div>
          <div className="text-2xl font-bold mt-1">{sla ? `${sla.uptime_pct}%` : "—"}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-[var(--gs-muted)] text-xs"><AlertTriangle className="h-4 w-4" />Error rate</div>
          <div className="text-2xl font-bold mt-1">{sla ? `${sla.error_rate}%` : "—"}</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-[var(--gs-muted)] text-xs"><Activity className="h-4 w-4" />p95 latency</div>
          <div className="text-2xl font-bold mt-1">{sla ? `${sla.p95_ms}ms` : "—"}</div>
        </Card>
      </div>

      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3">Platform counts</h3>
        {!data ? (
          <div className="text-xs text-[var(--gs-muted)]">Loading…</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
            {Object.entries(data.counts || {}).map(([k, v]) => (
              <div key={k} className="rounded-lg bg-[var(--gs-surface-2)] p-3">
                <div className="text-lg font-bold">{v}</div>
                <div className="text-[10px] text-[var(--gs-muted)] capitalize">{k}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
