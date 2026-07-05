import { useEffect, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const STATUSES = ["pending", "forwarded", "shipped", "delivered", "cancelled"];
const STATUS_COLORS = { pending: "bg-amber-100 text-amber-800", forwarded: "bg-sky-100 text-sky-800", shipped: "bg-blue-100 text-blue-800", delivered: "bg-emerald-100 text-emerald-800", cancelled: "bg-rose-100 text-rose-800" };

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("all");
  const [editOrder, setEditOrder] = useState(null);
  const [status, setStatus] = useState("pending");
  const [tracking, setTracking] = useState("");

  const load = async () => { const { data } = await api.get("/admin/orders"); setOrders(data); };
  useEffect(() => { load(); }, []);

  const filtered = orders.filter((o) => filter === "all" || o.status === filter);

  const openEdit = (o) => { setEditOrder(o); setStatus(o.status); setTracking(o.tracking_number || ""); };
  const save = async () => {
    await api.put(`/admin/orders/${editOrder.id}/status`, { status, tracking_number: tracking || null });
    toast.success("Order updated"); setEditOrder(null); await load();
  };

  return (
    <div data-testid="admin-orders-page">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div><h1 className="font-display text-3xl">Orders</h1><p className="text-sm text-[var(--gs-muted)]">{filtered.length} orders</p></div>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-44" data-testid="admin-orders-status-filter"><SelectValue/></SelectTrigger>
          <SelectContent><SelectItem value="all">All</SelectItem>{STATUSES.map((s) => <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="gs-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wider text-[var(--gs-muted)] border-b" style={{ borderColor: "var(--gs-border)" }}><tr><th className="p-4">Order</th><th className="p-4">Customer</th><th className="p-4 hidden md:table-cell">Items</th><th className="p-4">Total</th><th className="p-4">Profit</th><th className="p-4">Status</th><th className="p-4 w-20"></th></tr></thead>
          <tbody>{filtered.map((o) => (
            <tr key={o.id} className="border-b last:border-0" style={{ borderColor: "var(--gs-border)" }} data-testid={`admin-order-row-${o.order_number}`}>
              <td className="p-4"><div className="font-semibold">{o.order_number}</div><div className="text-xs text-[var(--gs-muted)]">{new Date(o.created_at).toLocaleDateString()}</div></td>
              <td className="p-4"><div>{o.customer_name}</div><div className="text-xs text-[var(--gs-muted)]">{o.customer_email}</div></td>
              <td className="p-4 hidden md:table-cell">{o.items.length}</td>
              <td className="p-4 font-semibold">{fmtINR(o.total)}</td>
              <td className="p-4 text-[var(--gs-teal)] font-semibold">{fmtINR(o.profit)}</td>
              <td className="p-4"><Badge className={`${STATUS_COLORS[o.status]} capitalize hover:opacity-100`}>{o.status}</Badge></td>
              <td className="p-4"><Button size="sm" variant="outline" onClick={() => openEdit(o)} data-testid={`admin-order-update-${o.order_number}`}>Update</Button></td>
            </tr>
          ))}{filtered.length === 0 && <tr><td colSpan={7} className="text-center py-10 text-[var(--gs-muted)]">No orders</td></tr>}</tbody>
        </table>
      </div>
      <Dialog open={!!editOrder} onOpenChange={(o) => !o && setEditOrder(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Update order {editOrder?.order_number}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Select value={status} onValueChange={setStatus}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>)}</SelectContent></Select>
            <Input placeholder="Tracking number (optional)" value={tracking} onChange={(e) => setTracking(e.target.value)} data-testid="admin-order-tracking-input"/>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setEditOrder(null)}>Cancel</Button><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" onClick={save} data-testid="admin-order-save-button">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
