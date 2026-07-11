import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Brain, Plus, Trash2, Search, Users, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const CATEGORIES = ["general","user-prefs","context","facts","instructions","persona","history"];
const BLANK = { key:"", value:"", category:"general", user_id:"system", ttl_days:0 };

export default function AIMemory() {
  const [memories, setMemories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(BLANK);
  const [userFilter, setUserFilter] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [search, setSearch] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [mr, sr] = await Promise.allSettled([
        api.get(`/admin/ai-platform/memory?user_id=${userFilter}&category=${catFilter}&limit=100`),
        api.get("/admin/ai-platform/memory/stats"),
      ]);
      if (mr.status==="fulfilled") setMemories(mr.value.data);
      if (sr.status==="fulfilled") setStats(sr.value.data);
    } catch { toast.error("Load failed"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [userFilter, catFilter]);

  const save = async () => {
    if (!form.key || !form.value) return toast.error("Key aur value required");
    try {
      await api.post("/admin/ai-platform/memory", form);
      toast.success("Memory saved!");
      setOpen(false); load();
    } catch { toast.error("Save failed"); }
  };

  const del = async (id) => {
    await api.delete(`/admin/ai-platform/memory/${id}`);
    toast.success("Deleted"); load();
  };

  const clearAll = async () => {
    if (!window.confirm("Sari memories clear karein? Ye wapis nahi aayengi.")) return;
    await api.delete(`/admin/ai-platform/memory?user_id=${userFilter}&category=${catFilter}`);
    toast.success("Cleared!"); load();
  };

  const filtered = search
    ? memories.filter(m => (m.key+m.value+m.user_id).toLowerCase().includes(search.toLowerCase()))
    : memories;

  const CAT_COLORS = { general:"bg-slate-100 text-slate-700", "user-prefs":"bg-blue-100 text-blue-700", context:"bg-teal-100 text-teal-700", facts:"bg-amber-100 text-amber-700", instructions:"bg-purple-100 text-purple-700", persona:"bg-pink-100 text-pink-700", history:"bg-green-100 text-green-700" };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Brain className="h-7 w-7 text-[var(--gs-teal)]"/>AI Memory</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">AI context store — users ke baare mein AI kya yaad rakhta hai</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="text-rose-600 border-rose-200" onClick={clearAll} disabled={memories.length===0}>
            <Trash2 className="h-4 w-4 mr-1.5"/>Clear Filtered
          </Button>
          <Button onClick={()=>{ setForm(BLANK); setOpen(true); }} style={{background:"var(--gs-teal)"}} className="text-white">
            <Plus className="h-4 w-4 mr-1.5"/>Add Memory
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label:"Total Entries", value:stats.total, color:"text-[var(--gs-teal)]", bg:"bg-[var(--gs-teal-soft)]", icon:Brain },
            { label:"Unique Users", value:stats.by_user?.length, color:"text-blue-600", bg:"bg-blue-50", icon:Users },
            { label:"Categories", value:stats.by_category?.length, color:"text-violet-600", bg:"bg-violet-50", icon:Brain },
            { label:"System Entries", value:stats.by_user?.find(u=>u.user==="system")?.count||0, color:"text-amber-600", bg:"bg-amber-50", icon:Brain },
          ].map(s=>(
            <Card key={s.label} className="p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{s.label}</span>
                <div className={`h-7 w-7 rounded-lg ${s.bg} grid place-items-center`}><s.icon className={`h-3.5 w-3.5 ${s.color}`}/></div>
              </div>
              <div className="text-2xl font-display">{s.value ?? "—"}</div>
            </Card>
          ))}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-40">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]"/>
          <Input placeholder="Search memories…" className="pl-9" value={search} onChange={e=>setSearch(e.target.value)}/>
        </div>
        <Input placeholder="Filter by user_id…" className="w-40" value={userFilter} onChange={e=>setUserFilter(e.target.value)}/>
        <Select value={catFilter} onValueChange={setCatFilter}>
          <SelectTrigger className="w-40"><SelectValue placeholder="All categories"/></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All</SelectItem>
            {CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {stats?.by_category?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {stats.by_category.map(c=>(
            <button key={c.cat} onClick={()=>setCatFilter(catFilter===c.cat?"":c.cat)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${catFilter===c.cat ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "border-[var(--gs-border)] hover:border-[var(--gs-teal)]"}`}>
              {c.cat} ({c.count})
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i=><div key={i} className="h-16 animate-pulse rounded-xl bg-[var(--gs-surface-2)]"/>)}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-[var(--gs-muted)]">
          <Brain className="h-12 w-12 mx-auto mb-3 opacity-20"/>
          <p>Koi memory nahi — AI abhi kuch yaad nahi rakhta</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(m=>(
            <Card key={m.id} className="p-3 flex items-start gap-3 group hover:shadow-sm transition-shadow">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono text-xs font-semibold text-[var(--gs-teal)]">{m.key}</span>
                  <Badge className={`text-[10px] ${CAT_COLORS[m.category]||"bg-slate-100 text-slate-700"}`}>{m.category}</Badge>
                  <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-0.5"><Users className="h-3 w-3"/>{m.user_id}</span>
                  {m.ttl_days > 0 && <span className="text-[10px] text-amber-600 flex items-center gap-0.5"><AlertTriangle className="h-3 w-3"/>expires {m.ttl_days}d</span>}
                </div>
                <p className="text-xs text-[var(--gs-muted)] line-clamp-2">{m.value}</p>
                <p className="text-[10px] text-[var(--gs-muted)] mt-1">{new Date(m.created_at).toLocaleDateString("en-IN")}</p>
              </div>
              <button onClick={()=>del(m.id)} className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-rose-50 flex-shrink-0">
                <Trash2 className="h-3.5 w-3.5 text-rose-500"/>
              </button>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Memory Add Karo</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium mb-1 block">Key *</label>
                <Input value={form.key} onChange={e=>setForm(f=>({...f,key:e.target.value}))} placeholder="e.g. user_language"/></div>
              <div><label className="text-xs font-medium mb-1 block">User ID</label>
                <Input value={form.user_id} onChange={e=>setForm(f=>({...f,user_id:e.target.value}))} placeholder="system or user ID"/></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium mb-1 block">Category</label>
                <Select value={form.category} onValueChange={v=>setForm(f=>({...f,category:v}))}>
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>{CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select></div>
              <div><label className="text-xs font-medium mb-1 block">TTL (days, 0=forever)</label>
                <Input type="number" min={0} value={form.ttl_days} onChange={e=>setForm(f=>({...f,ttl_days:+e.target.value}))}/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Value *</label>
              <Textarea value={form.value} onChange={e=>setForm(f=>({...f,value:e.target.value}))} placeholder="Memory content…" rows={4}/></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={()=>setOpen(false)}>Cancel</Button>
              <Button onClick={save} style={{background:"var(--gs-teal)"}} className="text-white">Save</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
