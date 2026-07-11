import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Crown, Plus, Trash2, RefreshCw, Loader2, Check, Edit2, Save, X } from "lucide-react";
import { toast } from "sonner";

const COLORS = ["#6366f1","#0ea5e9","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899"];
const EMPTY = { name:"", price_monthly:"", price_yearly:"", description:"", features:"", color:"#6366f1", badge:"" };

export default function Memberships() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get("/admin/memberships"); setItems(r.data.items||[]); }
    catch { toast.error("Load failed"); } finally { setLoading(false); }
  },[]);
  useEffect(()=>{ load(); },[load]);

  const create = async()=>{
    if (!form.name||!form.price_monthly) return toast.error("Name aur price chahiye");
    setCreating(true);
    try {
      await api.post("/admin/memberships",{
        ...form,
        price_monthly:parseFloat(form.price_monthly),
        price_yearly:parseFloat(form.price_yearly)||0,
        features:form.features.split("\n").map(f=>f.trim()).filter(Boolean)
      });
      toast.success("Membership plan created!"); setShowNew(false); setForm(EMPTY); await load();
    } catch { toast.error("Error"); } finally { setCreating(false); }
  };

  const saveEdit = async(id)=>{
    try {
      const upd = {...editForm};
      if (typeof upd.features==="string") upd.features=upd.features.split("\n").map(f=>f.trim()).filter(Boolean);
      await api.put(`/admin/memberships/${id}`,upd);
      setEditing(null); toast.success("Updated"); await load();
    } catch { toast.error("Error"); }
  };

  const toggle = async(item)=>{
    try { await api.put(`/admin/memberships/${item.id}`,{active:!item.active}); await load(); } catch { toast.error("Error"); }
  };

  const del = async(item)=>{
    if (!window.confirm(`"${item.name}" delete karein?`)) return;
    try { await api.delete(`/admin/memberships/${item.id}`); toast.success("Deleted"); await load(); } catch { toast.error("Error"); }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Crown className="h-7 w-7 text-[var(--gs-teal)]"/>Memberships</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{items.length} plans · {items.reduce((s,i)=>s+(i.member_count||0),0)} total members</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1"/>New Plan</Button>
        </div>
      </div>

      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-muted)]"/></div> : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.length===0 ? (
            <div className="col-span-full"><Card className="p-12 text-center"><Crown className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/><p className="text-sm text-[var(--gs-muted)]">Koi plans nahi — pehla banao</p></Card></div>
          ) : items.map(m=>(
            <Card key={m.id} className="overflow-hidden">
              <div className="h-2" style={{background:m.color||"#6366f1"}}/>
              <div className="p-5 space-y-4">
                {editing===m.id ? (
                  <div className="space-y-2">
                    <Input className="h-8 text-sm font-bold" value={editForm.name||""} onChange={e=>setEditForm(p=>({...p,name:e.target.value}))}/>
                    <div className="flex gap-2">
                      <Input type="number" className="h-8 text-xs" placeholder="Monthly ₹" value={editForm.price_monthly||""} onChange={e=>setEditForm(p=>({...p,price_monthly:e.target.value}))}/>
                      <Input type="number" className="h-8 text-xs" placeholder="Yearly ₹" value={editForm.price_yearly||""} onChange={e=>setEditForm(p=>({...p,price_yearly:e.target.value}))}/>
                    </div>
                    <Textarea className="text-xs" rows={3} placeholder="Features (one per line)" value={typeof editForm.features==="string"?editForm.features:(editForm.features||[]).join("\n")} onChange={e=>setEditForm(p=>({...p,features:e.target.value}))}/>
                    <div className="flex gap-2">
                      <Button size="sm" className="flex-1 bg-[var(--gs-teal)] h-7" onClick={()=>saveEdit(m.id)}><Save className="h-3 w-3 mr-1"/>Save</Button>
                      <Button size="sm" variant="outline" className="h-7" onClick={()=>setEditing(null)}><X className="h-3 w-3"/></Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-base">{m.name}</h3>
                          {m.badge&&<Badge className="text-[10px]" style={{background:m.color}}>{m.badge}</Badge>}
                        </div>
                        <div className="mt-1">
                          <span className="text-2xl font-extrabold">₹{m.price_monthly}</span>
                          <span className="text-xs text-[var(--gs-muted)]">/month</span>
                          {m.price_yearly>0&&<p className="text-xs text-emerald-600 mt-0.5">₹{m.price_yearly}/year (save {Math.round((1-m.price_yearly/(m.price_monthly*12))*100)}%)</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Switch checked={!!m.active} onCheckedChange={()=>toggle(m)}/>
                        <button onClick={()=>{setEditing(m.id);setEditForm({...m,features:(m.features||[]).join("\n")});}} className="p-1.5 rounded hover:bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"><Edit2 className="h-3.5 w-3.5"/></button>
                        <button onClick={()=>del(m)} className="p-1.5 rounded hover:bg-rose-50 text-rose-400"><Trash2 className="h-3.5 w-3.5"/></button>
                      </div>
                    </div>
                    {m.description&&<p className="text-xs text-[var(--gs-muted)]">{m.description}</p>}
                    <ul className="space-y-1.5">
                      {(m.features||[]).map((f,i)=>(
                        <li key={i} className="flex items-start gap-2 text-xs">
                          <Check className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0 mt-0.5"/>
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="flex items-center justify-between pt-2 border-t border-[var(--gs-border)]">
                      <span className="text-xs text-[var(--gs-muted)]">{m.member_count||0} members</span>
                      {!m.active&&<Badge variant="outline" className="text-[10px] text-gray-400">Inactive</Badge>}
                    </div>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showNew} onOpenChange={setShowNew}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle className="font-display">New Membership Plan</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><label className="text-xs font-medium mb-1 block">Plan Name *</label>
              <Input className="h-9 text-sm" placeholder="Gold, Silver, Diamond…" value={form.name} onChange={e=>setForm(p=>({...p,name:e.target.value}))}/></div>
            <div className="flex gap-2">
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Monthly Price (₹) *</label>
                <Input type="number" className="h-9 text-sm" placeholder="499" value={form.price_monthly} onChange={e=>setForm(p=>({...p,price_monthly:e.target.value}))}/></div>
              <div className="flex-1"><label className="text-xs font-medium mb-1 block">Yearly Price (₹)</label>
                <Input type="number" className="h-9 text-sm" placeholder="4999" value={form.price_yearly} onChange={e=>setForm(p=>({...p,price_yearly:e.target.value}))}/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Description</label>
              <Input className="h-9 text-sm" value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Features (ek per line)</label>
              <Textarea className="text-xs" rows={4} placeholder={"Unlimited AI credits\n24/7 support\nPriority processing"} value={form.features} onChange={e=>setForm(p=>({...p,features:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Badge Label</label>
              <Input className="h-9 text-sm" placeholder="Most Popular, Best Value…" value={form.badge} onChange={e=>setForm(p=>({...p,badge:e.target.value}))}/></div>
            <div><label className="text-xs font-medium mb-1 block">Color</label>
              <div className="flex gap-2">{COLORS.map(c=><button key={c} onClick={()=>setForm(p=>({...p,color:c}))} className={`h-6 w-6 rounded-full ${form.color===c?"ring-2 ring-offset-1 ring-gray-400":""}`} style={{background:c}}/> )}</div></div>
            <Button className="w-full bg-[var(--gs-teal)]" onClick={create} disabled={creating}>
              {creating?<Loader2 className="h-4 w-4 animate-spin mr-2"/>:<Plus className="h-4 w-4 mr-2"/>}Create Plan
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
