import { useEffect, useState, useMemo } from "react";
import { api, fmtINR } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  ShoppingCart, Search, RefreshCw, Download, TrendingUp,
  IndianRupee, Package, Clock, Truck, CheckCircle2, XCircle,
  ArrowUpDown, ArrowUp, ArrowDown, Eye, Filter, DollarSign,
  AlertTriangle, BarChart3, Calendar
} from "lucide-react";
import NeoPanel from "@/components/admin/NeoPanel";
import { toast } from "sonner";
import SectionHeader from "@/components/admin/SectionHeader";
import { StatusBadge } from "@/components/admin/StatusBadge";
import ProdStatCard from "@/components/admin/ProdStatCard";

const STATUSES = ["pending", "forwarded", "shipped", "delivered", "cancelled"];

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("all");
  const [editOrder, setEditOrder] = useState(null);
  const [status, setStatus] = useState("pending");
  const [tracking, setTracking] = useState("");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const PER_PAGE = 20;

  const load = async () => {
    setLoading(true);
    try { const { data } = await api.get("/admin/orders"); setOrders(Array.isArray(data) ? data : []); }
    catch { toast.error("Failed to load orders"); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    let list = orders;
    if (filter !== 'all') list = list.filter(o => o.status === filter);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(o => o.order_number?.toLowerCase().includes(q) || o.customer_name?.toLowerCase().includes(q) || o.customer_email?.toLowerCase().includes(q));
    }
    list = [...list].sort((a, b) => {
      const va = a[sortKey], vb = b[sortKey];
      if (va == null) return 1; if (vb == null) return -1;
      if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
      return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    return list;
  }, [orders, filter, search, sortKey, sortDir]);

  const paged = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(filtered.length / PER_PAGE);

  const toggleSort = (k) => { if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc'); else { setSortKey(k); setSortDir('desc'); } };
  const SortIcon = ({ k }) => sortKey === k ? (sortDir === 'asc' ? <ArrowUp className="h-3 w-3"/> : <ArrowDown className="h-3 w-3"/>) : <ArrowUpDown className="h-3 w-3 opacity-30"/>;

  const openEdit = (o) => { setEditOrder(o); setStatus(o.status); setTracking(o.tracking_number || ""); };
  const save = async () => {
    try {
      await api.put(`/admin/orders/${editOrder.id}/status`, { status, tracking_number: tracking || null });
      toast.success("Order updated"); setEditOrder(null); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Update failed"); }
  };

  const exportCSV = () => {
    const rows = [['Order #', 'Customer', 'Email', 'Items', 'Total', 'Profit', 'Status', 'Date']];
    filtered.forEach(o => rows.push([o.order_number, o.customer_name, o.customer_email, o.items?.length || 0, o.total, o.profit || 0, o.status, o.created_at]));
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'orders.csv'; a.click();
    toast.success("Exported " + filtered.length + " orders");
  };

  // Stats
  const totalOrders = orders.length;
  const totalRevenue = orders.reduce((s, o) => s + (o.total || 0), 0);
  const totalProfit = orders.reduce((s, o) => s + (o.profit || 0), 0);
  const avgOrder = totalOrders ? totalRevenue / totalOrders : 0;
  const pendingOrders = orders.filter(o => o.status === 'pending').length;
  const deliveredOrders = orders.filter(o => o.status === 'delivered').length;
  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
  const ordersToday = orders.filter(o => new Date(o.created_at) >= todayStart).length;

  return (
    <div className="space-y-6" data-testid="admin-orders-page">
      <SectionHeader title="Orders" subtitle={`${totalOrders} total · ${ordersToday} today`} icon={ShoppingCart} loading={loading} onRefresh={load}>
        <Button onClick={exportCSV} variant="outline" size="sm" className="h-8"><Download className="h-3.5 w-3.5 mr-1"/>Export</Button>
      </SectionHeader>

      <NeoPanel context="orders" title="Neo Orders Insight" />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <ProdStatCard label="Total Orders" value={totalOrders} icon={ShoppingCart}/>
        <ProdStatCard label="Revenue" value={fmtINR(totalRevenue)} icon={IndianRupee} color="bg-emerald-50" iconColor="text-emerald-600"/>
        <ProdStatCard label="Profit" value={fmtINR(totalProfit)} icon={TrendingUp} color="bg-blue-50" iconColor="text-blue-600"/>
        <ProdStatCard label="Avg Order" value={fmtINR(avgOrder)} icon={DollarSign} color="bg-violet-50" iconColor="text-violet-600"/>
        <ProdStatCard label="Pending" value={pendingOrders} icon={Clock} danger={pendingOrders > 5}/>
        <ProdStatCard label="Delivered" value={deliveredOrders} icon={CheckCircle2} color="bg-emerald-50" iconColor="text-emerald-600"/>
      </div>

      {/* Status Quick Filters */}
      <div className="flex flex-wrap gap-2">
        {[{ label: 'All', value: 'all', count: totalOrders },
          ...STATUSES.map(s => ({ label: s.charAt(0).toUpperCase() + s.slice(1), value: s, count: orders.filter(o => o.status === s).length }))
        ].map(f => (
          <button key={f.value} onClick={() => { setFilter(f.value); setPage(0); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === f.value ? 'bg-[var(--gs-teal)] text-white' : 'bg-[var(--gs-surface-2)] text-[var(--gs-muted)] hover:text-[var(--gs-ink)]'}`}>
            {f.label} <span className="ml-1 opacity-70">({f.count})</span>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--gs-muted)]"/>
        <Input className="pl-9" placeholder="Search by order #, customer, email..." value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}/>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[750px]">
            <thead className="text-left text-[10px] uppercase tracking-wider text-[var(--gs-muted)] bg-[var(--gs-surface-2)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold cursor-pointer select-none" onClick={() => toggleSort('order_number')}><div className="flex items-center gap-1">Order <SortIcon k="order_number"/></div></th>
                <th className="px-4 py-2.5 font-semibold">Customer</th>
                <th className="px-4 py-2.5 font-semibold hidden md:table-cell">Items</th>
                <th className="px-4 py-2.5 font-semibold cursor-pointer select-none" onClick={() => toggleSort('total')}><div className="flex items-center gap-1">Total <SortIcon k="total"/></div></th>
                <th className="px-4 py-2.5 font-semibold hidden md:table-cell">Profit</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold w-32">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((o) => (
                <tr key={o.id} className="border-t hover:bg-[var(--gs-surface-2)]/50 transition-colors" style={{ borderColor: "var(--gs-border)" }} data-testid={`admin-order-row-${o.order_number}`}>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-xs">{o.order_number}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{o.created_at ? new Date(o.created_at).toLocaleDateString('en-IN') : '—'}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs font-medium">{o.customer_name}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{o.customer_email}</div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <Badge variant="outline" className="text-[10px]">{o.items?.length || 0} items</Badge>
                  </td>
                  <td className="px-4 py-3 font-semibold text-xs">{fmtINR(o.total)}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-[var(--gs-teal)] font-semibold text-xs">{fmtINR(o.profit)}</td>
                  <td className="px-4 py-3"><StatusBadge status={o.status}/></td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setSelectedOrder(o)}><Eye className="h-3 w-3 mr-1"/>View</Button>
                      <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => openEdit(o)} data-testid={`admin-order-update-${o.order_number}`}>Update</Button>
                    </div>
                  </td>
                </tr>
              ))}
              {paged.length === 0 && (
                <tr><td colSpan={7} className="py-12 text-center text-[var(--gs-muted)] text-sm">No orders match filters</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-2 border-t text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>
            <span>{filtered.length} orders</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</Button>
              <span>{page + 1} / {totalPages}</span>
              <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Card>

      {/* Update Dialog */}
      <Dialog open={!!editOrder} onOpenChange={(o) => !o && setEditOrder(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Update {editOrder?.order_number}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Status</label>
              <Select value={status} onValueChange={setStatus}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>)}</SelectContent></Select>
            </div>
            <div>
              <label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Tracking Number</label>
              <Input placeholder="Optional" value={tracking} onChange={(e) => setTracking(e.target.value)} data-testid="admin-order-tracking-input"/>
            </div>
            {/* Status Timeline */}
            <div className="flex items-center gap-1 pt-2">
              {STATUSES.map((s, i) => (
                <div key={s} className="flex items-center gap-1 flex-1">
                  <div className={`h-2 flex-1 rounded ${STATUSES.indexOf(status) >= i ? 'bg-[var(--gs-teal)]' : 'bg-gray-200'}`}/>
                </div>
              ))}
            </div>
            <div className="flex justify-between text-[9px] text-[var(--gs-muted)] px-1">
              {STATUSES.map(s => <span key={s} className="capitalize">{s}</span>)}
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setEditOrder(null)}>Cancel</Button><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" onClick={save} data-testid="admin-order-save-button">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Order Dialog */}
      <Dialog open={!!selectedOrder} onOpenChange={(o) => !o && setSelectedOrder(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Order {selectedOrder?.order_number}</DialogTitle></DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-[var(--gs-muted)]">Customer:</span><div className="font-semibold">{selectedOrder.customer_name}</div></div>
                <div><span className="text-[var(--gs-muted)]">Email:</span><div className="font-semibold">{selectedOrder.customer_email}</div></div>
                <div><span className="text-[var(--gs-muted)]">Date:</span><div className="font-semibold">{selectedOrder.created_at ? new Date(selectedOrder.created_at).toLocaleString('en-IN') : '—'}</div></div>
                <div><span className="text-[var(--gs-muted)]">Status:</span><div><StatusBadge status={selectedOrder.status}/></div></div>
              </div>
              <div className="border-t pt-3" style={{ borderColor: "var(--gs-border)" }}>
                <div className="text-[10px] text-[var(--gs-muted)] uppercase tracking-wider font-semibold mb-2">Items</div>
                {selectedOrder.items?.map((item, i) => (
                  <div key={i} className="flex justify-between py-1.5 text-xs border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
                    <span>{item.name} × {item.quantity}</span>
                    <span className="font-semibold">{fmtINR(item.line_total || item.price * item.quantity)}</span>
                  </div>
                ))}
              </div>
              <div className="border-t pt-3 flex justify-between" style={{ borderColor: "var(--gs-border)" }}>
                <div className="text-xs text-[var(--gs-muted)]">Total</div>
                <div className="font-bold">{fmtINR(selectedOrder.total)}</div>
              </div>
              {selectedOrder.tracking_number && (
                <div className="text-xs"><span className="text-[var(--gs-muted)]">Tracking: </span><span className="font-semibold">{selectedOrder.tracking_number}</span></div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedOrder(null)}>Close</Button>
            <Button variant="outline" onClick={() => { setSelectedOrder(null); openEdit(selectedOrder); }}>Edit Status</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
