import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { BookMarked, Plus, Search, Trash2, Edit2, FileText, Hash, Globe, BarChart2 } from "lucide-react";
import { toast } from "sonner";

const CATEGORIES = ["general","product","faq","policy","technical","marketing","legal","finance","ops"];
const BLANK = { title:"", content:"", category:"general", tags:[], source_url:"" };

function KBStats({ stats }) {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {[
        { label:"Total Docs", value: stats.total_docs, icon: FileText, color:"text-[var(--gs-teal)]", bg:"bg-[var(--gs-teal-soft)]" },
        { label:"Total Words", value: stats.total_words?.toLocaleString(), icon: Hash, color:"text-violet-600", bg:"bg-violet-50" },
        { label:"Categories", value: stats.categories?.length, icon: BarChart2, color:"text-blue-600", bg:"bg-blue-50" },
        { label:"Avg Words/Doc", value: stats.total_docs ? Math.round(stats.total_words/stats.total_docs) : 0, icon: FileText, color:"text-amber-600", bg:"bg-amber-50" },
      ].map(s => (
        <Card key={s.label} className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{s.label}</span>
            <div className={`h-7 w-7 rounded-lg ${s.bg} grid place-items-center`}><s.icon className={`h-3.5 w-3.5 ${s.color}`}/></div>
          </div>
          <div className="text-2xl font-display">{s.value ?? "—"}</div>
        </Card>
      ))}
    </div>
  );
}

