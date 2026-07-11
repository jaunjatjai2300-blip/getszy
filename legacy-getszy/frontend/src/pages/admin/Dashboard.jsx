import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import { Link } from "react-router-dom";
import {
  IndianRupee, Users, Film, Zap, TrendingUp, ShoppingBag,
  AlertTriangle, Activity, CheckCircle2, XCircle, Rocket,
  ArrowUpRight, RefreshCw, Sparkles, Cpu, Server, Wand2,
  Image, PenTool, Package, BarChart3, Radio
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const QUICK_ACTIONS = [
  { label: "Generate Video",   icon: Film,     to: "/admin/video",    color: "bg-violet-500" },
  { label: "New Product",      icon: Package,  to: "/admin/products", color: "bg-blue-500" },
  { label: "Creator OS",       icon: PenTool,  to: "/admin/creator",  color: "bg-emerald-500" },
  { label: "Avatar Studio",    icon: Image,    to: "/admin/avatar",   color: "bg-pink-500" },
  { label: "Deploy",           icon: Rocket,   to: "/admin/deploy",   color: "bg-orange-500" },
  { label: "Analytics",        icon: BarChart3,to: "/admin/analytics",color: "bg-cyan-500" },
];

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

export default function AdminDashboard() {
  const [range, setRange] = useState("month");
  const [stats, setStats] = useState(null);
  const [founder, setFounder] = useState(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setError(false);
    try {
      const [s, f] = await Promise.all([
        api.get(`/admin/stats?range=${range}`),
        api.get("/admin/founder-stats").catch(() => ({ data: null })),
      ]);
      setStats(s.data);
      setFounder(f.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { setLoading(true); load(); }, [range]);

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Stats load nahi ho sakin. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  const f = founder || {};
  const s = stats || {};

  return (
    <div className="space-y-6" data-testid="admin-dashboard-page">

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Founder Dashboard</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Getszy AI Business OS — Command Center</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={range} onValueChange={setRange}>
            <SelectTrigger className="w-36 h-8 text-xs"><SelectValue/></SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This week</SelectItem>
              <SelectItem value="month">This month</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" className="h-8" onClick={load}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
        </div>
      </div>

      {/* Row 1 — Revenue KPIs */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">💰 Revenue</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Revenue" value={fmtINR(s.revenue)} sub={`Profit: ${fmtINR(s.profit)}`} icon={IndianRupee}/>
          <KpiCard label="MRR" value={fmtINR(f.mrr)} sub="Monthly Recurring" icon={TrendingUp} color="bg-emerald-50" iconColor="text-emerald-600"/>
          <KpiCard label="ARR" value={fmtINR(f.arr)} sub="Annual Recurring" icon={TrendingUp} color="bg-blue-50" iconColor="text-blue-600"/>
          <KpiCard label="Orders" value={s.orders_count} sub="Total orders" icon={ShoppingBag} color="bg-violet-50" iconColor="text-violet-600"/>
        </div>
      </div>

      {/* Row 2 — Users & AI KPIs */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">👥 Users & AI</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Total Users" value={s.customers_count} sub={`${f.active_users ?? "—"} active`} icon={Users} color="bg-cyan-50" iconColor="text-cyan-600"/>
          <KpiCard label="Subscribers" value={f.subscribers} sub="Paid plans" icon={Zap} color="bg-amber-50" iconColor="text-amber-600"/>
          <KpiCard label="AI Jobs Today" value={f.ai_jobs_today} sub="Videos + Images" icon={Film} color="bg-pink-50" iconColor="text-pink-600"/>
          <KpiCard label="Credits Used" value={f.credits_used_today} sub="Today" icon={Cpu} color="bg-indigo-50" iconColor="text-indigo-600"/>
        </div>
      </div>

      {/* Row 3 — System + Low Stock */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">🖥 System</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Low Stock" value={s.low_stock_count} sub="Products" icon={AlertTriangle} danger/>
          <KpiCard label="Videos Made" value={f.total_videos} sub="All time" icon={Film} color="bg-violet-50" iconColor="text-violet-600"/>
          <KpiCard label="Products" value={s.products_count} sub="Active" icon={Package}/>

          {/* System Health Card */}
          <Card className="p-4">
            <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2">System Health</div>
            <div className="space-y-1.5">
              {[
                { label: "Backend",    ok: true },
                { label: "MongoDB",    ok: true },
                { label: "FLUX / HF",  ok: !!(f.hf_token_set) },
                { label: "Groq LLM",   ok: !!(f.groq_set) },
                { label: "OpenRouter", ok: !!(f.openrouter_set) },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between text-xs">
                  <span className="text-[var(--gs-muted)]">{item.label}</span>
                  <div className="flex items-center gap-1">
                    <HealthDot ok={item.ok}/>
                    <span className={item.ok ? "text-emerald-600" : "text-rose-500"}>{item.ok ? "OK" : "Not set"}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Revenue — last 7 days</h3>
            <TrendingUp className="h-4 w-4 text-[var(--gs-teal)]"/>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={s.series_7d || []}>
              <defs><linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#C58B7A" stopOpacity={0.5}/>
                <stop offset="100%" stopColor="#C58B7A" stopOpacity={0}/>
              </linearGradient></defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Area type="monotone" dataKey="revenue" stroke="#A86B5B" fill="url(#rev)"/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Orders — last 7 days</h3>
            <ShoppingBag className="h-4 w-4 text-[var(--gs-teal)]"/>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={s.series_7d || []}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={11}/>
              <YAxis stroke="#6B625B" fontSize={11} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Bar dataKey="orders" fill="#2F7E7A" radius={[4, 4, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Quick Actions */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">⚡ Quick Actions</div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {QUICK_ACTIONS.map(a => (
            <Link key={a.to} to={a.to}
              className="flex flex-col items-center gap-2 p-3 rounded-xl border bg-white hover:shadow-md transition-all text-center group">
              <div className={`h-9 w-9 rounded-xl ${a.color} grid place-items-center`}>
                <a.icon className="h-4 w-4 text-white"/>
              </div>
              <span className="text-[10px] font-semibold text-[var(--gs-ink)] leading-tight">{a.label}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Recent Orders */}
        <Card className="p-5" data-testid="admin-recent-orders-table">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Recent Orders</h3>
            <Link to="/admin/orders" className="text-xs text-[var(--gs-teal)] flex items-center gap-1">
              View all <ArrowUpRight className="h-3 w-3"/>
            </Link>
          </div>
          {(!s.recent_orders || s.recent_orders.length === 0) ? (
            <div className="text-center text-[var(--gs-muted)] py-8 text-sm">Is range mein koi orders nahi</div>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {s.recent_orders.map((o) => (
                <div key={o.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <div className="font-semibold">{o.order_number}</div>
                    <div className="text-xs text-[var(--gs-muted)]">{o.customer_name} · {new Date(o.created_at).toLocaleString("en-IN")}</div>
                  </div>
                  <Badge variant="outline" className="capitalize text-[10px]">{o.status}</Badge>
                  <div className="font-semibold">{fmtINR(o.total)}</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Live Activity Feed */}
        <LiveActivityFeed />
      </div>
    </div>
  );
}

function LiveActivityFeed() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const TYPE_ICON = {
    order:   { emoji: "💰", color: "bg-emerald-50 text-emerald-700" },
    ai_job:  { emoji: "🤖", color: "bg-violet-50 text-violet-700" },
    signup:  { emoji: "👤", color: "bg-blue-50 text-blue-700" },
  };

  const loadActivity = useCallback(async () => {
    try {
      const r = await api.get("/admin/live-activity?limit=15");
      setItems(r.data.items || []);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    loadActivity();
    const t = setInterval(loadActivity, 20000);
    return () => clearInterval(t);
  }, [loadActivity]);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2">
          <Radio className="h-4 w-4 text-[var(--gs-teal)] animate-pulse"/>Live Activity
        </h3>
        <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Auto-refresh 20s</Badge>
      </div>
      {loading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <div key={i} className="h-8 animate-pulse bg-[var(--gs-surface-2)] rounded-lg"/>)}</div>
      ) : items.length === 0 ? (
        <div className="text-center text-[var(--gs-muted)] text-sm py-8">
          <Activity className="h-8 w-8 mx-auto mb-2 opacity-30"/>
          Koi activity nahi abhi — orders, signups, AI jobs yahan dikhenge
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => {
            const style = TYPE_ICON[item.type] || { emoji: "⚡", color: "bg-slate-50 text-slate-700" };
            const timeAgo = item.at ? new Date(item.at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "";
            return (
              <div key={item.id || i} className={`flex items-center gap-3 p-2.5 rounded-xl ${style.color}`}>
                <span className="text-base">{style.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium truncate">{item.msg}</div>
                </div>
                <div className="text-[10px] opacity-60 flex-shrink-0">{timeAgo}</div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
