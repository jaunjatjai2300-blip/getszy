import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import {
  RefreshCw, ShoppingCart, Package, Users, Tag, ArrowUpDown,
  CheckCircle2, XCircle, AlertTriangle, Send, Clock, Loader2,
  Wifi, WifiOff, Database, Layers, Eye
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function HealthDot({ ok }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}/>;
}

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

function SyncStatusBadge({ status }) {
  const map = {
    synced: "bg-emerald-100 text-emerald-700",
    pending: "bg-amber-100 text-amber-700",
    error: "bg-rose-100 text-rose-700",
    conflict: "bg-orange-100 text-orange-700",
  };
  return <Badge className={`text-[10px] ${map[status] || "bg-slate-100 text-slate-600"}`}>{status}</Badge>;
}

export default function WooSync() {
  const [tab, setTab] = useState("products");
  const [connection, setConnection] = useState(null);
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    setError(false);
    try {
      const [conn, st, prods, ords, inv, custs, cps, lg] = await Promise.all([
        api.get("/admin/woo-sync/connection").catch(() => ({ data: { connected: false } })),
        api.get("/admin/woo-sync/stats").catch(() => ({ data: {} })),
        api.get("/admin/woo-sync/products").catch(() => ({ data: { items: [] } })),
        api.get("/admin/woo-sync/orders").catch(() => ({ data: { items: [] } })),
        api.get("/admin/woo-sync/inventory").catch(() => ({ data: { items: [] } })),
        api.get("/admin/woo-sync/customers").catch(() => ({ data: { items: [] } })),
        api.get("/admin/woo-sync/coupons").catch(() => ({ data: { items: [] } })),
        api.get("/admin/woo-sync/logs").catch(() => ({ data: { items: [] } })),
      ]);
      setConnection(conn.data);
      setStats(st.data);
      setProducts(prods.data?.items || []);
      setOrders(ords.data?.items || []);
      setInventory(inv.data?.items || []);
      setCustomers(custs.data?.items || []);
      setCoupons(cps.data?.items || []);
      setLogs(lg.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const fullSync = async () => {
    setSyncing(true);
    try {
      await api.post("/admin/woo-sync/full-sync");
      await load();
    } catch { /* silent */ }
    setSyncing(false);
  };

  const pushProduct = async (wcId) => {
    try {
      await api.post(`/admin/woo-sync/push-product/${wcId}`);
      setProducts(prev => prev.map(p => p.wc_id === wcId ? { ...p, sync_status: "synced" } : p));
    } catch { /* silent */ }
  };

  const adjustStock = async (productId, qty) => {
    try {
      await api.post(`/admin/woo-sync/adjust-stock/${productId}`, { quantity: qty });
      await load();
    } catch { /* silent */ }
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  const s = stats || {};
  const conn = connection || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">WooCommerce Sync</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Bidirectional sync with WooCommerce store</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="h-8" onClick={load}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
          <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={fullSync} disabled={syncing}>
            {syncing ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin"/> : <RefreshCw className="h-3.5 w-3.5 mr-1"/>}
            Full Sync
          </Button>
        </div>
      </div>

      {/* Connection Status */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {conn.connected ? <Wifi className="h-5 w-5 text-emerald-500"/> : <WifiOff className="h-5 w-5 text-rose-500"/>}
            <div>
              <div className="text-sm font-semibold flex items-center gap-2">
                WooCommerce Connection
                <HealthDot ok={conn.connected}/>
                <span className={conn.connected ? "text-emerald-600 text-xs" : "text-rose-500 text-xs"}>
                  {conn.connected ? "Connected" : "Disconnected"}
                </span>
              </div>
              {conn.store_url && <div className="text-xs text-[var(--gs-muted)]">{conn.store_url}</div>}
            </div>
          </div>
          {conn.last_sync && (
            <div className="text-xs text-[var(--gs-muted)]">Last sync: {new Date(conn.last_sync).toLocaleString("en-IN")}</div>
          )}
        </div>
      </Card>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="WC Products" value={s.total_products ?? products.length} sub="Synced products" icon={Package}/>
        <KpiCard label="WC Orders" value={s.total_orders ?? orders.length} sub="All orders" icon={ShoppingCart} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="WC Customers" value={s.total_customers ?? customers.length} sub="Synced customers" icon={Users} color="bg-violet-50" iconColor="text-violet-600"/>
        <KpiCard label="Pending Sync" value={s.pending_sync ?? 0} sub="Awaiting sync" icon={Clock} color="bg-amber-50" iconColor="text-amber-600"/>
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="products">Products ({products.length})</TabsTrigger>
          <TabsTrigger value="orders">Orders ({orders.length})</TabsTrigger>
          <TabsTrigger value="inventory">Inventory</TabsTrigger>
          <TabsTrigger value="customers">Customers ({customers.length})</TabsTrigger>
          <TabsTrigger value="coupons">Coupons ({coupons.length})</TabsTrigger>
          <TabsTrigger value="logs">Sync Logs</TabsTrigger>
        </TabsList>

        {/* Products Tab */}
        <TabsContent value="products" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">WC ID</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Name</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Price</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Stock</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Sync Status</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {products.map((p) => (
                    <tr key={p.wc_id || p.id} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 font-mono text-xs">{p.wc_id}</td>
                      <td className="p-3 font-semibold">{p.name}</td>
                      <td className="p-3">{fmtINR(p.price)}</td>
                      <td className="p-3">{p.stock ?? "—"}</td>
                      <td className="p-3"><SyncStatusBadge status={p.sync_status}/></td>
                      <td className="p-3 text-right">
                        <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => pushProduct(p.wc_id)}>
                          <Send className="h-3 w-3 mr-1"/>Push
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {products.length === 0 && (
                    <tr><td colSpan={6} className="p-6 text-center text-[var(--gs-muted)] text-sm">No products found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Orders Tab */}
        <TabsContent value="orders" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Order #</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Customer</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Total</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Sync Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {orders.map((o) => (
                    <tr key={o.wc_id || o.id} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 font-mono text-xs">#{o.order_number}</td>
                      <td className="p-3">{o.customer_name}</td>
                      <td className="p-3 font-semibold">{fmtINR(o.total)}</td>
                      <td className="p-3"><Badge variant="outline" className="capitalize text-[10px]">{o.status}</Badge></td>
                      <td className="p-3"><SyncStatusBadge status={o.sync_status}/></td>
                    </tr>
                  ))}
                  {orders.length === 0 && (
                    <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No orders found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Inventory Tab */}
        <TabsContent value="inventory" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Product</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Local Stock</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">WC Stock</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Difference</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {inventory.map((inv) => {
                    const diff = (inv.local_stock || 0) - (inv.wc_stock || 0);
                    return (
                      <tr key={inv.product_id || inv.id} className="hover:bg-[var(--gs-surface-2)]">
                        <td className="p-3 font-semibold">{inv.product_name}</td>
                        <td className="p-3">{inv.local_stock}</td>
                        <td className="p-3">{inv.wc_stock}</td>
                        <td className="p-3">
                          <span className={diff !== 0 ? "text-amber-600 font-semibold" : ""}>{diff > 0 ? `+${diff}` : diff}</span>
                        </td>
                        <td className="p-3 text-right">
                          <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => adjustStock(inv.product_id, inv.local_stock)}>
                            <ArrowUpDown className="h-3 w-3 mr-1"/>Adjust
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                  {inventory.length === 0 && (
                    <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No inventory data</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Customers Tab */}
        <TabsContent value="customers" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">WC ID</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Name</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Email</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Orders</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Sync Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {customers.map((c) => (
                    <tr key={c.wc_id || c.id} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 font-mono text-xs">{c.wc_id}</td>
                      <td className="p-3 font-semibold">{c.name}</td>
                      <td className="p-3 text-[var(--gs-muted)]">{c.email}</td>
                      <td className="p-3">{c.orders_count ?? 0}</td>
                      <td className="p-3"><SyncStatusBadge status={c.sync_status}/></td>
                    </tr>
                  ))}
                  {customers.length === 0 && (
                    <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No customers found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Coupons Tab */}
        <TabsContent value="coupons" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Code</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Type</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Amount</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Usage</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {coupons.map((c) => (
                    <tr key={c.wc_id || c.id} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 font-mono text-xs font-semibold">{c.code}</td>
                      <td className="p-3"><Badge variant="outline" className="text-[10px]">{c.type}</Badge></td>
                      <td className="p-3">{c.type === "percent" ? `${c.amount}%` : fmtINR(c.amount)}</td>
                      <td className="p-3">{c.usage_count ?? 0} / {c.usage_limit || "∞"}</td>
                      <td className="p-3"><SyncStatusBadge status={c.sync_status}/></td>
                    </tr>
                  ))}
                  {coupons.length === 0 && (
                    <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No coupons found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Timestamp</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Action</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {logs.map((l, i) => (
                    <tr key={l.id || i} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 text-xs text-[var(--gs-muted)]">{l.timestamp ? new Date(l.timestamp).toLocaleString("en-IN") : "—"}</td>
                      <td className="p-3 font-semibold">{l.action}</td>
                      <td className="p-3">
                        {l.status === "success" ? (
                          <span className="flex items-center gap-1 text-emerald-600 text-xs"><CheckCircle2 className="h-3 w-3"/>Success</span>
                        ) : l.status === "error" ? (
                          <span className="flex items-center gap-1 text-rose-500 text-xs"><XCircle className="h-3 w-3"/>Error</span>
                        ) : (
                          <span className="flex items-center gap-1 text-amber-600 text-xs"><AlertTriangle className="h-3 w-3"/>Warning</span>
                        )}
                      </td>
                      <td className="p-3 text-xs text-[var(--gs-muted)] max-w-xs truncate">{l.details}</td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No sync logs yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
