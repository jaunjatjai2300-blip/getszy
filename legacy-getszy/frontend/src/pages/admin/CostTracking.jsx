import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { IndianRupee, TrendingUp, Zap, RefreshCw, Coins } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#2F7E7A", "#C58B7A", "#7C3AED", "#F59E0B", "#EC4899", "#06B6D4"];

export default function CostTracking() {
  const [myCost, setMyCost] = useState(null);
  const [globalCost, setGlobalCost] = useState([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [my, glob] = await Promise.allSettled([
        api.get(`/extras/cost/my?days=${days}`),
        api.get(`/extras/cost/global?days=${days}`),
      ]);
      if (my.status === "fulfilled") setMyCost(my.value.data);
      if (glob.status === "fulfilled") setGlobalCost(glob.value.data || []);
    } finally { setLoading(false); }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const providerData = (myCost?.by_provider || []).map(p => ({
    name: p._id, tokens: p.total_tokens, cost: p.total_cost, requests: p.requests
  }));

  const globalData = globalCost.map(g => ({
    name: `${g._id?.provider}/${g._id?.model || 'unknown'}`,
    tokens: g.total_tokens, cost: g.total_cost, requests: g.requests
  }));

  return (
    <div className="space-y-6" data-testid="cost-tracking-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-amber-100 grid place-items-center">
            <IndianRupee className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h1 className="text-2xl font-display">AI Cost Tracking</h1>
            <p className="text-xs text-[var(--gs-muted)]">Monitor AI usage costs across providers</p>
          </div>
        </div>
        <div className="flex gap-2">
          <select value={days} onChange={e => setDays(+e.target.value)}
            className="h-9 px-3 rounded-lg border border-[var(--gs-border)] bg-[var(--gs-surface)] text-sm">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <RefreshCw className={`h-4 w-4 mt-2 cursor-pointer text-[var(--gs-muted)] ${loading ? 'animate-spin' : ''}`} onClick={load} />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 text-[var(--gs-teal)]" />
            <span className="text-xs uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Total Cost</span>
          </div>
          <div className="text-3xl font-display">${loading ? "…" : (myCost?.total_cost_usd?.toFixed(4) ?? "0.00")}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Last {days} days</p>
        </Card>
        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-purple-600" />
            <span className="text-xs uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Total Tokens</span>
          </div>
          <div className="text-3xl font-display">{loading ? "…" : (myCost?.total_tokens?.toLocaleString() ?? "0")}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Across all providers</p>
        </Card>
        <Card className="p-4 space-y-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-600" />
            <span className="text-xs uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Providers Used</span>
          </div>
          <div className="text-3xl font-display">{loading ? "…" : providerData.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Active AI providers</p>
        </Card>
      </div>

      <Tabs defaultValue="my">
        <TabsList>
          <TabsTrigger value="my">My Usage</TabsTrigger>
          <TabsTrigger value="global">Global Usage</TabsTrigger>
        </TabsList>

        <TabsContent value="my" className="space-y-4">
          {providerData.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card className="p-5">
                <h3 className="font-display text-sm mb-4">Cost by Provider</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={providerData}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="cost" fill="#2F7E7A" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <Card className="p-5">
                <h3 className="font-display text-sm mb-4">Token Distribution</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={providerData} dataKey="tokens" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                      {providerData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Card>
            </div>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No usage data yet</Card>
          )}

          {/* Provider breakdown table */}
          {providerData.length > 0 && (
            <Card className="p-5">
              <h3 className="font-display text-sm mb-3">Provider Breakdown</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] text-[var(--gs-muted)] uppercase border-b border-[var(--gs-border)]">
                    <th className="text-left py-2">Provider</th>
                    <th className="text-right py-2">Tokens</th>
                    <th className="text-right py-2">Cost</th>
                    <th className="text-right py-2">Requests</th>
                  </tr>
                </thead>
                <tbody>
                  {providerData.map(p => (
                    <tr key={p.name} className="border-b border-[var(--gs-border)]/50">
                      <td className="py-2 font-medium flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">{p.name}</Badge>
                      </td>
                      <td className="text-right">{p.tokens.toLocaleString()}</td>
                      <td className="text-right">${p.cost.toFixed(6)}</td>
                      <td className="text-right">{p.requests}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="global">
          {globalData.length > 0 ? (
            <Card className="p-5">
              <h3 className="font-display text-sm mb-4">Global AI Usage (All Users)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={globalData}>
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={80} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="cost" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No global usage data</Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
