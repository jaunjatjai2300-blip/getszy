import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { BarChart3, TrendingUp, Users, Film, Zap, IndianRupee, RefreshCw, Target, Activity } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell, Legend, FunnelChart, Funnel, LabelList,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const COLORS = ["#2F7E7A", "#C58B7A", "#7C3AED", "#F59E0B", "#EC4899", "#06B6D4"];

function StatCard({ label, value, sub, icon: Icon, color = "bg-[var(--gs-teal-soft)]", iconColor = "text-[var(--gs-teal)]", loading }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${color}`}>
          <Icon className={`h-4 w-4 ${iconColor}`}/>
        </div>
      </div>
      <div className="text-2xl font-display">{loading ? "…" : (value ?? "—")}</div>
      {sub && <div className="text-[11px] text-[var(--gs-muted)]">{sub}</div>}
    </Card>
  );
}

const FUNNEL_COLORS = ["#2F7E7A", "#C58B7A", "#7C3AED"];

export default function Analytics() {
  const [range, setRange] = useState("month");
  const [stats, setStats] = useState(null);
  const [founder, setFounder] = useState(null);
  const [series, setSeries] = useState([]);
  const [funnel, setFunnel] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seriesDays, setSeriesDays] = useState("30");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, f, ser, fn] = await Promise.allSettled([
        api.get(`/admin/stats?range=${range}`),
        api.get("/admin/founder-stats"),
        api.get(`/admin/analytics/series?days=${seriesDays}`),
        api.get("/admin/analytics/funnel"),
      ]);
      if (s.status === "fulfilled")   setStats(s.value.data);
      if (f.status === "fulfilled")   setFounder(f.value.data || {});
      if (ser.status === "fulfilled") setSeries(ser.value.data?.series || []);
      if (fn.status === "fulfilled")  setFunnel(fn.value.data?.funnel || []);
    } finally { setLoading(false); }
  }, [range, seriesDays]);

  useEffect(() => { load(); }, [load]);

  const s = stats || {};
  const f = founder || {};
  const revenueData = s.series_7d || [];

  const aiData = [
    { name: "Video Jobs", value: f.total_videos || 0 },
    { name: "AI Images",  value: f.total_images || 0 },
    { name: "Voice",      value: f.total_voice || 0 },
    { name: "LLM Calls",  value: f.total_llm || 0 },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Analytics</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Revenue · Users · AI Usage · Funnel — sab ek jagah</p>
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

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Revenue"  value={fmtINR(s.revenue)} sub={`Profit: ${fmtINR(s.profit)}`}        icon={IndianRupee} loading={loading}/>
        <StatCard label="MRR"      value={fmtINR(f.mrr)}     sub="Monthly recurring"                    icon={TrendingUp}  loading={loading} color="bg-emerald-50" iconColor="text-emerald-600"/>
        <StatCard label="Users"    value={s.customers_count} sub={`${f.active_users || 0} active`}       icon={Users}       loading={loading} color="bg-blue-50"    iconColor="text-blue-600"/>
        <StatCard label="AI Jobs"  value={(f.total_videos||0)+(f.total_images||0)} sub="Videos + Images" icon={Film}        loading={loading} color="bg-violet-50"  iconColor="text-violet-600"/>
      </div>

      <Tabs defaultValue="revenue">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="revenue"><IndianRupee className="h-3.5 w-3.5 mr-1"/>Revenue</TabsTrigger>
          <TabsTrigger value="growth"><Users className="h-3.5 w-3.5 mr-1"/>Growth</TabsTrigger>
          <TabsTrigger value="funnel"><Target className="h-3.5 w-3.5 mr-1"/>Funnel</TabsTrigger>
          <TabsTrigger value="ai"><Film className="h-3.5 w-3.5 mr-1"/>AI Usage</TabsTrigger>
          <TabsTrigger value="credits"><Zap className="h-3.5 w-3.5 mr-1"/>Credits</TabsTrigger>
        </TabsList>

        {/* ── Revenue ── */}
        <TabsContent value="revenue" className="mt-4 space-y-4">
          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-3">Revenue — Last 7 Days</h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={revenueData}>
                  <defs><linearGradient id="rev2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.4}/>
                    <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                  </linearGradient></defs>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="date" fontSize={11}/>
                  <YAxis fontSize={11}/>
                  <Tooltip contentStyle={{ fontSize: 11 }}/>
                  <Area type="monotone" dataKey="revenue" stroke="#2F7E7A" fill="url(#rev2)"/>
                </AreaChart>
              </ResponsiveContainer>
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-3">Orders — Last 7 Days</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={revenueData}>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="date" fontSize={11}/>
                  <YAxis fontSize={11} allowDecimals={false}/>
                  <Tooltip contentStyle={{ fontSize: 11 }}/>
                  <Bar dataKey="orders" fill="#C58B7A" radius={[4,4,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Total Revenue" value={fmtINR(s.revenue)}  icon={IndianRupee}/>
            <StatCard label="Total Profit"  value={fmtINR(s.profit)}   icon={TrendingUp} color="bg-emerald-50" iconColor="text-emerald-600"/>
            <StatCard label="Orders"        value={s.orders_count}      icon={BarChart3}/>
            <StatCard label="Avg Order"     value={s.orders_count ? fmtINR(Math.round((s.revenue||0)/s.orders_count)) : "—"} icon={IndianRupee}/>
          </div>
        </TabsContent>

        {/* ── Growth (30d time series) ── */}
        <TabsContent value="growth" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Daily Growth — Last</h3>
            <Select value={seriesDays} onValueChange={v => { setSeriesDays(v); }}>
              <SelectTrigger className="w-24 h-7 text-xs"><SelectValue/></SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7 days</SelectItem>
                <SelectItem value="30">30 days</SelectItem>
                <SelectItem value="90">90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-3">New Users per Day</h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={series}>
                  <defs><linearGradient id="users" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.4}/>
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity={0}/>
                  </linearGradient></defs>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="date" fontSize={10} interval={Math.floor(series.length / 6)}/>
                  <YAxis fontSize={11} allowDecimals={false}/>
                  <Tooltip contentStyle={{ fontSize: 11 }}/>
                  <Area type="monotone" dataKey="new_users" stroke="#3B82F6" fill="url(#users)" name="New Users"/>
                </AreaChart>
              </ResponsiveContainer>
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-3">AI Jobs per Day</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={series}>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="date" fontSize={10} interval={Math.floor(series.length / 6)}/>
                  <YAxis fontSize={11} allowDecimals={false}/>
                  <Tooltip contentStyle={{ fontSize: 11 }}/>
                  <Bar dataKey="ai_jobs" fill="#7C3AED" radius={[4,4,0,0]} name="AI Jobs"/>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-3">Credits Spent per Day</h3>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={series}>
                <defs><linearGradient id="cr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity={0}/>
                </linearGradient></defs>
                <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                <XAxis dataKey="date" fontSize={10} interval={Math.floor(series.length / 6)}/>
                <YAxis fontSize={11}/>
                <Tooltip contentStyle={{ fontSize: 11 }}/>
                <Area type="monotone" dataKey="credits_spent" stroke="#F59E0B" fill="url(#cr)" name="Credits Spent"/>
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        {/* ── Funnel ── */}
        <TabsContent value="funnel" className="mt-4 space-y-4">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2"><Target className="h-4 w-4 text-[var(--gs-teal)]"/>Conversion Funnel</h3>
              {funnel.length === 0 ? (
                <div className="text-center py-10 text-[var(--gs-muted)] text-sm">Loading funnel data…</div>
              ) : (
                <div className="space-y-3">
                  {funnel.map((stage, i) => (
                    <div key={stage.stage} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{stage.stage}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{stage.count}</span>
                          <Badge className="text-[10px]" style={{ background: FUNNEL_COLORS[i], color: "white" }}>{stage.pct}%</Badge>
                        </div>
                      </div>
                      <div className="h-6 rounded-lg overflow-hidden bg-[var(--gs-surface-2)]">
                        <div className="h-full rounded-lg transition-all" style={{ width: `${stage.pct}%`, background: FUNNEL_COLORS[i] }}/>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4">User Plan Distribution</h3>
              <div className="space-y-3">
                {[
                  { label: "Free",      value: (s.customers_count||0) - (f.subscribers||0), color: "bg-slate-300" },
                  { label: "Subscribed", value: f.subscribers||0,                             color: "bg-[var(--gs-teal)]" },
                ].map(p => (
                  <div key={p.label} className="flex items-center gap-3">
                    <div className="text-xs w-24 text-[var(--gs-muted)]">{p.label}</div>
                    <div className="flex-1 h-3 rounded-full bg-[var(--gs-surface-2)]">
                      <div className={`h-full rounded-full ${p.color}`}
                        style={{ width: s.customers_count ? `${Math.round((p.value / s.customers_count) * 100)}%` : "0%" }}/>
                    </div>
                    <div className="text-xs font-bold w-8 text-right">{p.value}</div>
                  </div>
                ))}
              </div>
              <div className="mt-6 grid grid-cols-2 gap-3">
                <StatCard label="Total Users"   value={s.customers_count} icon={Users}/>
                <StatCard label="Active (30d)"  value={f.active_users}    icon={Activity} color="bg-emerald-50" iconColor="text-emerald-600"/>
                <StatCard label="Subscribers"   value={f.subscribers}     icon={Zap}      color="bg-amber-50"   iconColor="text-amber-600"/>
                <StatCard label="Free Users"    value={(s.customers_count||0)-(f.subscribers||0)} icon={Users} color="bg-slate-50" iconColor="text-slate-600"/>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* ── AI Usage ── */}
        <TabsContent value="ai" className="mt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard label="Videos Made"   value={f.total_videos}  icon={Film}     color="bg-violet-50" iconColor="text-violet-600"/>
            <StatCard label="AI Images"     value={f.total_images}  icon={BarChart3} color="bg-pink-50"  iconColor="text-pink-600"/>
            <StatCard label="AI Jobs Today" value={f.ai_jobs_today} icon={Zap}      color="bg-amber-50"  iconColor="text-amber-600"/>
            <StatCard label="LLM Calls"     value={f.total_llm}     icon={BarChart3} color="bg-cyan-50"  iconColor="text-cyan-600"/>
          </div>
          {aiData.length > 0 ? (
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-3">AI Usage Breakdown</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={aiData} cx="50%" cy="50%" outerRadius={100} dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`} labelLine>
                    {aiData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]}/>)}
                  </Pie>
                  <Tooltip/>
                  <Legend/>
                </PieChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Card className="p-10 text-center text-[var(--gs-muted)] text-sm">
              Abhi tak koi AI jobs nahi hain. Video Studio se pehla video banao!
            </Card>
          )}
        </TabsContent>

        {/* ── Credits ── */}
        <TabsContent value="credits" className="mt-4 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Credits Used Today"  value={f.credits_used_today}  icon={Zap}/>
            <StatCard label="Credits Used (Month)" value={f.credits_used_month} icon={Zap}   color="bg-amber-50"   iconColor="text-amber-600"/>
            <StatCard label="Total Granted"        value={f.credits_granted}    icon={Zap}   color="bg-emerald-50" iconColor="text-emerald-600"/>
            <StatCard label="Avg per User"         value={f.customers_count ? Math.round((f.credits_granted||0)/f.customers_count) : "—"} icon={Users}/>
          </div>
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-3">Credits Spent — Daily</h3>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={series}>
                <defs><linearGradient id="credits2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.4}/>
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity={0}/>
                </linearGradient></defs>
                <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                <XAxis dataKey="date" fontSize={10} interval={Math.floor(series.length / 6)}/>
                <YAxis fontSize={11}/>
                <Tooltip contentStyle={{ fontSize: 11 }}/>
                <Area type="monotone" dataKey="credits_spent" stroke="#F59E0B" fill="url(#credits2)" name="Credits"/>
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
