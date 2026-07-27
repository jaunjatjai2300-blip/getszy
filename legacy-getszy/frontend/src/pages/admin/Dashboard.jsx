import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import { Link } from "react-router-dom";
import {
  IndianRupee, Users, Film, Zap, TrendingUp, ShoppingBag,
  AlertTriangle, Activity, CheckCircle2, XCircle, Rocket,
  ArrowUpRight, RefreshCw, Sparkles, Cpu, Server, Package,
  BarChart3, Radio, Heart, Globe, ShoppingCart, CreditCard,
  UserPlus, BoxesIcon, Brain, Eye, Clock, Target, Flame,
  ArrowRight, LayoutDashboard
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ProdStatCard from "@/components/admin/ProdStatCard";
import HealthScore from "@/components/admin/HealthScore";
import SectionHeader from "@/components/admin/SectionHeader";
import { StatusBadge } from "@/components/admin/StatusBadge";

const QUICK_ACTIONS = [
  { label: "Add Product", icon: Package, to: "/admin/products", color: "bg-blue-500" },
  { label: "View Orders", icon: ShoppingCart, to: "/admin/orders", color: "bg-emerald-500" },
  { label: "Neo AI", icon: Sparkles, to: "/admin/chat", color: "bg-violet-500" },
  { label: "Video Studio", icon: Film, to: "/admin/video", color: "bg-pink-500" },
  { label: "Analytics", icon: BarChart3, to: "/admin/analytics", color: "bg-cyan-500" },
  { label: "Deploy", icon: Rocket, to: "/admin/deploy", color: "bg-orange-500" },
  { label: "Users", icon: Users, to: "/admin/users", color: "bg-indigo-500" },
  { label: "Growth", icon: TrendingUp, to: "/admin/growth", color: "bg-teal-500" },
  { label: "Settings", icon: Cpu, to: "/admin/settings", color: "bg-gray-600" },
];

const PIE_COLORS = ['#2F7E7A', '#A86B5B', '#6366f1', '#f59e0b', '#ec4899'];

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [chartRange, setChartRange] = useState("7d");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/admin/dashboard/executive");
      setData(r.data);
      setLastRefresh(new Date());
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  if (error) return (
    <div className="p-10 text-center space-y-3">
      <XCircle className="h-10 w-10 text-rose-400 mx-auto"/>
      <div className="text-[var(--gs-muted)]">Dashboard data load nahi ho saka.</div>
      <Button onClick={load} variant="outline" size="sm"><RefreshCw className="h-3.5 w-3.5 mr-1"/>Retry</Button>
    </div>
  );

  if (loading || !data) return (
    <div className="space-y-6">
      <div className="h-12 w-64 animate-pulse bg-[var(--gs-surface-2)] rounded-lg"/>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[1,2,3,4].map(i => <div key={i} className="h-28 animate-pulse bg-[var(--gs-surface-2)] rounded-xl"/>)}
      </div>
      <div className="grid lg:grid-cols-3 gap-3">
        {[1,2,3].map(i => <div key={i} className="h-64 animate-pulse bg-[var(--gs-surface-2)] rounded-xl"/>)}
      </div>
    </div>
  );

  const k = data.kpi || {};
  const s = data.series || {};
  const chartData = chartRange === '7d' ? (s.revenue_7d || []) : (s.revenue_30d || []);

  return (
    <div className="space-y-6" data-testid="admin-dashboard-page">

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <SectionHeader title="Dashboard" subtitle="Production command center — real-time business overview" icon={LayoutDashboard} loading={loading} onRefresh={load}/>
        <div className="flex items-center gap-2">
          {lastRefresh && (
            <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1">
              <Clock className="h-3 w-3"/>Live {lastRefresh.toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit'})}
            </span>
          )}
          <Select value={chartRange} onValueChange={setChartRange}>
            <SelectTrigger className="w-24 h-8 text-xs"><SelectValue/></SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">7 Days</SelectItem>
              <SelectItem value="30d">30 Days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Health Score + Quick Stats */}
      <div className="grid lg:grid-cols-4 gap-3">
        <HealthScore score={data.health_score}/>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Today</div>
          <div className="space-y-2">
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Revenue</span><span className="text-sm font-semibold">{fmtINR(k.revenue_today)}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Orders</span><span className="text-sm font-semibold">{k.orders_today}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">New Users</span><span className="text-sm font-semibold">{k.users_today}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">AI Jobs</span><span className="text-sm font-semibold">{k.ai_today}</span></div>
          </div>
        </Card>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">This Week</div>
          <div className="space-y-2">
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Revenue</span><span className="text-sm font-semibold">{fmtINR(k.revenue_week)}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Orders</span><span className="text-sm font-semibold">{k.orders_week}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">New Users</span><span className="text-sm font-semibold">{k.users_week}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">AI Jobs</span><span className="text-sm font-semibold">{k.ai_week}</span></div>
          </div>
        </Card>
        <Card className="p-4 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">This Month</div>
          <div className="space-y-2">
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Revenue</span><span className="text-sm font-semibold">{fmtINR(k.revenue_month)}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Growth</span><span className={`text-sm font-semibold ${k.rev_growth_pct >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>{k.rev_growth_pct >= 0 ? '+' : ''}{k.rev_growth_pct}%</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">Users</span><span className="text-sm font-semibold">{k.users_month}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs text-[var(--gs-muted)]">User Growth</span><span className={`text-sm font-semibold ${k.user_growth_pct >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>{k.user_growth_pct >= 0 ? '+' : ''}{k.user_growth_pct}%</span></div>
          </div>
        </Card>
      </div>

      {/* KPI Cards Row */}
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Key Metrics</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <ProdStatCard label="Total Revenue" value={fmtINR(k.total_revenue)} sub={`Profit: ${fmtINR(k.total_profit)}`} icon={IndianRupee} trend={k.rev_growth_pct}/>
          <ProdStatCard label="MRR" value={fmtINR(k.mrr)} sub={`ARR: ${fmtINR(k.arr)}`} icon={TrendingUp} color="bg-emerald-50" iconColor="text-emerald-600"/>
          <ProdStatCard label="Customers" value={k.customers} sub={`${k.active_users} active`} icon={Users} color="bg-cyan-50" iconColor="text-cyan-600" trend={k.user_growth_pct}/>
          <ProdStatCard label="Subscribers" value={k.active_subs} sub={`${k.pro_subs} Pro · ${k.elite_subs} Elite`} icon={CreditCard} color="bg-amber-50" iconColor="text-amber-600"/>
          <ProdStatCard label="Orders" value={k.total_orders} sub={`AOV: ${fmtINR(k.avg_order_value)}`} icon={ShoppingBag} color="bg-violet-50" iconColor="text-violet-600"/>
          <ProdStatCard label="AI Jobs" value={k.ai_month} sub={`${k.total_videos} videos · ${k.total_images} images`} icon={Brain} color="bg-pink-50" iconColor="text-pink-600"/>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <IndianRupee className="h-4 w-4 text-[var(--gs-teal)]"/>Revenue Trend
            </h3>
            <Badge className="bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] text-[10px] border-0">{chartRange === '7d' ? '7 Day' : '30 Day'}</Badge>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }} formatter={(v) => [`₹${v}`, 'Revenue']}/>
              <Area type="monotone" dataKey="revenue" stroke="#2F7E7A" fill="url(#revGrad)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <ShoppingBag className="h-4 w-4 text-[var(--gs-teal)]"/>Orders Trend
            </h3>
            <Badge className="bg-violet-50 text-violet-600 text-[10px] border-0">Daily</Badge>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Bar dataKey="orders" fill="#6366f1" radius={[4, 4, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* User Growth + Funnel */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-[var(--gs-teal)]"/>User Signups (30d)
            </h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={s.users_30d || []}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={10} tickLine={false} interval={4}/>
              <YAxis stroke="#6B625B" fontSize={10} tickLine={false} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
              <Line type="monotone" dataKey="signups" stroke="#A86B5B" strokeWidth={2} dot={false}/>
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Target className="h-4 w-4 text-[var(--gs-teal)]"/>Conversion Funnel
            </h3>
            <Badge className="bg-emerald-50 text-emerald-600 text-[10px] border-0">{data.conversion_rate}% conv.</Badge>
          </div>
          <FunnelViz funnel={data.funnel} rate={data.conversion_rate}/>
        </Card>
      </div>

      {/* Alerts */}
      {data.alerts && data.alerts.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold px-1">Alerts ({data.alerts.length})</div>
          {data.alerts.map((a, i) => {
            const styles = { warn: 'bg-amber-50 border-amber-200 text-amber-800', error: 'bg-rose-50 border-rose-200 text-rose-800', info: 'bg-blue-50 border-blue-200 text-blue-800' };
            const icons = { warn: AlertTriangle, error: XCircle, info: Activity };
            const Icon = icons[a.level] || AlertTriangle;
            return (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${styles[a.level] || styles.info}`}>
                <Icon className="h-4 w-4 flex-shrink-0"/>
                <span className="flex-1 text-sm">{a.msg}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom Grid: Top Products + Recent Orders + Activity */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Top Products */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Top Products</h3>
            <Link to="/admin/products" className="text-[10px] text-[var(--gs-teal)] flex items-center gap-1">View all <ArrowUpRight className="h-3 w-3"/></Link>
          </div>
          {(!data.top_products || data.top_products.length === 0) ? (
            <div className="text-center text-[var(--gs-muted)] py-8 text-xs">No product sales yet</div>
          ) : (
            <div className="space-y-2">
              {data.top_products.map((p, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded bg-[var(--gs-teal-soft)] grid place-items-center text-[10px] font-bold text-[var(--gs-teal)]">{i + 1}</div>
                    <span className="text-xs font-medium truncate max-w-[120px]">{p.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold">{fmtINR(p.revenue)}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{p.orders} orders</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Recent Orders */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Recent Orders</h3>
            <Link to="/admin/orders" className="text-[10px] text-[var(--gs-teal)] flex items-center gap-1">View all <ArrowUpRight className="h-3 w-3"/></Link>
          </div>
          {(!data.recent_orders || data.recent_orders.length === 0) ? (
            <div className="text-center text-[var(--gs-muted)] py-8 text-xs">No orders yet</div>
          ) : (
            <div className="space-y-2">
              {data.recent_orders.slice(0, 6).map((o, i) => (
                <div key={o.id || i} className="flex items-center justify-between py-1.5 border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
                  <div>
                    <div className="text-xs font-semibold">{o.order_number}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{o.customer_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold">{fmtINR(o.total)}</div>
                    <StatusBadge status={o.status} size="sm" dot={false}/>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Live Activity */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Radio className="h-3.5 w-3.5 text-[var(--gs-teal)] animate-pulse"/>Live Activity
            </h3>
            <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Auto 60s</Badge>
          </div>
          <div className="space-y-2 max-h-[280px] overflow-y-auto">
            {(data.activity || []).map((item, i) => {
              const TYPE_STYLE = { order: 'bg-emerald-50 text-emerald-700', ai_job: 'bg-violet-50 text-violet-700', signup: 'bg-blue-50 text-blue-700' };
              const TYPE_EMOJI = { order: '💰', ai_job: '🤖', signup: '👤' };
              const t = TYPE_STYLE[item.type] || 'bg-gray-50 text-gray-700';
              return (
                <div key={item.id || i} className={`flex items-center gap-2 p-2 rounded-lg ${t}`}>
                  <span className="text-sm">{TYPE_EMOJI[item.type] || '⚡'}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-medium truncate">{item.msg}</div>
                  </div>
                  <div className="text-[9px] opacity-60 flex-shrink-0">
                    {item.at ? new Date(item.at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : ''}
                  </div>
                </div>
              );
            })}
            {(!data.activity || data.activity.length === 0) && (
              <div className="text-center text-[var(--gs-muted)] py-6 text-xs">No recent activity</div>
            )}
          </div>
        </Card>
      </div>

      {/* System Health Row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <Server className="h-4 w-4 text-[var(--gs-teal)]"/>System Status
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'MongoDB', ok: data.mongo_ok },
              { label: 'Backend API', ok: true },
              { label: 'GROQ LLM', ok: data.env_health?.GROQ_API_KEY },
              { label: 'Gemini', ok: data.env_health?.GEMINI_API_KEY },
              { label: 'OpenRouter', ok: data.env_health?.OPENROUTER_API_KEY },
              { label: 'Razorpay', ok: data.env_health?.RAZORPAY_KEY_ID },
              { label: 'Ollama', ok: data.env_health?.OLLAMA_BASE_URL },
              { label: 'JWT Secret', ok: data.env_health?.JWT_SECRET },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between text-xs p-2 rounded-lg bg-[var(--gs-surface-2)]">
                <span className="text-[var(--gs-muted)]">{item.label}</span>
                <div className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${item.ok ? 'bg-emerald-500' : 'bg-rose-400'}`}/>
                  <span className={item.ok ? 'text-emerald-600' : 'text-rose-500'}>{item.ok ? 'OK' : 'Off'}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Quick Actions Grid */}
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <Zap className="h-4 w-4 text-[var(--gs-teal)]"/>Quick Actions
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {QUICK_ACTIONS.map(a => (
              <Link key={a.to} to={a.to} className="flex flex-col items-center gap-1.5 p-3 rounded-xl border bg-white hover:shadow-md transition-all text-center group" style={{ borderColor: "var(--gs-border)" }}>
                <div className={`h-8 w-8 rounded-lg ${a.color} grid place-items-center`}>
                  <a.icon className="h-4 w-4 text-white"/>
                </div>
                <span className="text-[10px] font-semibold text-[var(--gs-ink)] leading-tight">{a.label}</span>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      {/* Inventory Status */}
      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <BoxesIcon className="h-4 w-4 text-[var(--gs-teal)]"/>Inventory Overview
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 rounded-xl bg-[var(--gs-surface-2)]">
            <div className="text-2xl font-display">{k.total_products}</div>
            <div className="text-[10px] text-[var(--gs-muted)]">Total Products</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-emerald-50">
            <div className="text-2xl font-display text-emerald-600">{k.active_products}</div>
            <div className="text-[10px] text-emerald-700">Active</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-amber-50">
            <div className="text-2xl font-display text-amber-600">{k.low_stock}</div>
            <div className="text-[10px] text-amber-700">Low Stock</div>
          </div>
          <div className="text-center p-3 rounded-xl bg-rose-50">
            <div className="text-2xl font-display text-rose-600">{k.out_of_stock}</div>
            <div className="text-[10px] text-rose-700">Out of Stock</div>
          </div>
        </div>
      </Card>

      {/* Subscription Breakdown */}
      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-[var(--gs-teal)]"/>Subscription Breakdown
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: 'Active', value: k.active_subs, color: 'bg-emerald-50 text-emerald-700' },
            { label: 'Pro', value: k.pro_subs, color: 'bg-blue-50 text-blue-700' },
            { label: 'Elite', value: k.elite_subs, color: 'bg-violet-50 text-violet-700' },
            { label: 'Trial', value: k.trial_subs, color: 'bg-amber-50 text-amber-700' },
            { label: 'MRR', value: fmtINR(k.mrr), color: 'bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]' },
          ].map(item => (
            <div key={item.label} className={`text-center p-3 rounded-xl ${item.color}`}>
              <div className="text-xl font-display">{item.value ?? 0}</div>
              <div className="text-[10px] opacity-80">{item.label}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* AI Platform Status */}
      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
          <Brain className="h-4 w-4 text-[var(--gs-teal)]"/>AI Platform
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { label: 'Videos', value: k.total_videos, icon: Film, color: 'bg-violet-50 text-violet-600' },
            { label: 'Images', value: k.total_images, icon: Eye, color: 'bg-pink-50 text-pink-600' },
            { label: 'Voice', value: k.total_voice, icon: Activity, color: 'bg-blue-50 text-blue-600' },
            { label: 'Today', value: k.ai_today, icon: Flame, color: 'bg-orange-50 text-orange-600' },
            { label: 'This Week', value: k.ai_week, icon: BarChart3, color: 'bg-cyan-50 text-cyan-600' },
            { label: 'Credits Used', value: k.credits_used_month, icon: Zap, color: 'bg-amber-50 text-amber-600' },
          ].map(item => (
            <div key={item.label} className={`text-center p-3 rounded-xl ${item.color}`}>
              <item.icon className="h-4 w-4 mx-auto mb-1 opacity-80"/>
              <div className="text-xl font-display">{item.value ?? 0}</div>
              <div className="text-[10px] opacity-80">{item.label}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function FunnelViz({ funnel, rate }) {
  if (!funnel) return <div className="text-center text-[var(--gs-muted)] py-8 text-xs">No funnel data</div>;
  const stages = [
    { label: 'Total Users', value: funnel.visitors, pct: 100 },
    { label: 'Customers', value: funnel.signups, pct: funnel.visitors ? Math.round(funnel.signups / funnel.visitors * 100) : 0 },
    { label: 'Subscribers', value: funnel.subscribers, pct: funnel.signups ? Math.round(funnel.subscribers / funnel.signups * 100) : 0 },
  ];
  const colors = ['#6366f1', '#2F7E7A', '#10b981'];

  return (
    <div className="space-y-2">
      {stages.map((st, i) => (
        <div key={st.label} className="relative">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-[var(--gs-muted)]">{st.label}</span>
            <span className="font-semibold">{st.value?.toLocaleString() || 0} <span className="text-[var(--gs-muted)]">({st.pct}%)</span></span>
          </div>
          <div className="h-6 rounded-lg bg-gray-100 overflow-hidden">
            <div className="h-full rounded-lg transition-all duration-700" style={{ width: `${st.pct}%`, backgroundColor: colors[i] }}/>
          </div>
        </div>
      ))}
      <div className="text-center pt-2">
        <span className="text-xs text-[var(--gs-muted)]">Visitor → Subscriber: </span>
        <span className="text-sm font-bold text-[var(--gs-teal)]">{rate}%</span>
      </div>
    </div>
  );
}
