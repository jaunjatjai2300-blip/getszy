import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { BookOpen, Plus, Search, Copy, Trash2, Edit2, Sparkles, Tag, TrendingUp } from "lucide-react";
import { toast } from "sonner";

const CATEGORIES = ["general", "marketing", "coding", "content", "sales", "support", "seo", "email", "social", "data"];
const CAT_COLOR = { general:"bg-slate-100 text-slate-700", marketing:"bg-pink-100 text-pink-700", coding:"bg-blue-100 text-blue-700", content:"bg-purple-100 text-purple-700", sales:"bg-green-100 text-green-700", support:"bg-amber-100 text-amber-700", seo:"bg-cyan-100 text-cyan-700", email:"bg-indigo-100 text-indigo-700", social:"bg-rose-100 text-rose-700", data:"bg-teal-100 text-teal-700" };

const BLANK = { title:"", category:"general", prompt:"", variables:[], tags:[], model:"any", is_public:false };

export default function PromptLibrary() {
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [tagInput, setTagInput] = useState("");
  const [preview, setPreview] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/ai-platform/prompts?search=${search}&category=${catFilter}`);
      setPrompts(r.data);
    } catch { toast.error("Load failed"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [search, catFilter]);

  const openCreate = () => { setEditing(null); setForm(BLANK); setTagInput(""); setOpen(true); };
  const openEdit = (p) => { setEditing(p); setForm({ title:p.title, category:p.category, prompt:p.prompt, variables:p.variables||[], tags:p.tags||[], model:p.model||"any", is_public:!!p.is_public }); setTagInput(""); setOpen(true); };

  const save = async () => {
    if (!form.title || !form.prompt) return toast.error("Title aur prompt required hai");
    try {
      if (editing) await api.put(`/admin/ai-platform/prompts/${editing.id}`, form);
      else await api.post("/admin/ai-platform/prompts", form);
      toast.success(editing ? "Prompt updated!" : "Prompt created!");
      setOpen(false); load();
    } catch { toast.error("Save failed"); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete karein?")) return;
    await api.delete(`/admin/ai-platform/prompts/${id}`);
    toast.success("Deleted"); load();
  };

  const copyPrompt = (p) => {
    navigator.clipboard.writeText(p.prompt);
    api.post(`/admin/ai-platform/prompts/${p.id}/use`).catch(()=>{});
    toast.success("Prompt copied!");
  };

  const addTag = () => {
    if (!tagInput.trim()) return;
    setForm(f => ({ ...f, tags: [...f.tags, tagInput.trim()] }));
    setTagInput("");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><BookOpen className="h-7 w-7 text-[var(--gs-teal)]"/>Prompt Library</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Reusable AI prompts — {prompts.length} saved</p>
        </div>
        <Button onClick={openCreate} style={{ background:"var(--gs-teal)" }} className="text-white">
          <Plus className="h-4 w-4 mr-1.5"/>New Prompt
        </Button>
      </div>

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]"/>
          <Input placeholder="Search prompts…" className="pl-9" value={search} onChange={e=>setSearch(e.target.value)}/>
        </div>
        <Select value={catFilter} onValueChange={setCatFilter}>
          <SelectTrigger className="w-40"><SelectValue placeholder="All categories"/></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All</SelectItem>
            {CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{[1,2,3,4,5,6].map(i=><div key={i} className="h-44 animate-pulse rounded-2xl bg-[var(--gs-surface-2)]"/>)}</div>
      ) : prompts.length === 0 ? (
        <div className="text-center py-16 text-[var(--gs-muted)]">
          <Sparkles className="h-12 w-12 mx-auto mb-3 opacity-20"/>
          <p>Koi prompt nahi mila — pehla prompt banao!</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {prompts.map(p=>(
            <Card key={p.id} className="p-4 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer group" onClick={()=>setPreview(p)}>
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold text-sm leading-tight">{p.title}</div>
                <Badge className={`text-[10px] flex-shrink-0 ${CAT_COLOR[p.category]||"bg-slate-100 text-slate-700"}`}>{p.category}</Badge>
              </div>
              <p className="text-xs text-[var(--gs-muted)] line-clamp-3 flex-1">{p.prompt}</p>
              {p.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {p.tags.slice(0,3).map(t=><span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--gs-surface-2)] text-[var(--gs-muted)]">#{t}</span>)}
                </div>
              )}
              <div className="flex items-center justify-between pt-2 border-t" style={{borderColor:"var(--gs-border)"}}>
                <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1"><TrendingUp className="h-3 w-3"/>{p.uses||0} uses</span>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e=>e.stopPropagation()}>
                  <button onClick={()=>copyPrompt(p)} className="p-1.5 rounded-lg hover:bg-[var(--gs-surface-2)]"><Copy className="h-3.5 w-3.5 text-[var(--gs-muted)]"/></button>
                  <button onClick={()=>openEdit(p)} className="p-1.5 rounded-lg hover:bg-[var(--gs-surface-2)]"><Edit2 className="h-3.5 w-3.5 text-[var(--gs-muted)]"/></button>
                  <button onClick={()=>del(p.id)} className="p-1.5 rounded-lg hover:bg-rose-50"><Trash2 className="h-3.5 w-3.5 text-rose-500"/></button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Prompt Edit Karo" : "Naya Prompt"}</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <div><label className="text-xs font-medium mb-1 block">Title *</label>
              <Input value={form.title} onChange={e=>setForm(f=>({...f,title:e.target.value}))} placeholder="Prompt ka naam"/></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium mb-1 block">Category</label>
                <Select value={form.category} onValueChange={v=>setForm(f=>({...f,category:v}))}>
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>{CATEGORIES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select></div>
              <div><label className="text-xs font-medium mb-1 block">Model</label>
                <Input value={form.model} onChange={e=>setForm(f=>({...f,model:e.target.value}))} placeholder="any / llama / gpt-4"/></div>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Prompt *</label>
              <Textarea value={form.prompt} onChange={e=>setForm(f=>({...f,prompt:e.target.value}))} placeholder="Yahan apna prompt likho… {variable} use kar sakte ho" rows={8} className="font-mono text-sm"/></div>
            <div><label className="text-xs font-medium mb-1 block">Tags</label>
              <div className="flex gap-2 flex-wrap mb-2">
                {form.tags.map(t=>(
                  <span key={t} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">
                    #{t}<button onClick={()=>setForm(f=>({...f,tags:f.tags.filter(x=>x!==t)}))}>×</button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input value={tagInput} onChange={e=>setTagInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addTag()} placeholder="Tag add karo…" className="text-sm"/>
                <Button variant="outline" size="sm" onClick={addTag}><Tag className="h-3.5 w-3.5"/></Button>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={()=>setOpen(false)}>Cancel</Button>
              <Button onClick={save} style={{background:"var(--gs-teal)"}} className="text-white">Save Prompt</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!preview} onOpenChange={()=>setPreview(null)}>
        {preview && (
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle className="flex items-center gap-2"><BookOpen className="h-5 w-5 text-[var(--gs-teal)]"/>{preview.title}</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div className="flex gap-2 flex-wrap">
                <Badge className={CAT_COLOR[preview.category]||"bg-slate-100"}>{preview.category}</Badge>
                {preview.model !== "any" && <Badge variant="outline">{preview.model}</Badge>}
              </div>
              <div className="bg-[var(--gs-surface-2)] rounded-xl p-4 font-mono text-sm whitespace-pre-wrap">{preview.prompt}</div>
              {preview.tags?.length > 0 && <div className="flex gap-1 flex-wrap">{preview.tags.map(t=><span key={t} className="text-xs px-2 py-0.5 rounded-full bg-[var(--gs-surface-2)]">#{t}</span>)}</div>}
              <div className="flex gap-2 pt-2">
                <Button onClick={()=>copyPrompt(preview)} style={{background:"var(--gs-teal)"}} className="text-white flex-1"><Copy className="h-4 w-4 mr-1.5"/>Copy Prompt</Button>
                <Button variant="outline" onClick={()=>{setPreview(null);openEdit(preview);}}>Edit</Button>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
