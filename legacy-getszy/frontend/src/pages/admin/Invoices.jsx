import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { FileText, Plus, RefreshCw, Loader2, Eye, CheckCircle2, Clock, XCircle, Printer } from "lucide-react";
import { toast } from "sonner";

const STATUS_BADGE = {
  issued: "bg-blue-100 text-blue-700",
  paid: "bg-emerald-100 text-emerald-700",
  overdue: "bg-rose-100 text-rose-700",
  cancelled: "bg-gray-100 text-gray-500",
};

const EMPTY = { customer_name:"", customer_email:"", customer_gstin:"", subtotal:"", gst_rate:"18", notes:"", items:[] };

export default function Invoices() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [viewInvoice, setViewInvoice] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [lineItems, setLineItems] = useState([{ description:"", qty:1, rate:"" }]);

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get("/admin/invoices"); setItems(r.data.items||[]); }
    catch { toast.error("Load failed"); } finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const addLine = ()=>setLineItems(p=>[...p,{description:"",qty:1,rate:""}]);
  const updLine = (i,k,v)=>setLineItems(p=>p.map((l,idx)=>idx===i?{...l,[k]:v}:l));
  const delLine = (i)=>setLineItems(p=>p.filter((_,idx)=>idx!==i));

  const create = async()=>{
    if (!form.customer_name||!form.subtotal) return toast.error("Customer name aur subtotal chahiye");
    setCreating(true);
    try {
      const items_list = lineItems.filter(l=>l.description&&l.rate).map(l=>({...l,qty:parseInt(l.qty)||1,rate:parseFloat(l.rate)||0,amount:(parseInt(l.qty)||1)*(parseFloat(l.rate)||0)}));
      await api.post("/admin/invoices/generate",{...form,subtotal:parseFloat(form.subtotal),gst_rate:parseFloat(form.gst_rate)||18,items:items_list});
      toast.success("Invoice generated!"); setShowNew(false); setForm(EMPTY); setLineItems([{description:"",qty:1,rate:""}]); await load();
    } catch { toast.error("Error"); } finally { setCreating(false); }
  };

  const updateStatus = async(iid,status)=>{
    try { await api.put(`/admin/invoices/${iid}`,{status}); await load(); toast.success("Updated"); } catch { toast.error("Error"); }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><FileText className="h-7 w-7 text-[var(--gs-teal)]"/>Invoices</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">GST invoices · {items.length} total</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1"/>New Invoice</Button>
        </div>
      </div>

      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-muted)]"/></div> : (
        <div className="space-y-2">
          {items.length===0 ? (
            <Card className="p-12 text-center"><FileText className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/><p className="text-sm text-[var(--gs-muted)]">Koi invoices nahi — pehla banao</p></Card>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-[var(--gs-muted)] border-b border-[var(--gs-border)]">
                  <th className="text-left py-2 pr-4">Invoice #</th>
                  <th className="text-left py-2 pr-4">Customer</th>
                  <th className="text-right py-2 pr-4">Subtotal</th>
                  <th className="text-right py-2 pr-4">GST ({'{'}items[0]?.gst_rate||18{'}'}%)</th>
                  <th className="text-right py-2 pr-4">Total</th>
                  <th className="text-left py-2 pr-4">Status</th>
                  <th className="text-left py-2 pr-4">Date</th>
                  <th className="py-2">Actions</th>
                </tr></thead>
                <tbody>{items.map(inv=>(
                  <tr key={inv.id} className="border-b border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]">
                    <td className="py-2.5 pr-4 font-mono font-semibold text-[var(--gs-teal)]">{inv.invoice_number}</td>
                    <td className="py-2.5 pr-4"><p className="font-medium">{inv.customer_name}</p><p className="text-[var(--gs-muted)]">{inv.customer_email}</p></td>
                    <td className="py-2.5 pr-4 text-right">₹{inv.subtotal?.toFixed(2)}</td>
                    <td className="py-2.5 pr-4 text-right text-emerald-600">₹{inv.gst_amount?.toFixed(2)}</td>
                    <td className="py-2.5 pr-4 text-right font-bold">₹{inv.total?.toFixed(2)}</td>
                    <td className="py-2.5 pr-4">
                      <Badge className={`text-[10px] ${STATUS_BADGE[inv.status]||""}`}>{inv.status}</Badge>
                    </td>
                    <td className="py-2.5 pr-4 text-[var(--gs-muted)]">{inv.created_at?new Date(inv.created_at).toLocaleDateString("en-IN"):""}</td>
                    <td className="py-2.5">
                      <div className="flex gap-1">
                        <button onClick={()=>setViewInvoice(inv)} className="p-1.5 rounded hover:bg-[var(--gs-surface-3)] text-[var(--gs-teal)]"><Eye className="h-3.5 w-3.5"/></button>
                        {inv.status==="issued"&&<button onClick={()=>updateStatus(inv.id,"paid")} className="p-1.5 rounded hover:bg-emerald-50 text-emerald-500"><CheckCircle2 className="h-3.5 w-3.5"/></button>}
                        {inv.status==="issued"&&<button onClick={()=>updateStatus(inv.id,"cancelled")} className="p-1.5 rounded hover:bg-rose-50 text-rose-400"><XCircle className="h-3.5 w-3.5"/></button>}
                      </div>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* New Invoice Dialog */}
      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle className="font-display">Generate Invoice</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-xs font-medium mb-1 block">Customer Name *</label>
                <Input className="h-9 text-sm" value={form.customer_name} onChange={e=>setForm(p=>({...p,customer_name:e.target.value}))}/></div>
              <div><label className="text-xs font-medium mb-1 block">Email</label>
                <Input type="email" className="h-9 text-sm" value={form.customer_email} onChange={e=>setForm(p=>({...p,customer_email:e.target.value}))}/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Customer GSTIN</label>
              <Input className="h-9 text-sm font-mono" placeholder="22AAAAA0000A1Z5" value={form.customer_gstin} onChange={e=>setForm(p=>({...p,customer_gstin:e.target.value}))}/></div>
            <div>
              <div className="flex items-center justify-between mb-1"><label className="text-xs font-medium">Line Items</label>
                <button onClick={addLine} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Plus className="h-3 w-3"/>Add Row</button></div>
              {lineItems.map((l,i)=>(
                <div key={i} className="flex gap-1.5 mb-1.5">
                  <Input className="h-8 text-xs flex-1" placeholder="Description" value={l.description} onChange={e=>updLine(i,"description",e.target.value)}/>
                  <Input type="number" className="h-8 text-xs w-14" placeholder="Qty" value={l.qty} onChange={e=>updLine(i,"qty",e.target.value)}/>
                  <Input type="number" className="h-8 text-xs w-24" placeholder="Rate ₹" value={l.rate} onChange={e=>updLine(i,"rate",e.target.value)}/>
                  <Button size="sm" variant="ghost" className="h-8 px-1.5 text-rose-400" onClick={()=>delLine(i)}>✕</Button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Subtotal ₹ *</label>
                <Input type="number" className="h-9 text-sm" value={form.subtotal} onChange={e=>setForm(p=>({...p,subtotal:e.target.value}))}/></div>
              <div className="w-24"><label className="text-xs font-medium mb-1 block">GST %</label>
                <Input type="number" className="h-9 text-sm" value={form.gst_rate} onChange={e=>setForm(p=>({...p,gst_rate:e.target.value}))}/></div>
            </div>
            {form.subtotal&&<div className="bg-[var(--gs-surface-2)] rounded-lg p-3 text-xs space-y-1">
              <div className="flex justify-between"><span>Subtotal</span><span>₹{parseFloat(form.subtotal||0).toFixed(2)}</span></div>
              <div className="flex justify-between text-emerald-600"><span>GST ({form.gst_rate}%)</span><span>₹{(parseFloat(form.subtotal||0)*parseFloat(form.gst_rate||18)/100).toFixed(2)}</span></div>
              <div className="flex justify-between font-bold border-t border-[var(--gs-border)] pt-1"><span>Total</span><span>₹{(parseFloat(form.subtotal||0)*(1+parseFloat(form.gst_rate||18)/100)).toFixed(2)}</span></div>
            </div>}
            <div><label className="text-xs font-medium mb-1 block">Notes</label>
              <Textarea className="text-xs" rows={2} value={form.notes} onChange={e=>setForm(p=>({...p,notes:e.target.value}))}/></div>
            <Button className="w-full bg-[var(--gs-teal)]" onClick={create} disabled={creating}>
              {creating?<Loader2 className="h-4 w-4 animate-spin mr-2"/>:<FileText className="h-4 w-4 mr-2"/>}Generate Invoice
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Invoice Dialog */}
      {viewInvoice && (
        <Dialog open={!!viewInvoice} onOpenChange={()=>setViewInvoice(null)}>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle className="font-display font-mono text-[var(--gs-teal)]">{viewInvoice.invoice_number}</DialogTitle></DialogHeader>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><div><p className="font-semibold">{viewInvoice.customer_name}</p><p className="text-xs text-[var(--gs-muted)]">{viewInvoice.customer_email}</p>{viewInvoice.customer_gstin&&<p className="text-xs font-mono">{viewInvoice.customer_gstin}</p>}</div>
                <div className="text-right"><Badge className={`text-xs ${STATUS_BADGE[viewInvoice.status]||""}`}>{viewInvoice.status}</Badge><p className="text-xs text-[var(--gs-muted)] mt-1">{viewInvoice.created_at?new Date(viewInvoice.created_at).toLocaleDateString("en-IN"):""}</p></div>
              </div>
              {viewInvoice.items?.length>0&&<div className="border border-[var(--gs-border)] rounded-lg overflow-hidden">
                <table className="w-full text-xs"><thead className="bg-[var(--gs-surface-2)]"><tr><th className="text-left p-2">Item</th><th className="text-right p-2">Qty</th><th className="text-right p-2">Rate</th><th className="text-right p-2">Amount</th></tr></thead>
                  <tbody>{viewInvoice.items.map((item,i)=><tr key={i} className="border-t border-[var(--gs-border)]"><td className="p-2">{item.description}</td><td className="p-2 text-right">{item.qty}</td><td className="p-2 text-right">₹{item.rate}</td><td className="p-2 text-right font-medium">₹{item.amount}</td></tr>)}</tbody>
                </table>
              </div>}
              <div className="bg-[var(--gs-surface-2)] rounded-lg p-3 space-y-1 text-xs">
                <div className="flex justify-between"><span>Subtotal</span><span>₹{viewInvoice.subtotal?.toFixed(2)}</span></div>
                <div className="flex justify-between text-emerald-600"><span>GST ({viewInvoice.gst_rate}%)</span><span>₹{viewInvoice.gst_amount?.toFixed(2)}</span></div>
                <div className="flex justify-between font-bold text-sm border-t border-[var(--gs-border)] pt-2"><span>Total</span><span>₹{viewInvoice.total?.toFixed(2)}</span></div>
              </div>
              {viewInvoice.notes&&<p className="text-xs text-[var(--gs-muted)] italic">{viewInvoice.notes}</p>}
              <div className="flex gap-2">
                {viewInvoice.status==="issued"&&<Button size="sm" className="bg-emerald-600 text-white flex-1" onClick={()=>{updateStatus(viewInvoice.id,"paid");setViewInvoice(null);}}><CheckCircle2 className="h-4 w-4 mr-1"/>Mark Paid</Button>}
                <Button size="sm" variant="outline" className="flex-1" onClick={()=>window.print()}><Printer className="h-4 w-4 mr-1"/>Print</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
