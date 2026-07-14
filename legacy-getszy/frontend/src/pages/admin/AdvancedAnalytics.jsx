import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import {
  TrendingUp, Users, DollarSign, ArrowUpDown, RefreshCw, Download,
  AlertTriangle, CheckCircle2, BarChart3, PieChart as PieIcon,
  Filter, Target, Activity, Zap, ArrowUpRight, ArrowDownRight,
  Calendar, Layers, Brain
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function KpiCard({ label, value, sub, icon: Icon, color = "bg-[var(--gs-teal-soft)]", iconColor = "text-[var(--gs-teal)]", trend, trendUp }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${color}`}>
          <Icon className={`h-4 w-4 ${iconColor}`}/>
        </div>
      </div>
      <div className="text-2xl font-display" style={{ fontVariantNumeric: "tabular-nums" }}>{value ?? "—"}</div>
      <div className="flex items-center gap-1.5">
        {sub && <div className="text-[11px] text-[var(--gs-muted)]">{sub}</div>}
        {trend && (
          <div className={`flex items-center gap-0.5 text-[10px] font-semibold ${trendUp ? "text-emerald-600" : "text-rose-500"}`}>
            {trendUp ? <ArrowUpRight className="h-3 w-3"/> : <ArrowDownRight className="h-3 w-3"/>}
            {trend}
          </div>
        )}
      </div>
    </Card>
  );
}

function getRetentionColor(pct) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 60) return "bg-emerald-400";
  if (pct >= 40) return "bg-amber-400";
  if (pct >= 20) return "bg-orange-400";
  return "bg-rose-400";
}

const PIE_COLORS = ["#2F7E7A", "#A86B5B", "#6366F1", "#F59E0B", "#EC4899"];

/* ========== FUNNELS TAB ========== */
function FunnelsTab() {
  const [funnels, setFunnels] = useState([]);
  const [selectedFunnel, setSelectedFunnel] = useState(null);

  useEffect(() => {
    api.get("/admin/analytics-advanced/funnels").catch(() => ({ data: { items: [] } }))
      .then(r => setFunnels(r.data?.items || []));
  }, []);

  const loadFunnel = async (id) => {
    try {
      const r = await api.get(`/admin/analytics-advanced/funnels/${id}`);
      setSelectedFunnel(r.data);
    } catch { /* silent */ }
  };

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {funnels.map((f, i) => (
          <Card key={f.id || i} className={`p-5 cursor-pointer hover:shadow-md transition-all ${selectedFunnel?.id === f.id ? "ring-2 ring-[var(--gs-teal)]" : ""}`}
            onClick={() => loadFunnel(f.id)}>
            <h3 className="font-semibold text-sm">{f.name}</h3>
            <div className="text-xs text-[var(--gs-muted)] mt-0.5">{f.steps?.length ?? 0} steps</div>
            <div className="text-xs font-semibold text-[var(--gs-teal)] mt-2">{f.conversion_rate ?? 0}% conversion</div>
          </Card>
        ))}
      </div>

      {selectedFunnel && (
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-4">{selectedFunnel.name} — Funnel Visualization</h3>
          <div className="flex flex-col items-center gap-1">
            {(selectedFunnel.steps || []).map((step, i) => {
              const widthPct = step.percentage || 100 - (i * 15);
              const nextStep = (selectedFunnel.steps || [])[i + 1];
              return (
                <div key={i} className="w-full flex flex-col items-center">
                  <div className="relative w-full flex justify-center">
                    <div
                      className="rounded-lg py-3 px-6 text-center text-sm font-semibold text-white transition-all"
                      style={{
                        width: `${Math.max(widthPct, 20)}%`,
                        backgroundColor: `hsl(${170 + i * 20}, 60%, ${45 - i * 3}%)`,
                      }}>
                      <div>{step.name}</div>
                      <div className="text-[10px] opacity-80">{step.count?.toLocaleString()} ({widthPct.toFixed(1)}%)</div>
                    </div>
                  </div>
                  {nextStep && (
                    <div className="text-[10px] text-[var(--gs-muted)] py-0.5">
                      ↓ {step.dropoff_rate ? `${step.dropoff_rate}% drop-off` : ""}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ========== RETENTION TAB ========== */
function RetentionTab() {
  const [cohorts, setCohorts] = useState([]);
  const [weeks, setWeeks] = useState([]);

  useEffect(() => {
    api.get("/admin/analytics-advanced/retention").catch(() => ({ data: { cohorts: [], weeks: [] } }))
      .then(r => {
        setCohorts(r.data?.cohorts || []);
        setWeeks(r.data?.weeks || []);
      });
  }, []);

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Cohort Retention Heatmap</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-2 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-left">Cohort</th>
                <th className="p-2 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-left">Users</th>
                {weeks.map((w, i) => (
                  <th key={i} className="p-2 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-center">W{i}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {cohorts.map((cohort, ci) => (
                <tr key={ci} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-2 text-xs font-semibold whitespace-nowrap">{cohort.label}</td>
                  <td className="p-2 text-xs text-[var(--gs-muted)]">{cohort.total_users}</td>
                  {(cohort.retention || []).map((pct, wi) => (
                    <td key={wi} className="p-1 text-center">
                      <div className={`rounded-md py-1.5 px-2 text-[10px] font-semibold text-white ${getRetentionColor(pct)}`}>
                        {pct}%
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
              {cohorts.length === 0 && (
                <tr><td colSpan={weeks.length + 2} className="p-6 text-center text-[var(--gs-muted)] text-sm">No cohort data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========== CHURN TAB ========== */
function ChurnTab({ churnData }) {
  const planChurn = churnData?.by_plan || [];
  const dormant = churnData?.dormant_users || [];

  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">Churn Rate by Plan</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={planChurn}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="plan" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Bar dataKey="churn_rate" fill="#EF4444" radius={[4, 4, 0, 0]} name="Churn %"/>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">Key Metrics</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
              <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Overall Churn</div>
              <div className="text-xl font-display">{churnData?.overall_churn ?? "—"}%</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
              <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Dormant Users</div>
              <div className="text-xl font-display">{dormant.length}</div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Dormant Users</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">User</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Email</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Last Active</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Plan</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {dormant.map((u, i) => (
                <tr key={u.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{u.name}</td>
                  <td className="p-3 text-[var(--gs-muted)] text-xs">{u.email}</td>
                  <td className="p-3 text-xs">{u.last_active ? new Date(u.last_active).toLocaleDateString("en-IN") : "—"}</td>
                  <td className="p-3"><Badge variant="outline" className="text-[10px]">{u.plan || "free"}</Badge></td>
                </tr>
              ))}
              {dormant.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No dormant users</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========== REVENUE TAB ========== */
function RevenueTab({ revenueData }) {
  const mrrTrend = revenueData?.mrr_trend || [];
  const byProduct = revenueData?.by_product || [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="MRR" value={fmtINR(revenueData?.mrr)} sub="Monthly Recurring" icon={TrendingUp} trend={revenueData?.mrr_trend_pct} trendUp={revenueData?.mrr_trend_up}/>
        <KpiCard label="ARR" value={fmtINR(revenueData?.arr)} sub="Annual Recurring" icon={TrendingUp} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="LTV" value={fmtINR(revenueData?.ltv)} sub="Avg Lifetime Value" icon={DollarSign} color="bg-violet-50" iconColor="text-violet-600"/>
        <KpiCard label="ARPU" value={fmtINR(revenueData?.arpu)} sub="Avg Revenue Per User" icon={Target} color="bg-emerald-50" iconColor="text-emerald-600"/>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">MRR / ARR Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={mrrTrend}>
              <defs>
                <linearGradient id="mrrGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.5}/>
                  <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="month" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Area type="monotone" dataKey="mrr" stroke="#2F7E7A" fill="url(#mrrGrad)" name="MRR"/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">Revenue by Product</h3>
          {byProduct.length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width={150} height={150}>
                <PieChart>
                  <Pie data={byProduct} dataKey="revenue" nameKey="name" cx="50%" cy="50%" outerRadius={60}>
                    {byProduct.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]}/>)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {byProduct.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}/>
                    <span className="font-semibold">{p.name}</span>
                    <span className="text-[var(--gs-muted)]">{fmtINR(p.revenue)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-[var(--gs-muted)] text-sm">No product revenue data</div>
          )}
        </Card>
      </div>
    </div>
  );
}

/* ========== USERS TAB ========== */
function UsersTab({ userData }) {
  const dauWauMau = userData?.dau_wau_mau || [];
  const signupTrend = userData?.signup_trend || [];
  const sessions = userData?.sessions || {};

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <KpiCard label="DAU" value={sessions.dau ?? "—"} sub="Daily Active" icon={Activity}/>
        <KpiCard label="WAU" value={sessions.wau ?? "—"} sub="Weekly Active" icon={Users} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="MAU" value={sessions.mau ?? "—"} sub="Monthly Active" icon={Users} color="bg-violet-50" iconColor="text-violet-600"/>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">DAU / WAU / MAU Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dauWauMau}>
              <defs>
                <linearGradient id="dauGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.5}/>
                  <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Area type="monotone" dataKey="dau" stroke="#2F7E7A" fill="url(#dauGrad)" name="DAU"/>
              <Area type="monotone" dataKey="wau" stroke="#6366F1" fill="transparent" name="WAU"/>
              <Area type="monotone" dataKey="mau" stroke="#F59E0B" fill="transparent" name="MAU"/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3">Signup Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={signupTrend}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Bar dataKey="signups" fill="#2F7E7A" radius={[4, 4, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3">Session Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Avg Session</div>
            <div className="text-lg font-display">{sessions.avg_duration ?? "—"}</div>
          </div>
          <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Pages / Session</div>
            <div className="text-lg font-display">{sessions.pages_per_session ?? "—"}</div>
          </div>
          <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Bounce Rate</div>
            <div className="text-lg font-display">{sessions.bounce_rate ?? "—"}%</div>
          </div>
          <div className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase font-semibold">Retention D7</div>
            <div className="text-lg font-display">{sessions.retention_d7 ?? "—"}%</div>
          </div>
        </div>
      </Card>
    </div>
  );
}

/* ========== SEGMENTS TAB ========== */
function SegmentsTab({ segmentsData }) {
  const segments = segmentsData?.segments || [];

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {segments.map((seg, i) => (
          <Card key={i} className="p-4">
            <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-1">{seg.name}</div>
            <div className="text-2xl font-display">{seg.count?.toLocaleString()}</div>
            <div className="text-[11px] text-[var(--gs-muted)] mt-1">{seg.percentage ?? 0}% of total</div>
            <div className="mt-2 space-y-0.5">
              {(seg.sample_users || []).slice(0, 3).map((u, ui) => (
                <div key={ui} className="text-[10px] text-[var(--gs-muted)] truncate">{u.name || u.email}</div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PREDICTIONS TAB ========== */
function PredictionsTab({ predictions }) {
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-3 gap-3">
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain className="h-4 w-4 text-[var(--gs-teal)]"/>
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Projected MRR (Next Month)</span>
          </div>
          <div className="text-3xl font-display text-[var(--gs-teal)]">{fmtINR(predictions?.projected_mrr)}</div>
          {predictions?.mrr_confidence && (
            <div className="text-xs text-[var(--gs-muted)] mt-1">Confidence: {predictions.mrr_confidence}%</div>
          )}
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-rose-500"/>
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Projected Churn</span>
          </div>
          <div className="text-3xl font-display text-rose-500">{predictions?.projected_churn ?? "—"}%</div>
          {predictions?.churn_confidence && (
            <div className="text-xs text-[var(--gs-muted)] mt-1">Confidence: {predictions.churn_confidence}%</div>
          )}
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Users className="h-4 w-4 text-blue-600"/>
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Projected Signups (Next Month)</span>
          </div>
          <div className="text-3xl font-display text-blue-600">{predictions?.projected_signups?.toLocaleString() ?? "—"}</div>
          {predictions?.signups_confidence && (
            <div className="text-xs text-[var(--gs-muted)] mt-1">Confidence: {predictions.signups_confidence}%</div>
          )}
        </Card>
      </div>
    </div>
  );
}

/* ========== MAIN ========== */
export default function AdvancedAnalytics() {
  const [tab, setTab] = useState("funnels");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [churnData, setChurnData] = useState(null);
  const [revenueData, setRevenueData] = useState(null);
  const [userData, setUserData] = useState(null);
  const [segmentsData, setSegmentsData] = useState(null);
  const [predictions, setPredictions] = useState(null);

  const load = async () => {
    setError(false);
    try {
      const [c, r, u, s, p] = await Promise.all([
        api.get("/admin/analytics-advanced/churn").catch(() => ({ data: {} })),
        api.get("/admin/analytics-advanced/revenue").catch(() => ({ data: {} })),
        api.get("/admin/analytics-advanced/users").catch(() => ({ data: {} })),
        api.get("/admin/analytics-advanced/segments").catch(() => ({ data: {} })),
        api.get("/admin/analytics-advanced/predictions").catch(() => ({ data: {} })),
      ]);
      setChurnData(c.data);
      setRevenueData(r.data);
      setUserData(u.data);
      setSegmentsData(s.data);
      setPredictions(p.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const exportCSV = async () => {
    try {
      const r = await api.get("/admin/analytics-advanced/export", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `analytics-export-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* silent */ }
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Advanced Analytics</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Funnels, retention, churn, revenue & predictions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8" onClick={load}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
          <Button variant="outline" size="sm" className="h-8" onClick={exportCSV}>
            <Download className="h-3.5 w-3.5 mr-1"/>Export CSV
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="funnels">Funnels</TabsTrigger>
          <TabsTrigger value="retention">Retention</TabsTrigger>
          <TabsTrigger value="churn">Churn</TabsTrigger>
          <TabsTrigger value="revenue">Revenue</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="segments">Segments</TabsTrigger>
          <TabsTrigger value="predictions">Predictions</TabsTrigger>
        </TabsList>

        <TabsContent value="funnels" className="mt-4"><FunnelsTab/></TabsContent>
        <TabsContent value="retention" className="mt-4"><RetentionTab/></TabsContent>
        <TabsContent value="churn" className="mt-4"><ChurnTab churnData={churnData}/></TabsContent>
        <TabsContent value="revenue" className="mt-4"><RevenueTab revenueData={revenueData}/></TabsContent>
        <TabsContent value="users" className="mt-4"><UsersTab userData={userData}/></TabsContent>
        <TabsContent value="segments" className="mt-4"><SegmentsTab segmentsData={segmentsData}/></TabsContent>
        <TabsContent value="predictions" className="mt-4"><PredictionsTab predictions={predictions}/></TabsContent>
      </Tabs>
    </div>
  );
}
