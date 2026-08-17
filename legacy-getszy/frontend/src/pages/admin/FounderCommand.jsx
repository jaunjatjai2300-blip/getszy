import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import { Link } from "react-router-dom";
import {
  Heart, IndianRupee, Users, Zap, TrendingUp, Film, Cpu, Server,
  Database, HardDrive, RefreshCw, AlertTriangle, Activity, CheckCircle2,
  XCircle, Rocket, ArrowUpRight, Shield, Globe, Clock, BarChart3,
  CreditCard, FolderOpen, GitBranch, Layers, Sparkle, Bell, Command,
  Brain, ShoppingCart, UserPlus, Target, Flame, Eye, Gauge, Timer,
  TrendingDown, ArrowRight, Download, Calendar, DollarSign, BoxesIcon,
  PieChart as PieChartIcon
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, RadarChart,
  PolarGrid, PolarAngleAxis, Radar
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ProdStatCard from "@/components/admin/ProdStatCard";
import HealthScore from "@/components/admin/HealthScore";
import SectionHeader from "@/components/admin/SectionHeader";
import { StatusBadge, InlineStat } from "@/components/admin/StatusBadge";
import LiveFeed from "@/components/admin/LiveFeed";

const PIE_COLORS = ['#2F7E7A', '#A86B5B', '#6366f1', '#f59e0b', '#ec4899', '#10b981'];

export default function FounderCommand() {
  const [health, setHealth] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [revenueChart, setRevenueChart] = useState(null);
  const [growth, setGrowth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [chartRange, setChartRange] = useState("7d");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [askQ, setAskQ] = useState("");
  const [askA, setAskA] = useState("");
  const [askLoading, setAskLoading] = useState(false);

  const load = useCallback(async () => {
    setError(false);
    try {
      const [h, k, r, g, a, an] = await Promise.all([
        api.get("/admin/founder/health-summary").catch(() => ({ data: null })),
        api.get("/admin/founder/kpi").catch(() => ({ data: null })),
        api.get(`/admin/founder/revenue-chart?range=${chartRange}`).catch(() => ({ data: null })),
        api.get("/admin/founder/growth-metrics").catch(() => ({ data: null })),
        api.get("/admin/founder/alerts").catch(() => ({ data: { items: [] } })),
        api.get("/admin/analytics-advanced/revenue-analytics").catch(() => ({ data: null })),
      ]);
      setHealth(h.data);
      setKpi(k.data);
      setRevenueChart(r.data);
      setGrowth(g.data);
      setAlerts(a.data?.items || []);
      setAnalytics(an.data);
      setLastRefresh(new Date());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [chartRange]);

  useEffect(() => { setLoading(true); load(); }, [load]);

  const askNeo = useCallback(async () => {
    const q = askQ.trim();
    if (!q) return;
    setAskLoading(true);
    try {
      const { data } = await api.post("/admin/founder/ask", { question: q }).catch(() => ({ data: { answer: "Neo is unavailable right now." } }));
      setAskA(data?.answer || "No response.");
    } catch (e) {
      setAskA("Neo is unavailable right now.");
    } finally {
      setAskLoading(false);
    }
  }, [askQ]);
  useEffect(() => {
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  if (error) return (
    <div className="p-10 text-center space-y-3">
      <XCircle className="h-10 w-10 text-rose-400 mx-auto"/>
      <div className="text-[var(--gs-muted)]">Command Center data load nahi ho saka.</div>
      <Button onClick={load} variant="outline" size="sm"><RefreshCw className="h-3.5 w-3.5 mr-1"/>Retry</Button>
    </div>
  );

  const hp = health || {};
  const kpiData = kpi || {};
  const growthData = growth || {};
  const revData = revenueChart || {};
  const anData = analytics || {};

  const revenuePie = [
    { name: 'MRR', value: kpiData.mrr || 0 },
    { name: 'One-time', value: (anData.total_revenue || 0) - (kpiData.mrr || 0) * 12 || 0 },
  ].filter(x => x.value > 0);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionHeader title="Command Center" subtitle="Deep analytics, health monitoring & business intelligence" icon={Command} loading={loading} onRefresh={load}>
          <Select value={chartRange} onValueChange={setChartRange}>
            <SelectTrigger className="w-24 h-8 text-xs"><SelectValue/></SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
              <SelectItem value="90d">90 Days</SelectItem>
            </SelectContent>
          </Select>
        </SectionHeader>
        <div className="flex items-center gap-2">
          {lastRefresh && (
            <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1">
              <Clock className="h-3 w-3"/>Live {lastRefresh.toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit'})}
            </span>
          )}
        </div>
      </div>

      {/* Health Score + Services Row */}
      <div className="grid lg:grid-cols-4 gap-3">
        <HealthScore score={Math.round((hp.mongodb_ok ? 25 : 0) + (hp.redis_ok ? 25 : 0) + (hp.ollama_ok ? 25 : 0) + (hp.backend_ok ? 25 : 0))} label="System Health"/>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Services</div>
          {[
            { label: 'MongoDB', ok: hp.mongodb_ok, detail: hp.mongodb_detail },
            { label: 'Redis', ok: hp.redis_ok, detail: hp.redis_detail },
            { label: 'Ollama', ok: hp.ollama_ok, detail: hp.ollama_detail },
            { label: 'Backend API', ok: hp.backend_ok, detail: hp.backend_detail },
          ].map(s => (
            <div key={s.label} className="flex items-center justify-between text-xs">
              <span className="text-[var(--gs-muted)]">{s.label}</span>
              <div className="flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${s.ok ? 'bg-emerald-500' : 'bg-rose-400'}`}/>
                <span className={s.ok ? 'text-emerald-600' : 'text-rose-500'}>{s.ok ? 'OK' : 'Down'}</span>
              </div>
            </div>
          ))}
        </Card>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">System Resources</div>
          {[
            { label: 'Disk', value: hp.disk_usage, detail: hp.disk_detail, icon: HardDrive },
            { label: 'CPU', value: hp.cpu_usage, detail: hp.cpu_detail, icon: Cpu },
            { label: 'RAM', value: hp.ram_usage, detail: hp.ram_detail, icon: Server },
          ].map(r => (
            <div key={r.label} className="flex items-center justify-between text-xs">
              <span className="text-[var(--gs-muted)] flex items-center gap-1"><r.icon className="h-3 w-3"/>{r.label}</span>
              <div className="text-right">
                <span className="font-semibold">{r.value || '—'}</span>
                {r.detail && r.detail !== '—' && <span className="text-[var(--gs-muted)] ml-1 text-[10px]">{r.detail}</span>}
              </div>
            </div>
          ))}
        </Card>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Revenue Summary</div>
          <div className="space-y-2">
            <div className="flex justify-between"><span className="text-xs text-[var(--gs-muted)]">MRR</span><span className="text-sm font-semibold">{fmtINR(kpiData.mrr)}</span></div>
            <div className="flex justify-between"><span className="text-xs text-[var(--gs-muted)]">ARR</span><span className="text-sm font-semibold">{fmtINR(kpiData.arr)}</span></div>
            <div className="flex justify-between"><span className="text-xs text-[var(--gs-muted)]">Today</span><span className="text-sm font-semibold">{fmtINR(kpiData.revenue_today)}</span></div>
            <div className="flex justify-between"><span className="text-xs text-[var(--gs-muted)]">Total</span><span className="text-sm font-semibold">{fmtINR(kpiData.total_revenue)}</span></div>
          </div>
        </Card>
      </div>

      {/* KPI Cards */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Performance Metrics</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <ProdStatCard label="Active Users" value={kpiData.active_users} sub={`${kpiData.total_users} total`} icon={Users} color="bg-cyan-50" iconColor="text-cyan-600" trend={growthData?.users_trend?.current ? Math.round((growthData.users_trend.current - growthData.users_trend.previous) / Math.max(growthData.users_trend.previous, 1) * 100) : null}/>
          <ProdStatCard label="Subscribers" value={kpiData.active_subscribers} sub="Paid plans" icon={CreditCard} color="bg-amber-50" iconColor="text-amber-600"/>
          <ProdStatCard label="Orders Today" value={kpiData.orders_today} sub={`${kpiData.total_orders || 0} total`} icon={ShoppingCart} color="bg-emerald-50" iconColor="text-emerald-600"/>
          <ProdStatCard label="Revenue Today" value={fmtINR(kpiData.revenue_today)} sub="Total collection" icon={IndianRupee} trend={growthData?.revenue_trend?.current ? Math.round((growthData.revenue_trend.current - growthData.revenue_trend.previous) / Math.max(growthData.revenue_trend.previous, 1) * 100) : null}/>
          <ProdStatCard label="AI Jobs Today" value={kpiData.ai_jobs_today} sub={`${kpiData.ai_jobs_total || 0} total`} icon={Brain} color="bg-pink-50" iconColor="text-pink-600"/>
          <ProdStatCard label="Credits Used" value={kpiData.credits_used_today} sub="Today" icon={Zap} color="bg-violet-50" iconColor="text-violet-600"/>
        </div>
      </div>

      {/* Revenue Charts */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <IndianRupee className="h-4 w-4 text-[var(--gs-teal)]"/>Revenue Trend
            </h3>
            <Badge className="bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] text-[10px] border-0">{chartRange}</Badge>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={revData.data || []}>
              <defs>
                <linearGradient id="revGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }} formatter={(v) => [`₹${v}`, 'Revenue']}/>
              <Area type="monotone" dataKey="revenue" stroke="#2F7E7A" fill="url(#revGrad2)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-[var(--gs-teal)]"/>Orders Trend
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={revData.data || []}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Bar dataKey="orders" fill="#6366f1" radius={[4, 4, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Growth Metrics Charts */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-[var(--gs-teal)]"/>User Growth
            </h3>
            {growthData?.users_trend && (
              <TrendBadge current={growthData.users_trend.current} previous={growthData.users_trend.previous}/>
            )}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={growthData?.user_growth || []}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false} interval={Math.max(Math.floor((growthData?.user_growth || []).length / 6), 1)}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Line type="monotone" dataKey="count" stroke="#A86B5B" strokeWidth={2} dot={false}/>
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <IndianRupee className="h-4 w-4 text-[var(--gs-teal)]"/>Revenue Growth
            </h3>
            {growthData?.revenue_trend && (
              <TrendBadge current={growthData.revenue_trend.current} previous={growthData.revenue_trend.previous} prefix="₹"/>
            )}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={growthData?.revenue_growth || []}>
              <defs>
                <linearGradient id="revGrowGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false} interval={Math.max(Math.floor((growthData?.revenue_growth || []).length / 6), 1)}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }} formatter={(v) => [`₹${v}`, 'Revenue']}/>
              <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="url(#revGrowGrad)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Subscription Growth + Revenue Breakdown */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-[var(--gs-teal)]"/>Subscription Growth
            </h3>
            {growthData?.subscriber_trend && (
              <TrendBadge current={growthData.subscriber_trend.current} previous={growthData.subscriber_trend.previous}/>
            )}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={growthData?.subscriber_growth || []}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false} interval={Math.max(Math.floor((growthData?.subscriber_growth || []).length / 6), 1)}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Line type="monotone" dataKey="count" stroke="#f59e0b" strokeWidth={2} dot={false}/>
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <PieChartIcon className="h-4 w-4 text-[var(--gs-teal)]"/>Revenue Breakdown
            </h3>
          </div>
          {revenuePie.length > 0 ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={180}>
                <PieChart>
                  <Pie data={revenuePie} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={3} dataKey="value">
                    {revenuePie.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]}/>)}
                  </Pie>
                  <Tooltip formatter={(v) => [fmtINR(v)]}/>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 flex-1">
                {revenuePie.map((item, i) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded" style={{ backgroundColor: PIE_COLORS[i] }}/>
                    <span className="text-xs text-[var(--gs-muted)]">{item.name}</span>
                    <span className="text-xs font-semibold ml-auto">{fmtINR(item.value)}</span>
                  </div>
                ))}
                <div className="pt-1 border-t" style={{ borderColor: "var(--gs-border)" }}>
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--gs-muted)]">LTV</span>
                    <span className="font-semibold">{fmtINR(anData.ltv)}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--gs-muted)]">ARPU</span>
                    <span className="font-semibold">{fmtINR(anData.arpu)}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-[var(--gs-muted)] py-8 text-xs">No revenue data yet</div>
          )}
        </Card>
      </div>

      {/* Alerts */}
      {(Array.isArray(alerts) ? alerts : []).length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold px-1">
            Alerts ({(Array.isArray(alerts) ? alerts : []).length})
          </div>
          {(Array.isArray(alerts) ? alerts : []).slice(0, 5).map((a, i) => {
            const styles = { warn: 'bg-amber-50 border-amber-200 text-amber-800', error: 'bg-rose-50 border-rose-200 text-rose-800', info: 'bg-blue-50 border-blue-200 text-blue-800' };
            const icons = { warn: AlertTriangle, error: XCircle, info: Activity };
            const level = a.level || a.severity || 'info';
            const Icon = icons[level] || AlertTriangle;
            return (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${styles[level] || styles.info}`}>
                <Icon className="h-4 w-4 flex-shrink-0"/>
                <span className="flex-1 text-sm">{a.msg || a.message}</span>
                {a.action && <Link to={a.to || '/admin/settings'} className="text-xs font-semibold underline">{a.action}</Link>}
              </div>
            );
          })}
        </div>
      )}

      {/* Quick Access Grid */}
      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <Rocket className="h-4 w-4 text-[var(--gs-teal)]"/>Quick Access
        </h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {[
            { label: "Analytics", icon: BarChart3, to: "/admin/analytics", color: "bg-cyan-500" },
            { label: "Products", icon: BoxesIcon, to: "/admin/products", color: "bg-blue-500" },
            { label: "Orders", icon: ShoppingCart, to: "/admin/orders", color: "bg-emerald-500" },
            { label: "Users", icon: Users, to: "/admin/users", color: "bg-indigo-500" },
            { label: "Security", icon: Shield, to: "/admin/security", color: "bg-rose-500" },
            { label: "Settings", icon: Cpu, to: "/admin/settings", color: "bg-gray-600" },
          ].map(a => (
            <Link key={a.to} to={a.to} className="flex flex-col items-center gap-1.5 p-3 rounded-xl border bg-white hover:shadow-md transition-all text-center" style={{ borderColor: "var(--gs-border)" }}>
              <div className={`h-8 w-8 rounded-lg ${a.color} grid place-items-center`}>
                <a.icon className="h-4 w-4 text-white"/>
              </div>
              <span className="text-[10px] font-semibold">{a.label}</span>
            </Link>
          ))}
        </div>
      </Card>

      {/* Ask Neo — natural-language founder query (Tier 1 #6) */}
      <Card className="p-5">
        <SectionHeader title="Ask Neo" subtitle="Puchho apne business ke baare mein — live metrics ke saath." />
        <div className="flex gap-2 mt-3">
          <Input
            value={askQ}
            onChange={(e) => setAskQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') askNeo(); }}
            placeholder="e.g. Aaj refund kitne hue? / Why is conversion down?"
            className="flex-1"
          />
          <Button onClick={askNeo} disabled={askLoading}>
            {askLoading ? "Soch raha hoon..." : "Ask Neo"}
          </Button>
        </div>
        {askA && (
          <div className="mt-3 p-3 rounded-lg bg-[var(--gs-surface)] text-sm whitespace-pre-wrap">
            {askA}
          </div>
        )}
      </Card>

      {/* Live Ops Feed — real-time events over WebSocket (Tier 2 #10) */}
      <LiveFeed />
    </div>
  );
}

function TrendBadge({ current, previous, prefix = "" }) {
  if (!current || !previous) return null;
  const pct = Math.round((current - previous) / Math.max(previous, 1) * 100);
  const isUp = pct >= 0;
  return (
    <Badge className={`text-[10px] px-1.5 py-0 border-0 ${isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-500'}`}>
      {isUp ? <TrendingUp className="h-2.5 w-2.5 mr-0.5"/> : <TrendingDown className="h-2.5 w-2.5 mr-0.5"/>}
      {isUp ? '+' : ''}{pct}%
    </Badge>
  );
}
