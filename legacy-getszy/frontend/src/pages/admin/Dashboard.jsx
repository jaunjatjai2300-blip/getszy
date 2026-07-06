import { useEffect, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { TrendingUp, ShoppingBag, Users, Package, AlertTriangle, IndianRupee, ArrowUpRight } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";

const KPIS = [
  { key: "revenue", label: "Revenue", icon: IndianRupee, fmt: (v) => fmtINR(v) },
  { key: "orders_count", label: "Orders", icon: ShoppingBag, fmt: (v) => v },
  { key: "customers_count", label: "Customers", icon: Users, fmt: (v) => v },
  { key: "low_stock_count", label: "Low stock", icon: AlertTriangle, fmt: (v) => v, danger: true },
];

export default function AdminDashboard() {
  const [range, setRange] = useState("month");
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    api.get(`/admin/stats?range=${range}`).then(({ data }) => setStats(data)).catch(() => setError(true));
  }, [range]);

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Could not load dashboard stats. Please refresh the page.
    </div>
  );
  if (!stats) return <div className="p-6 text-center">Loading…</div>;

  return (
    <div className="space-y-6" data-testid="admin-dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Welcome back</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Here's what's happening with your store</p>
        </div>
        <Select value={range} onValueChange={setRange}>
          <SelectTrigger className="w-40" data-testid="admin-dashboard-range-select"><SelectValue/></SelectTrigger>
          <SelectContent>
            <SelectItem value="today">Today</SelectItem>
            <SelectItem value="week">This week</SelectItem>
            <SelectItem value="month">This month</SelectItem>
            <SelectItem value="all">All time</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        {KPIS.map((k) => (
          <div key={k.key} className="gs-card p-4 sm:p-5" data-testid={`admin-kpi-${k.key}`}>
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase tracking-wider text-[var(--gs-muted)]">{k.label}</div>
              <div className={`h-8 w-8 rounded-lg grid place-items-center ${k.danger ? "bg-rose-50 text-rose-600" : "bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]"}`}><k.icon className="h-4 w-4"/></div>
            </div>
            <div className="text-2xl sm:text-3xl font-display mt-2" style={{ fontVariantNumeric: "tabular-nums" }}>{k.fmt(stats[k.key])}</div>
            {k.key === "revenue" && <div className="text-xs text-[var(--gs-muted)] mt-1">Profit: <span className="font-semibold text-[var(--gs-teal)]">{fmtINR(stats.profit)}</span></div>}
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="gs-card p-5">
          <div className="flex items-center justify-between mb-3"><h3 className="font-semibold">Revenue — last 7 days</h3><TrendingUp className="h-4 w-4 text-[var(--gs-teal)]"/></div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={stats.series_7d}>
              <defs><linearGradient id="rev" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#C58B7A" stopOpacity={0.5}/><stop offset="100%" stopColor="#C58B7A" stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={12}/><YAxis stroke="#6B625B" fontSize={12}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8 }}/>
              <Area type="monotone" dataKey="revenue" stroke="#A86B5B" fill="url(#rev)"/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="gs-card p-5">
          <div className="flex items-center justify-between mb-3"><h3 className="font-semibold">Orders — last 7 days</h3><ShoppingBag className="h-4 w-4 text-[var(--gs-teal)]"/></div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.series_7d}>
              <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#6B625B" fontSize={12}/><YAxis stroke="#6B625B" fontSize={12} allowDecimals={false}/>
              <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8 }}/>
              <Bar dataKey="orders" fill="#2F7E7A" radius={[6, 6, 0, 0]}/>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="gs-card p-5" data-testid="admin-recent-orders-table">
        <div className="flex items-center justify-between mb-4"><h3 className="font-semibold">Recent orders</h3><Link to="/admin/orders" className="text-xs gs-link">View all <ArrowUpRight className="h-3 w-3 inline"/></Link></div>
        {(!stats.recent_orders || stats.recent_orders.length === 0) ? (
          <div className="text-center text-[var(--gs-muted)] py-8 text-sm">No orders in this range</div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
            {stats.recent_orders.map((o) => (
              <div key={o.id} className="flex items-center justify-between py-3 text-sm">
                <div><div className="font-semibold">{o.order_number}</div><div className="text-xs text-[var(--gs-muted)]">{o.customer_name} · {new Date(o.created_at).toLocaleString()}</div></div>
                <Badge variant="outline" className="capitalize">{o.status}</Badge>
                <div className="font-semibold">{fmtINR(o.total)}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
