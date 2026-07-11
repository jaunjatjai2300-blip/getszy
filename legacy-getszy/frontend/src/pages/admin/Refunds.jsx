import { useState, useCallback, useEffect } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { RefreshCw, Search, IndianRupee, CheckCircle2, XCircle, Clock, AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";

const REFUND_REASONS = [
  "Product not received","Wrong product delivered","Product damaged","Duplicate order","Customer changed mind","Payment failed but charged","Quality not as expected","Other"
];

const STATUS_STYLE = {
  pending:   "bg-amber-100 text-amber-700",
  approved:  "bg-emerald-100 text-emerald-700",
  rejected:  "bg-rose-100 text-rose-700",
  processed: "bg-blue-100 text-blue-700",
};

function RefundModal({ order, onClose, onSubmit }) {
  const [amount, setAmount] = useState(order?.total||"");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const max = order?.total||0;

  const submit = async () => {
    if (!reason) { toast.error("Reason select karo"); return; }
    if (!amount || parseFloat(amount) <= 0) { toast.error("Valid amount enter karo"); return; }
    if (parseFloat(amount) > max) { toast.error(`Maximum refund ₹${max} hai`); return; }
    setLoading(true);
    try {
      await onSubmit({ order_id: order._id, amount: parseFloat(amount), reason, notes });
      onClose();
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="w-full max-w-md p-6 space-y-4" onClick={e=>e.stopPropagation()}>
        <div>
          <h2 className="font-display text-xl">Refund Process Karo</h2>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Order: {order?.order_number} · {order?.customer_name}</p>
        </div>
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm">
          <p className="font-semibold text-amber-800">Order Amount: {fmtINR(order?.total)}</p>
          <p className="text-amber-700 text-xs mt-0.5">Partial ya full refund dono ho sakti hai</p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold mb-1.5 block">Refund Amount (₹) *</label>
            <Input type="number" value={amount} onChange={e=>setAmount(e.target.value)} placeholder={`Max: ${max}`} min="1" max={max}/>
            <p className="text-[10px] text-[var(--gs-muted)] mt-1">Full refund: ₹{max} | Partial refund: koi bhi amount</p>
          </div>
          <div>
            <label className="text-xs font-semibold mb-1.5 block">Refund Reason *</label>
            <Select value={reason} onValueChange={setReason}>
              <SelectTrigger><SelectValue placeholder="Reason select karo…"/></SelectTrigger>
              <SelectContent>{REFUND_REASONS.map(r=><SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-semibold mb-1.5 block">Internal Notes (optional)</label>
            <Textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Additional details…" rows={2} className="text-xs resize-none"/>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
          <Button className="flex-1 gap-2" style={{background:"var(--gs-teal)",color:"#fff"}} onClick={submit} disabled={loading}>
            {loading?<Loader2 className="h-4 w-4 animate-spin"/>:<IndianRupee className="h-4 w-4"/>}Refund Process Karo
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function Refunds() {
  const [orders, setOrders] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [tab, setTab] = useState("eligible");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ordR, refR] = await Promise.allSettled([
        api.get("/admin/orders?status=delivered&limit=50"),
        api.get("/admin/orders/refunds").catch(()=>({ data:{ refunds:[] } })),
      ]);
      if (ordR.status==="fulfilled") setOrders(ordR.value.data?.orders||ordR.value.data||[]);
      if (refR.status==="fulfilled") setRefunds(refR.value.data?.refunds||[]);
    } finally { setLoading(false); }
  }, []);

  useEffect(()=>{load();},[load]);

  const processRefund = async ({ order_id, amount, reason, notes }) => {
    try {
      await api.post("/admin/orders/refund", { order_id, amount, reason, notes });
      toast.success(`Refund ₹${amount} process ho gaya!`);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Refund process karne mein error");
      throw e;
    }
  };

  const filteredOrders = orders.filter(o =>
    !search || o.order_number?.toLowerCase().includes(search.toLowerCase()) ||
    o.customer_name?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    totalRefunds: refunds.length,
    totalAmount: refunds.reduce((a,r)=>a+(r.refund_amount||0),0),
    pending: refunds.filter(r=>r.refund_status==="pending").length,
    processed: refunds.filter(r=>r.refund_status==="processed"||r.refund_status==="approved").length,
  };

  return (
    <div className="space-y-5">
      {selectedOrder && <RefundModal order={selectedOrder} onClose={()=>setSelectedOrder(null)} onSubmit={processRefund}/>}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><IndianRupee className="h-7 w-7 text-rose-600"/>Refund Management</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Customer refunds process karo aur track karo</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading?"animate-spin":""}`}/>Refresh</Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label:"Total Refunds",   value:stats.totalRefunds,              icon:RefreshCw,     color:"bg-blue-50",    iconColor:"text-blue-600" },
          { label:"Amount Refunded", value:fmtINR(stats.totalAmount),       icon:IndianRupee,   color:"bg-rose-50",    iconColor:"text-rose-600" },
          { label:"Pending",         value:stats.pending,                   icon:Clock,         color:"bg-amber-50",   iconColor:"text-amber-600" },
          { label:"Processed",       value:stats.processed,                 icon:CheckCircle2,  color:"bg-emerald-50", iconColor:"text-emerald-600" },
        ].map(s=>(
          <Card key={s.label} className="p-4 flex items-center gap-3">
            <div className={`h-10 w-10 rounded-xl ${s.color} grid place-items-center flex-shrink-0`}>
              <s.icon className={`h-5 w-5 ${s.iconColor}`}/>
            </div>
            <div>
              <p className="font-display text-xl leading-none">{loading?"…":s.value}</p>
              <p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex gap-2">
        <button onClick={()=>setTab("eligible")} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab==="eligible"?"bg-[var(--gs-teal)] text-white":"bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"}`}>Eligible Orders</button>
        <button onClick={()=>setTab("history")} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab==="history"?"bg-[var(--gs-teal)] text-white":"bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"}`}>Refund History ({refunds.length})</button>
      </div>

      {tab==="eligible" && (
        <>
          <div className="relative max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]"/>
            <Input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Order ya customer search…" className="pl-9 h-9"/>
          </div>
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[var(--gs-surface-2)] text-[10px] uppercase tracking-wider">
                  <tr>{["Order","Customer","Date","Amount","Status","Action"].map(h=><th key={h} className="text-left py-3 px-4 font-semibold text-[var(--gs-muted)]">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={6} className="text-center py-12 text-[var(--gs-muted)]"><Loader2 className="h-6 w-6 animate-spin mx-auto"/></td></tr>
                  ) : filteredOrders.length===0 ? (
                    <tr><td colSpan={6} className="text-center py-12 text-[var(--gs-muted)]">Koi refund-eligible orders nahi hain</td></tr>
                  ) : filteredOrders.map(o=>(
                    <tr key={o._id} className="border-t hover:bg-[var(--gs-surface-2)] transition-colors">
                      <td className="py-3 px-4 font-mono text-xs font-semibold">{o.order_number}</td>
                      <td className="py-3 px-4">{o.customer_name}</td>
                      <td className="py-3 px-4 text-[var(--gs-muted)] text-xs">{o.created_at?new Date(o.created_at).toLocaleDateString("en-IN"):"—"}</td>
                      <td className="py-3 px-4 font-semibold">{fmtINR(o.total)}</td>
                      <td className="py-3 px-4"><Badge className="text-[10px] capitalize">{o.status}</Badge></td>
                      <td className="py-3 px-4">
                        <Button size="sm" variant="outline" className="h-7 text-xs gap-1 text-rose-600 border-rose-200 hover:bg-rose-50" onClick={()=>setSelectedOrder(o)}>
                          <IndianRupee className="h-3 w-3"/>Refund
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {tab==="history" && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[var(--gs-surface-2)] text-[10px] uppercase tracking-wider">
                <tr>{["Order","Customer","Refund Amount","Reason","Status","Date"].map(h=><th key={h} className="text-left py-3 px-4 font-semibold text-[var(--gs-muted)]">{h}</th>)}</tr>
              </thead>
              <tbody>
                {refunds.length===0 ? (
                  <tr><td colSpan={6} className="text-center py-12 text-[var(--gs-muted)]">Abhi koi refunds process nahi hue</td></tr>
                ) : refunds.map((r,i)=>(
                  <tr key={r._id||i} className="border-t hover:bg-[var(--gs-surface-2)]">
                    <td className="py-3 px-4 font-mono text-xs">{r.order_number||"—"}</td>
                    <td className="py-3 px-4">{r.customer_name||"—"}</td>
                    <td className="py-3 px-4 font-semibold text-rose-600">{fmtINR(r.refund_amount)}</td>
                    <td className="py-3 px-4 text-xs text-[var(--gs-muted)]">{r.reason||"—"}</td>
                    <td className="py-3 px-4"><Badge className={`text-[10px] ${STATUS_STYLE[r.refund_status]||"bg-slate-100 text-slate-600"}`}>{r.refund_status||"pending"}</Badge></td>
                    <td className="py-3 px-4 text-xs text-[var(--gs-muted)]">{r.refunded_at?new Date(r.refunded_at).toLocaleDateString("en-IN"):"—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
