import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Users, Plus, Trash2, RefreshCw, Loader2, Copy, TrendingUp, DollarSign, MousePointer, ShoppingCart } from "lucide-react";
import { toast } from "sonner";

const EMPTY = { name:"", email:"", commission_rate:"10" };

export default function Affiliates() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get("/admin/affiliates"); setItems(r.data.items||[]); }
    catch { toast.error("Load failed"); } finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const create = async()=>{
    if (!form.name||!form.email) return toast.error("Name aur email chahiye");
    setCreating(true);
    try {
      await api.post("/admin/affiliates",{...form,commission_rate:parseFloat(form.commission_rate)||10});
      toast.success("Affiliate added!"); setShowNew(false); setForm(EMPTY); await load();
    } catch { toast.error("Error"); } finally { setCreating(false); }
  };

  const toggle = async(item)=>{
    try { await api.put(`/admin/affiliates/${item.id}`,{status:item.status==="active"?"paused":"active"}); await load(); } catch { toast.error("Error"); }
  };

  const del = async(item)=>{
    if (!window.confirm(`"${item.name}" delete karein?`)) return;
    try { await api.delete(`/admin/affiliates/${item.id}`); toast.success("Deleted"); await load(); } catch { toast.error("Error"); }
  };

  const copy = (code)=>{ navigator.clipboard?.writeText(code); toast.success("Referral code copied!"); };

  const totalEarnings = items.reduce((s,i)=>s+(i.earnings||0),0);
  const totalConversions = items.reduce((s,i)=>s+(i.conversions||0),0);
  const totalClicks = items.reduce((s,i)=>s+(i.clicks||0),0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Users className="h-7 w-7 text-[var(--gs-teal)]"/>Affiliates</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{items.filter(i=>i.status==="active").length} active affiliates</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1"/>Add Affiliate</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[[<TrendingUp className="h-5 w-5 text-blue-500"/>,"Total Clicks",totalClicks],[<ShoppingCart className="h-5 w-5 text-emerald-500"/>,"Conversions",totalConversions],[<DollarSign className="h-5 w-5 text-amber-500"/>,"Total Earnings",`₹${totalEarnings.toFixed(2)}`]].map(([ic,k,v],i)=>(
          <Card key={i} className="p-4 flex items-center gap-3">{ic}<div><p className="text-[10px] text-[var(--gs-muted)]">{k}</p><p className="text-xl font-bold">{v}</p></div></Card>
        ))}
      </div>

      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-muted)]"/></div> : (
        <div className="space-y-3">
          {items.length===0 ? (
            <Card className="p-12 text-center"><Users className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/><p className="text-sm text-[var(--gs-muted)]">Koi affiliates nahi — pehla add karo</p></Card>
          ) : items.map(a=>(
            <Card key={a.id} className="p-4">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-[var(--gs-teal)] to-purple-500 grid place-items-center text-white font-bold text-sm flex-shrink-0">
                  {(a.name||"A")[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{a.name}</span>
                    <Badge className={`text-[10px] ${a.status==="active"?"bg-emerald-100 text-emerald-700":"bg-gray-100 text-gray-500"}`}>{a.status}</Badge>
                  </div>
                  <p className="text-xs text-[var(--gs-muted)]">{a.email}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <code className="text-xs font-mono bg-[var(--gs-surface-2)] px-2 py-0.5 rounded">{a.code}</code>
                    <button onClick={()=>copy(a.code)} className="text-[var(--gs-muted)] hover:text-[var(--gs-teal)]"><Copy className="h-3 w-3"/></button>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div><p className="text-[10px] text-[var(--gs-muted)]">Commission</p><p className="text-sm font-bold text-[var(--gs-teal)]">{a.commission_rate}%</p></div>
                  <div><p className="text-[10px] text-[var(--gs-muted)]">Clicks</p><p className="text-sm font-bold">{a.clicks||0}</p></div>
                  <div><p className="text-[10px] text-[var(--gs-muted)]">Conversions</p><p className="text-sm font-bold">{a.conversions||0}</p></div>
                </div>
                <div className="text-center">
                  <p className="text-[10px] text-[var(--gs-muted)]">Earnings</p>
                  <p className="text-sm font-bold text-emerald-600">₹{(a.earnings||0).toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={a.status==="active"} onCheckedChange={()=>toggle(a)}/>
                  <button onClick={()=>del(a)} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-4 w-4"/></button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-display">Add Affiliate</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><label className="text-xs font-medium mb-1 block">Full Name *</label>
              <Input className="h-9 text-sm" placeholder="Priya Sharma" value={form.name} onChange={e=>setForm(p=>({...p,name:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Email *</label>
              <Input type="email" className="h-9 text-sm" placeholder="priya@example.com" value={form.email} onChange={e=>setForm(p=>({...p,email:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Commission Rate (%)</label>
              <Input type="number" min="1" max="50" className="h-9 text-sm" value={form.commission_rate} onChange={e=>setForm(p=>({...p,commission_rate:e.target.value}))}/>
              <p className="text-[10px] text-[var(--gs-muted)] mt-1">Har sale pe yeh % commission milega</p></div>
            <Button className="w-full bg-[var(--gs-teal)]" onClick={create} disabled={creating}>
              {creating?<Loader2 className="h-4 w-4 animate-spin mr-2"/>:<Plus className="h-4 w-4 mr-2"/>}Add Affiliate
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
