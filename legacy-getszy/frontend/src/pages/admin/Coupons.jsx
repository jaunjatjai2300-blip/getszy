import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Tag, Plus, Trash2, RefreshCw, Loader2, Copy, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { toast } from "sonner";

const EMPTY = { code:"", discount_type:"percent", value:"", min_order:"0", max_uses:"0", expires_at:"", description:"" };

export default function Coupons() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get("/admin/coupons"); setItems(r.data.items||[]); }
    catch { toast.error("Load failed"); } finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const create = async()=>{
    if (!form.code||!form.value) return toast.error("Code aur value chahiye");
    setCreating(true);
    try {
      await api.post("/admin/coupons",{...form, value:parseFloat(form.value), min_order:parseFloat(form.min_order)||0, max_uses:parseInt(form.max_uses)||0});
      toast.success("Coupon created!"); setShowNew(false); setForm(EMPTY); await load();
    } catch(e) { toast.error(e?.response?.data?.detail||"Error"); } finally { setCreating(false); }
  };

  const toggle = async(item)=>{
    try { await api.put(`/admin/coupons/${item.id}`,{active:!item.active}); await load(); } catch { toast.error("Error"); }
  };

  const del = async(item)=>{
    if (!window.confirm(`"${item.code}" delete karein?`)) return;
    try { await api.delete(`/admin/coupons/${item.id}`); toast.success("Deleted"); await load(); } catch { toast.error("Error"); }
  };

  const copy = (code)=>{ navigator.clipboard?.writeText(code); toast.success("Copied!"); };

  const isExpired = (e)=> e && new Date(e)<new Date();
  const filtered = items.filter(i=>!search||(i.code||"").toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Tag className="h-7 w-7 text-[var(--gs-teal)]"/>Coupons</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{items.filter(i=>i.active).length} active · {items.length} total</p>
        </div>
        <div className="flex gap-2">
          <Input className="h-9 w-44 text-xs" placeholder="Search code…" value={search} onChange={e=>setSearch(e.target.value)}/>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1"/>New Coupon</Button>
        </div>
      </div>

      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-muted)]"/></div> : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.length===0 ? (
            <div className="col-span-full">
              <Card className="p-12 text-center"><Tag className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/>
                <p className="text-sm text-[var(--gs-muted)]">Koi coupons nahi — naya banao</p></Card>
            </div>
          ) : filtered.map(c=>(
            <Card key={c.id} className="p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <code className="font-mono font-bold text-sm text-[var(--gs-teal)]">{c.code}</code>
                  <button onClick={()=>copy(c.code)} className="text-[var(--gs-muted)] hover:text-[var(--gs-teal)]"><Copy className="h-3.5 w-3.5"/></button>
                </div>
                <Switch checked={!!c.active} onCheckedChange={()=>toggle(c)}/>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="text-sm font-bold bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">
                  {c.discount_type==="percent"?`${c.value}% OFF`:`₹${c.value} OFF`}
                </Badge>
                {!c.active&&<Badge variant="outline" className="text-[10px] text-gray-400">Inactive</Badge>}
                {isExpired(c.expires_at)&&<Badge className="text-[10px] bg-rose-100 text-rose-600">Expired</Badge>}
              </div>
              <div className="text-xs text-[var(--gs-muted)] space-y-1">
                {c.min_order>0&&<p>Min order: ₹{c.min_order}</p>}
                <p className="flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3 text-emerald-500"/>
                  {c.uses||0}{c.max_uses>0?` / ${c.max_uses}`:" (unlimited)"} uses
                </p>
                {c.expires_at&&<p className="flex items-center gap-1"><Clock className="h-3 w-3"/>Expires: {new Date(c.expires_at).toLocaleDateString("en-IN")}</p>}
                {c.description&&<p className="italic">{c.description}</p>}
              </div>
              <Button size="sm" variant="ghost" className="h-7 text-rose-500 hover:text-rose-700 w-full" onClick={()=>del(c)}>
                <Trash2 className="h-3.5 w-3.5 mr-1"/>Delete
              </Button>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-display">New Coupon</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><label className="text-xs font-medium mb-1 block">Coupon Code *</label>
              <Input className="h-9 text-sm font-mono uppercase" placeholder="SAVE20" value={form.code} onChange={e=>setForm(p=>({...p,code:e.target.value.toUpperCase()}))} /></div>
            <div className="flex gap-2">
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Type</label>
                <Select value={form.discount_type} onValueChange={v=>setForm(p=>({...p,discount_type:v}))}>
                  <SelectTrigger className="h-9 text-xs"><SelectValue/></SelectTrigger>
                  <SelectContent><SelectItem value="percent" className="text-xs">Percent (%)</SelectItem><SelectItem value="fixed" className="text-xs">Fixed (₹)</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Value *</label>
                <Input type="number" min="0" className="h-9 text-sm" placeholder={form.discount_type==="percent"?"20":"100"} value={form.value} onChange={e=>setForm(p=>({...p,value:e.target.value}))}/></div>
            </div>
            <div className="flex gap-2">
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Min Order (₹)</label>
                <Input type="number" min="0" className="h-9 text-sm" value={form.min_order} onChange={e=>setForm(p=>({...p,min_order:e.target.value}))}/></div>
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Max Uses (0=unlimited)</label>
                <Input type="number" min="0" className="h-9 text-sm" value={form.max_uses} onChange={e=>setForm(p=>({...p,max_uses:e.target.value}))}/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Expires At (optional)</label>
              <Input type="datetime-local" className="h-9 text-xs" value={form.expires_at} onChange={e=>setForm(p=>({...p,expires_at:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Description</label>
              <Input className="h-9 text-sm" placeholder="Diwali special offer" value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))}/></div>
            <Button className="w-full bg-[var(--gs-teal)]" onClick={create} disabled={creating}>
              {creating?<Loader2 className="h-4 w-4 animate-spin mr-2"/>:<Plus className="h-4 w-4 mr-2"/>}Create Coupon
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
