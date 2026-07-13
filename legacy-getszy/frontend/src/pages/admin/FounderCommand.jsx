import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import {
  Heart, IndianRupee, Users, Zap, TrendingUp, Film, Cpu, Server,
  Database, HardDrive, RefreshCw, AlertTriangle, Activity, CheckCircle2,
  XCircle, Rocket, ArrowUpRight, Shield, Globe, Clock, BarChart3,
  CreditCard, FolderOpen, GitBranch, Layers, Sparkles, Bell
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function KpiCard({ label, value, sub, icon: Icon, color = "bg-[var(--gs-teal-soft)]", iconColor = "text-[var(--gs-teal)]", danger }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${danger ? "bg-rose-50" : color}`}>
          <Icon className={`h-4 w-4 ${danger ? "text-rose-500" : iconColor}`}/>
        </div>
      </div>
      <div className="text-2xl font-display" style={{ fontVariantNumeric: "tabular-nums" }}>{value ?? "—"}</div>
      {sub && <div className="text-[11px] text-[var(--gs-muted)]">{sub}</div>}
    </Card>
  );
}

function HealthDot({ ok }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}/>;
}

export default function FounderCommand() {
  const [health, setHealth] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [revenueChart, setRevenueChart] = useState(null);
  const [growth, setGrowth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [chartRange, setChartRange] = useState("7d");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    setError(false);
    try {
      const [h, k, r, g, a] = await Promise.all([
        api.get("/admin/founder/health-summary").catch(() => ({ data: null })),
        api.get("/admin/founder/kpi").catch(() => ({ data: null })),
        api.get(`/admin/founder/revenue-chart?range=${chartRange}`).catch(() => ({ data: null })),
        api.get("/admin/founder/growth-metrics").catch(() => ({ data: null })),
        api.get("/admin/founder/alerts").catch(() => ({ data: { items: [] } })),
      ]);
      setHealth(h.data);
      setKpi(k.data);
      setRevenueChart(r.data);
      setGrowth(g.data);
      setAlerts(a.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { setLoading(true); load(); }, [chartRange]);

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  const hp = health || {};
  const kpiData = kpi || {};
  const growthData = growth || {};

  const SERVICES = [
    { label: "MongoDB", ok: hp.mongodb_ok, detail: hp.mongodb_detail },
    { label: "Redis", ok: hp.redis_ok, detail: hp.redis_detail },
    { label: "Ollama", ok: hp.ollama_ok, detail: hp.ollama_detail },
    { label: "Backend API", ok: hp.backend_ok, detail: hp.backend_detail },
  ];

  const SYSTEM_METRICS = [
    { label: "Disk", value: hp.disk_usage, icon: HardDrive, detail: hp.disk_detail },
    { label: "CPU", value: hp.cpu_usage, icon: Cpu, detail: hp.cpu_detail },
    { label: "RAM", value: hp.ram_usage, icon: Server, detail: hp.ram_detail },
  ];

  const QUICK_ACTIONS = [
    { label: "Deploy", icon: Rocket, to: "/admin/deploy", color: "bg-orange-500" },
    { label: "Users", icon: Users, to: "/admin/users", color: "bg-blue-500" },
    { label: "Analytics", icon: BarChart3, to: "/admin/analytics", color: "bg-cyan-500" },
    { label: "Security", icon: Shield, to: "/admin/security", color: "bg-rose-500" },
    { label: "Settings", icon: Activity, to: "/admin/settings", color: "bg-violet-500" },
    { label: "Projects", icon: FolderOpen, to: "/admin/projects", color: "bg-emerald-500" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Founder Command Center</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Full system overview — health, KPIs, revenue & alerts</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      {/* System Health */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">System Health</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {SERVICES.map(s => (
            <Card key={s.label} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{s.label}</span>
                <HealthDot ok={s.ok}/>
              </div>
              <div className={`text-sm font-semibold ${s.ok ? "text-emerald-600" : "text-rose-500"}`}>
                {s.ok ? "Running" : "Down"}
              </div>
              {s.detail && <div className="text-[11px] text-[var(--gs-muted)] mt-1">{s.detail}</div>}
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3">
          {SYSTEM_METRICS.map(m => (
            <Card key={m.label} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{m.label}</span>
                <m.icon className="h-4 w-4 text-[var(--gs-teal)]"/>
              </div>
              <div className="text-xl font-display">{m.value != null ? `${m.value}%` : "—"}</div>
              {m.value != null && (
                <div className="mt-2 h-1.5 rounded-full bg-[var(--gs-surface-2)]">
                  <div className={`h-1.5 rounded-full transition-all ${m.value > 90 ? "bg-rose-500" : m.value > 70 ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${Math.min(m.value, 100)}%` }}/>
                </div>
              )}
              {m.detail && <div className="text-[11px] text-[var(--gs-muted)] mt-1">{m.detail}</div>}
            </Card>
          ))}
        </div>
      </div>

      {/* Deep KPIs */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Financial KPIs</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <KpiCard label="MRR" value={fmtINR(kpiData.mrr)} sub="Monthly Recurring" icon={TrendingUp} color="bg-emerald-50" iconColor="text-emerald-600"/>
          <KpiCard label="ARR" value={fmtINR(kpiData.arr)} sub="Annual Recurring" icon={TrendingUp} color="bg-blue-50" iconColor="text-blue-600"/>
          <KpiCard label="Revenue" value={fmtINR(kpiData.revenue)} sub="Total revenue" icon={IndianRupee}/>
          <KpiCard label="Credits" value={fmtINR(kpiData.credits_revenue)} sub="Credits purchased" icon={CreditCard} color="bg-amber-50" iconColor="text-amber-600"/>
          <KpiCard label="Failed Jobs" value={kpiData.failed_jobs} sub="Needs attention" icon={XCircle} danger/>
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">User & Platform KPIs</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <KpiCard label="Total Users" value={kpiData.total_users} sub={`${kpiData.active_users ?? "—"} active`} icon={Users} color="bg-cyan-50" iconColor="text-cyan-600"/>
          <KpiCard label="Subscribers" value={kpiData.subscribers} sub="Paid plans" icon={Zap} color="bg-violet-50" iconColor="text-violet-600"/>
          <KpiCard label="AI Jobs" value={kpiData.ai_jobs_total} sub={`${kpiData.ai_jobs_today ?? 0} today`} icon={Film} color="bg-pink-50" iconColor="text-pink-600"/>
          <KpiCard label="Projects" value={kpiData.projects} sub="Total projects" icon={FolderOpen} color="bg-indigo-50" iconColor="text-indigo-600"/>
          <KpiCard label="Deployments" value={kpiData.deployments} sub={`${kpiData.deployments_live ?? 0} live`} icon={Layers} color="bg-orange-50" iconColor="text-orange-600"/>
        </div>
      </div>

      {/* Revenue Chart + Growth Metrics */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Revenue Trend</h3>
            <Select value={chartRange} onValueChange={setChartRange}>
              <SelectTrigger className="w-24 h-7 text-[10px]"><SelectValue/></SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">7 days</SelectItem>
                <SelectItem value="30d">30 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={revenueChart?.data || []}>
              <defs><linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.5}/>
                <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
              </linearGradient></defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Area type="monotone" dataKey="revenue" stroke="#2F7E7A" fill="url(#revGrad)"/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Growth Metrics</h3>
            <TrendingUp className="h-4 w-4 text-[var(--gs-teal)]"/>
          </div>
          <div className="space-y-4">
            {[
              { label: "User Growth", data: growthData.users_trend, icon: Users },
              { label: "Revenue Growth", data: growthData.revenue_trend, icon: IndianRupee },
              { label: "Subscriber Growth", data: growthData.subscriber_trend, icon: Zap },
            ].map(m => (
              <div key={m.label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--gs-muted)] flex items-center gap-1"><m.icon className="h-3 w-3"/> {m.label}</span>
                  <span className="font-semibold">{m.data?.current ?? "—"} / {m.data?.previous ?? "—"}</span>
                </div>
                {m.data?.current != null && m.data?.previous != null && (
                  <div className="h-1.5 rounded-full bg-[var(--gs-surface-2)]">
                    <div className="h-1.5 rounded-full bg-[var(--gs-teal)]" style={{ width: `${Math.min(m.data.previous > 0 ? (m.data.current / m.data.previous) * 50 : 50, 100)}%` }}/>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Alerts */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">
          <Bell className="inline h-3 w-3 mr-1"/>Alerts ({alerts.length})
        </div>
        {alerts.length === 0 ? (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0"/>
            <span className="font-medium">Sab theek hai! Koi critical alerts nahi.</span>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${
                a.level === "critical" ? "bg-rose-50 border-rose-200 text-rose-800" :
                a.level === "warning" ? "bg-amber-50 border-amber-200 text-amber-800" :
                "bg-blue-50 border-blue-200 text-blue-800"
              }`}>
                {a.level === "critical" ? <XCircle className="h-4 w-4 flex-shrink-0"/> :
                 a.level === "warning" ? <AlertTriangle className="h-4 w-4 flex-shrink-0"/> :
                 <Activity className="h-4 w-4 flex-shrink-0"/>}
                <span className="flex-1 text-sm">{a.message || a.msg}</span>
                <Badge variant="outline" className="text-[10px] capitalize">{a.level}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Quick Actions</div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {QUICK_ACTIONS.map(a => (
            <a key={a.to} href={a.to}
              className="flex flex-col items-center gap-2 p-3 rounded-xl border bg-white hover:shadow-md transition-all text-center group">
              <div className={`h-9 w-9 rounded-xl ${a.color} grid place-items-center`}>
                <a.icon className="h-4 w-4 text-white"/>
              </div>
              <span className="text-[10px] font-semibold text-[var(--gs-ink)] leading-tight">{a.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