export default function KnowledgeBase() {
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [tagInput, setTagInput] = useState("");
  const [selected, setSelected] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [dr, sr] = await Promise.allSettled([
        api.get(`/admin/ai-platform/kb?category=${catFilter}&search=${search}`),
        api.get("/admin/ai-platform/kb/stats"),
      ]);
      if (dr.status==="fulfilled") setDocs(dr.value.data);
      if (sr.status==="fulfilled") setStats(sr.value.data);
    } catch { toast.error("Load failed"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search, catFilter]);

  const openCreate = () => { setEditing(null); setForm(BLANK); setTagInput(""); setOpen(true); };
  const openEdit = (d) => { setEditing(d); setForm({ title:d.title, content:d.content, category:d.category, tags:d.tags||[], source_url:d.source_url||"" }); setTagInput(""); setOpen(true); };

  const save = async () => {
    if (!form.title || !form.content) return toast.error("Title aur content required hai");
    try {
      if (editing) await api.put(`/admin/ai-platform/kb/${editing.id}`, form);
      else await api.post("/admin/ai-platform/kb", form);
      toast.success(editing ? "Doc updated!" : "Doc added!");
      setOpen(false); load();
    } catch { toast.error("Save failed"); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete karein?")) return;
    await api.delete(`/admin/ai-platform/kb/${id}`);
    toast.success("Deleted"); load();
  };

  const addTag = () => {
    if (!tagInput.trim()) return;
    setForm(f=>({...f, tags:[...f.tags, tagInput.trim()]}));
    setTagInput("");
  };

  const searchKB = async () => {
    if (!search.trim()) return load();
    try {
      const r = await api.post("/admin/ai-platform/kb/search", { query:search, limit:20 });
      setDocs(r.data);
    } catch { toast.error("Search failed"); }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><BookMarked className="h-7 w-7 text-[var(--gs-teal)]"/>Knowledge Base</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">AI ka context — documents, FAQs, policies store karo</p>
        </div>
        <Button onClick={openCreate} style={{background:"var(--gs-teal)"}} className="text-white">
          <Plus className="h-4 w-4 mr-1.5"/>Add Document
        </Button>
      </div>

      <KBStats stats={stats}/>

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]"/>
          <Input placeholder="Search content…" className="pl-9" value={search}
            onChange={e=>setSearch(e.target.value)} onKeyDown={e=>e.key==="Enter"&&searchKB()}/>
        </div>
        <Select value={catFilter} onValueChange={setCatFilter}>
          <SelectTrigger className="w-40"><SelectValue placeholder="All categories"/></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All</SelectItem>
            {CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={searchKB}><Search className="h-4 w-4"/></Button>
      </div>

      {stats?.categories?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button onClick={()=>setCatFilter("")} className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${!catFilter ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "border-[var(--gs-border)] hover:border-[var(--gs-teal)]"}`}>All</button>
          {stats.categories.map(c=>(
            <button key={c.name} onClick={()=>setCatFilter(c.name)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${catFilter===c.name ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "border-[var(--gs-border)] hover:border-[var(--gs-teal)]"}`}>
              {c.name} ({c.count})
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-24 animate-pulse rounded-2xl bg-[var(--gs-surface-2)]"/>)}</div>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 text-[var(--gs-muted)]">
          <BookMarked className="h-12 w-12 mx-auto mb-3 opacity-20"/>
          <p>Koi document nahi — pehla doc add karo!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map(d=>(
            <Card key={d.id} className="p-4 hover:shadow-md transition-shadow cursor-pointer group" onClick={()=>setSelected(d)}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-[var(--gs-teal)] flex-shrink-0"/>
                    <span className="font-semibold text-sm truncate">{d.title}</span>
                    <Badge className="text-[10px] bg-slate-100 text-slate-700 flex-shrink-0">{d.category}</Badge>
                  </div>
                  <p className="text-xs text-[var(--gs-muted)] line-clamp-2">{d.content}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[10px] text-[var(--gs-muted)]">{d.word_count || 0} words</span>
                    {d.source_url && <a href={d.source_url} target="_blank" rel="noreferrer" className="text-[10px] text-[var(--gs-teal)] flex items-center gap-0.5" onClick={e=>e.stopPropagation()}><Globe className="h-3 w-3"/>Source</a>}
                    {d.tags?.length > 0 && d.tags.slice(0,3).map(t=><span key={t} className="text-[10px] text-[var(--gs-muted)]">#{t}</span>)}
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e=>e.stopPropagation()}>
                  <button onClick={()=>openEdit(d)} className="p-1.5 rounded-lg hover:bg-[var(--gs-surface-2)]"><Edit2 className="h-3.5 w-3.5 text-[var(--gs-muted)]"/></button>
                  <button onClick={()=>del(d.id)} className="p-1.5 rounded-lg hover:bg-rose-50"><Trash2 className="h-3.5 w-3.5 text-rose-500"/></button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Document Edit Karo" : "Naya Document Add Karo"}</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <div><label className="text-xs font-medium mb-1 block">Title *</label>
              <Input value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} placeholder="Document ka naam"/></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium mb-1 block">Category</label>
                <Select value={form.category} onValueChange={v=>setForm(f=>({...f,category:v}))}>
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>{CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select></div>
              <div><label className="text-xs font-medium mb-1 block">Source URL</label>
                <Input value={form.source_url} onChange={e=>setForm(f=>({...f,source_url:e.target.value}))} placeholder="https://…"/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Content *</label>
              <Textarea value={form.content} onChange={e=>setForm(f=>({...f,content:e.target.value}))} placeholder="Document ka poora content yahan paste karo…" rows={10}/></div>
            <div><label className="text-xs font-medium mb-1 block">Tags</label>
              <div className="flex gap-1 flex-wrap mb-2">
                {form.tags.map(t=><span key={t} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">#{t}<button onClick={()=>setForm(f=>({...f,tags:f.tags.filter(x=>x!==t)}))}>×</button></span>)}
              </div>
              <div className="flex gap-2">
                <Input value={tagInput} onChange={e=>setTagInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addTag()} placeholder="Tag…" className="text-sm"/>
                <Button variant="outline" size="sm" onClick={addTag}>Add</Button>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={()=>setOpen(false)}>Cancel</Button>
              <Button onClick={save} style={{background:"var(--gs-teal)"}} className="text-white">Save</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!selected} onOpenChange={()=>setSelected(null)}>
        {selected && (
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><FileText className="h-5 w-5 text-[var(--gs-teal)]"/>{selected.title}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 mt-2">
              <div className="flex gap-2 flex-wrap">
                <Badge className="bg-slate-100 text-slate-700">{selected.category}</Badge>
                <span className="text-xs text-[var(--gs-muted)]">{selected.word_count} words</span>
                {selected.source_url && <a href={selected.source_url} target="_blank" rel="noreferrer" className="text-xs text-[var(--gs-teal)]">Source →</a>}
              </div>
              <div className="bg-[var(--gs-surface-2)] rounded-xl p-4 text-sm whitespace-pre-wrap max-h-96 overflow-y-auto">{selected.content}</div>
              {selected.tags?.length > 0 && <div className="flex gap-1 flex-wrap">{selected.tags.map(t=><span key={t} className="text-xs px-2 py-0.5 rounded-full bg-[var(--gs-surface-2)]">#{t}</span>)}</div>}
              <div className="flex gap-2 pt-2">
                <Button onClick={()=>{setSelected(null);openEdit(selected);}} variant="outline" className="flex-1">Edit</Button>
                <Button onClick={()=>{del(selected.id);setSelected(null);}} variant="outline" className="text-rose-500 border-rose-200"><Trash2 className="h-4 w-4"/></Button>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
