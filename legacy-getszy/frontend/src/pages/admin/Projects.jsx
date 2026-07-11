import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  FolderOpen, Globe, Code2, Database, Server, Cpu, ShoppingBag,
  Rocket, BarChart2, FileText, Settings, ArrowLeft, Plus, Trash2,
  RefreshCw, Loader2, ChevronRight, Eye, Terminal, Layers, Key,
  Cloud, Activity, AlertCircle, CheckCircle2, Clock, Save, Zap
} from "lucide-react";
import { toast } from "sonner";

const PROJECT_TYPES = [
  { value: "webapp", label: "Web App", icon: "🌐" },
  { value: "saas", label: "SaaS", icon: "☁️" },
  { value: "store", label: "E-commerce Store", icon: "🛍️" },
  { value: "mobile", label: "Mobile App", icon: "📱" },
  { value: "api", label: "API Service", icon: "⚡" },
  { value: "internal", label: "Internal Tool", icon: "🔧" },
  { value: "blog", label: "Blog/Content", icon: "📝" },
  { value: "dashboard", label: "Dashboard", icon: "📊" },
];

const COLORS = ["#6366f1","#0ea5e9","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6"];
const ICONS = ["📁","🌐","⚡","🛍️","📱","🤖","🎯","🚀","📊","💡","🔧","🎨"];

function StatusPill({ s }) {
  if (s === "live") return <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-2.5 w-2.5 mr-1"/>Live</Badge>;
  if (s === "deploying") return <Badge className="bg-blue-100 text-blue-700 text-[10px]"><Loader2 className="h-2.5 w-2.5 mr-1 animate-spin"/>Deploying</Badge>;
  if (s === "draft") return <Badge variant="outline" className="text-[10px]">Draft</Badge>;
  return <Badge variant="outline" className="text-[10px]">{s}</Badge>;
}

// ─────────────── Overview Tab ───────────────
function OverviewTab({ project, onUpdate }) {
  const [form, setForm] = useState({ name: project.name, description: project.description || "", tags: (project.tags || []).join(", "), tech_stack: (project.tech_stack || []).join(", ") });
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/projects/${project.id}`, { name: form.name, description: form.description, tags: form.tags.split(",").map(t=>t.trim()).filter(Boolean), tech_stack: form.tech_stack.split(",").map(t=>t.trim()).filter(Boolean) });
      toast.success("Saved"); onUpdate();
    } catch { toast.error("Save failed"); } finally { setSaving(false); }
  };
  return (
    <div className="space-y-4 max-w-lg">
      <div><label className="text-xs font-medium mb-1 block">Project Name</label>
        <Input value={form.name} onChange={e=>setForm(p=>({...p,name:e.target.value}))} className="h-9 text-sm"/></div>
      <div><label className="text-xs font-medium mb-1 block">Description</label>
        <Textarea value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))} rows={3} className="text-sm"/></div>
      <div><label className="text-xs font-medium mb-1 block">Tech Stack (comma separated)</label>
        <Input placeholder="React, Node.js, MongoDB" value={form.tech_stack} onChange={e=>setForm(p=>({...p,tech_stack:e.target.value}))} className="h-9 text-sm"/></div>
      <div><label className="text-xs font-medium mb-1 block">Tags</label>
        <Input placeholder="ecommerce, ai, saas" value={form.tags} onChange={e=>setForm(p=>({...p,tags:e.target.value}))} className="h-9 text-sm"/></div>
      <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save} disabled={saving}>
        {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/> : <Save className="h-3.5 w-3.5 mr-1"/>}Save
      </Button>
      <div className="mt-6 grid grid-cols-2 gap-3">
        {[["Created",new Date(project.created_at).toLocaleDateString("en-IN")],["Status",project.status||"draft"],["Type",project.type||"webapp"],["Deploys",project.deploy_count||0]].map(([k,v])=>(
          <div key={k} className="bg-[var(--gs-surface-2)] rounded-xl p-3"><p className="text-[10px] text-[var(--gs-muted)]">{k}</p><p className="text-sm font-semibold mt-0.5">{v}</p></div>
        ))}
      </div>
    </div>
  );
}

// ─────────────── Database Tab ───────────────
function DatabaseTab({ project }) {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTable, setNewTable] = useState("");
  const [selected, setSelected] = useState(null);
  const [newCol, setNewCol] = useState({ name: "", type: "string", required: false });

  const load = useCallback(async () => {
    try { const r = await api.get(`/projects/${project.id}/schema`); setTables(r.data.tables || []); } catch {}
    finally { setLoading(false); }
  }, [project.id]);

  useEffect(() => { load(); }, [load]);

  const addTable = async () => {
    if (!newTable.trim()) return;
    try { await api.post(`/projects/${project.id}/schema/tables`, { name: newTable, columns: [{ name: "id", type: "string", required: true }] }); setNewTable(""); await load(); toast.success("Table added"); } catch { toast.error("Error"); }
  };

  const addColumn = async () => {
    if (!newCol.name || !selected) return;
    const tbl = tables.find(t => t.id === selected);
    if (!tbl) return;
    const cols = [...(tbl.columns || []), newCol];
    try { await api.put(`/projects/${project.id}/schema/tables/${selected}`, { columns: cols }); setNewCol({ name: "", type: "string", required: false }); await load(); } catch { toast.error("Error"); }
  };

  const delTable = async (tid) => {
    try { await api.delete(`/projects/${project.id}/schema/tables/${tid}`); if (selected === tid) setSelected(null); await load(); toast.success("Deleted"); } catch { toast.error("Error"); }
  };

  const selTable = tables.find(t => t.id === selected);
  const COL_TYPES = ["string","number","boolean","date","array","object","text","email","url","file"];

  return (
    <div className="flex gap-4 h-[420px]">
      <div className="w-48 flex flex-col gap-2">
        <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Tables ({tables.length})</p>
        {loading ? <Loader2 className="h-4 w-4 animate-spin text-[var(--gs-muted)]"/> : tables.map(t=>(
          <button key={t.id} onClick={()=>setSelected(t.id)}
            className={`text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between gap-1 ${selected===t.id?"bg-[var(--gs-teal)] text-white":"bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}>
            <span className="truncate">{t.name}</span>
            <button onClick={e=>{e.stopPropagation();delTable(t.id)}} className="opacity-50 hover:opacity-100"><Trash2 className="h-2.5 w-2.5"/></button>
          </button>
        ))}
        <div className="flex gap-1 mt-auto">
          <Input className="h-7 text-xs flex-1" placeholder="table_name" value={newTable} onChange={e=>setNewTable(e.target.value)} onKeyDown={e=>e.key==="Enter"&&addTable()}/>
          <Button size="sm" className="h-7 px-2 bg-[var(--gs-teal)]" onClick={addTable}><Plus className="h-3 w-3"/></Button>
        </div>
      </div>
      <div className="flex-1 bg-[var(--gs-surface-2)] rounded-xl p-4 overflow-y-auto">
        {!selTable ? <div className="h-full flex items-center justify-center text-sm text-[var(--gs-muted)]">← Table select karo</div> : (
          <>
            <p className="font-semibold text-sm mb-3 flex items-center gap-2"><Database className="h-4 w-4 text-[var(--gs-teal)]"/>{selTable.name}</p>
            <table className="w-full text-xs">
              <thead><tr className="text-[var(--gs-muted)]"><th className="text-left pb-2">Column</th><th className="text-left pb-2">Type</th><th className="text-left pb-2">Required</th></tr></thead>
              <tbody>{(selTable.columns||[]).map((c,i)=>(
                <tr key={i} className="border-t border-[var(--gs-border)]">
                  <td className="py-1.5 pr-3 font-mono">{c.name}</td>
                  <td className="py-1.5 pr-3"><Badge variant="outline" className="text-[10px]">{c.type}</Badge></td>
                  <td className="py-1.5">{c.required?<CheckCircle2 className="h-3 w-3 text-emerald-500"/>:<span className="text-[var(--gs-muted)]">—</span>}</td>
                </tr>
              ))}</tbody>
            </table>
            <div className="flex gap-2 mt-3 pt-3 border-t border-[var(--gs-border)]">
              <Input className="h-7 text-xs flex-1" placeholder="column_name" value={newCol.name} onChange={e=>setNewCol(p=>({...p,name:e.target.value}))}/>
              <Select value={newCol.type} onValueChange={v=>setNewCol(p=>({...p,type:v}))}>
                <SelectTrigger className="h-7 text-xs w-28"><SelectValue/></SelectTrigger>
                <SelectContent>{COL_TYPES.map(t=><SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>)}</SelectContent>
              </Select>
              <Button size="sm" className="h-7 px-2 bg-[var(--gs-teal)]" onClick={addColumn}><Plus className="h-3 w-3"/></Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────── API Endpoints Tab ───────────────
function ApiTab({ project }) {
  const [eps, setEps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ method: "GET", path: "", description: "", auth_required: true });

  const load = useCallback(async () => {
    try { const r = await api.get(`/projects/${project.id}/endpoints`); setEps(r.data.endpoints || []); } catch {} finally { setLoading(false); }
  }, [project.id]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!form.path) return toast.error("Path chahiye");
    try { await api.post(`/projects/${project.id}/endpoints`, form); setForm({ method:"GET", path:"", description:"", auth_required:true }); await load(); toast.success("Endpoint added"); } catch { toast.error("Error"); }
  };
  const del = async (eid) => { try { await api.delete(`/projects/${project.id}/endpoints/${eid}`); await load(); } catch {} };

  const METHOD_COLORS = { GET:"text-emerald-600 bg-emerald-50", POST:"text-blue-600 bg-blue-50", PUT:"text-amber-600 bg-amber-50", DELETE:"text-rose-600 bg-rose-50", PATCH:"text-purple-600 bg-purple-50" };
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Select value={form.method} onValueChange={v=>setForm(p=>({...p,method:v}))}>
          <SelectTrigger className="h-9 text-xs w-24"><SelectValue/></SelectTrigger>
          <SelectContent>{["GET","POST","PUT","DELETE","PATCH"].map(m=><SelectItem key={m} value={m} className="text-xs">{m}</SelectItem>)}</SelectContent>
        </Select>
        <Input className="h-9 text-xs font-mono flex-1" placeholder="/api/endpoint" value={form.path} onChange={e=>setForm(p=>({...p,path:e.target.value}))}/>
        <Input className="h-9 text-xs flex-1" placeholder="Description" value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))}/>
        <Button size="sm" className="h-9 bg-[var(--gs-teal)]" onClick={add}><Plus className="h-3.5 w-3.5 mr-1"/>Add</Button>
      </div>
      {loading ? <Loader2 className="h-4 w-4 animate-spin"/> : (
        <div className="space-y-2">
          {eps.length === 0 ? <p className="text-sm text-[var(--gs-muted)] text-center py-8">Koi endpoints nahi — upar se add karo</p> : eps.map(e=>(
            <div key={e.id} className="flex items-center gap-3 p-3 bg-[var(--gs-surface-2)] rounded-xl">
              <Badge className={`text-[10px] font-mono ${METHOD_COLORS[e.method]||"text-gray-600 bg-gray-50"}`}>{e.method}</Badge>
              <code className="text-xs flex-1 font-mono">{e.path}</code>
              <span className="text-xs text-[var(--gs-muted)] flex-1">{e.description}</span>
              {e.auth_required && <Badge variant="outline" className="text-[10px]"><Key className="h-2.5 w-2.5 mr-1"/>Auth</Badge>}
              <button onClick={()=>del(e.id)} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-3.5 w-3.5"/></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────── Env Vars Tab ───────────────
function EnvTab({ project }) {
  const [envs, setEnvs] = useState([]);
  const [form, setForm] = useState({ key: "", value: "", is_secret: false });
  const load = useCallback(async()=>{try{const r=await api.get(`/projects/${project.id}/env`);setEnvs(r.data.env||[]);}catch{}}, [project.id]);
  useEffect(()=>{load();},[load]);
  const add = async()=>{if(!form.key||!form.value)return;try{await api.post(`/projects/${project.id}/env`,form);setForm({key:"",value:"",is_secret:false});await load();toast.success("Saved");}catch{toast.error("Error");}};
  const del = async(key)=>{try{await api.delete(`/projects/${project.id}/env/${key}`);await load();}catch{}};
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input className="h-9 text-xs font-mono w-40" placeholder="KEY_NAME" value={form.key} onChange={e=>setForm(p=>({...p,key:e.target.value.toUpperCase()}))}/>
        <Input className="h-9 text-xs font-mono flex-1" placeholder="value" value={form.value} onChange={e=>setForm(p=>({...p,value:e.target.value}))}/>
        <Button size="sm" variant={form.is_secret?"default":"outline"} className="h-9 px-3 text-xs" onClick={()=>setForm(p=>({...p,is_secret:!p.is_secret}))}><Key className="h-3 w-3 mr-1"/>{form.is_secret?"Secret":"Plain"}</Button>
        <Button size="sm" className="h-9 bg-[var(--gs-teal)]" onClick={add}><Plus className="h-3.5 w-3.5 mr-1"/>Add</Button>
      </div>
      <div className="space-y-1.5">
        {envs.map(e=>(
          <div key={e.key} className="flex items-center gap-3 p-2.5 bg-[var(--gs-surface-2)] rounded-lg">
            <code className="text-xs font-mono text-[var(--gs-teal)] w-40 truncate">{e.key}</code>
            <code className="text-xs font-mono flex-1 text-[var(--gs-muted)]">{e.value}</code>
            {e.is_secret && <Key className="h-3 w-3 text-amber-500"/>}
            <button onClick={()=>del(e.key)} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-3 w-3"/></button>
          </div>
        ))}
        {envs.length===0 && <p className="text-sm text-[var(--gs-muted)] text-center py-6">Koi env vars nahi</p>}
      </div>
    </div>
  );
}

// ─────────────── Logs Tab ───────────────
function LogsTab({ project }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async()=>{setLoading(true);try{const r=await api.get(`/projects/${project.id}/logs`);setLogs(r.data.logs||[]);}catch{}finally{setLoading(false);}}, [project.id]);
  useEffect(()=>{load();},[load]);
  const clear = async()=>{try{await api.delete(`/projects/${project.id}/logs`);await load();toast.success("Logs cleared");}catch{}};
  const LEVEL_CL = { info:"text-[var(--gs-teal)]", error:"text-rose-400", warn:"text-amber-400", debug:"text-[var(--gs-muted)]" };
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-[var(--gs-muted)]">{logs.length} entries</p>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={load}><RefreshCw className="h-3 w-3 mr-1"/>Refresh</Button>
          <Button size="sm" variant="outline" className="h-7 text-xs text-rose-500" onClick={clear}>Clear</Button>
        </div>
      </div>
      <div className="bg-[#0a0a0a] rounded-xl p-3 font-mono text-xs h-80 overflow-y-auto space-y-1">
        {loading ? <p className="text-[var(--gs-muted)] text-center py-4">Loading…</p> : logs.length===0 ? <p className="text-[var(--gs-muted)] text-center py-4">No logs yet</p> : logs.map((l,i)=>(
          <div key={i} className="flex gap-2">
            <span className="text-[#555] shrink-0">{l.ts?.slice(11,19)||"--:--:--"}</span>
            <span className={LEVEL_CL[l.level]||"text-gray-400"}>[{l.level?.toUpperCase()||"INFO"}]</span>
            <span className="text-gray-200 flex-1">{l.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────── Analytics Tab ───────────────
function AnalyticsTab({ project }) {
  const [data, setData] = useState(null);
  useEffect(()=>{ api.get(`/projects/${project.id}/analytics`).then(r=>setData(r.data)).catch(()=>{}); },[project.id]);
  if (!data) return <Loader2 className="h-5 w-5 animate-spin text-[var(--gs-muted)]"/>;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {[["Page Views",data.page_views,"👁️"],["API Calls",data.api_calls,"⚡"],["Errors",data.errors,"❌"],["Uptime",data.uptime,"💚"],["Deploy Count",data.deploy_count,"🚀"],["Last Deployed",data.last_deployed?new Date(data.last_deployed).toLocaleDateString("en-IN"):"Never","📅"]].map(([k,v,ic])=>(
        <Card key={k} className="p-4"><p className="text-[10px] text-[var(--gs-muted)]">{ic} {k}</p><p className="text-2xl font-bold mt-1">{v??0}</p></Card>
      ))}
    </div>
  );
}

// ─────────────── Deploy Tab ───────────────
function DeployTab({ project, onUpdate }) {
  const [deploys, setDeploys] = useState([]);
  const [deploying, setDeploying] = useState(false);
  const [env, setEnv] = useState("production");
  const load = useCallback(async()=>{try{const r=await api.get(`/projects/${project.id}/deploys`);setDeploys(r.data.deploys||[]);}catch{}},[project.id]);
  useEffect(()=>{load();},[load]);
  const deploy = async()=>{
    setDeploying(true);
    try { await api.post(`/projects/${project.id}/deploy`,{environment:env}); toast.success("Deploy successful!"); await load(); onUpdate(); }
    catch { toast.error("Deploy failed"); } finally { setDeploying(false); }
  };
  return (
    <div className="space-y-4">
      <div className="flex gap-3 items-end">
        <div><label className="text-xs font-medium mb-1 block">Environment</label>
          <Select value={env} onValueChange={setEnv}>
            <SelectTrigger className="h-9 text-xs w-36"><SelectValue/></SelectTrigger>
            <SelectContent><SelectItem value="production" className="text-xs">🚀 Production</SelectItem><SelectItem value="staging" className="text-xs">🧪 Staging</SelectItem></SelectContent>
          </Select>
        </div>
        <Button className="h-9 bg-[var(--gs-teal)]" onClick={deploy} disabled={deploying}>
          {deploying?<Loader2 className="h-4 w-4 animate-spin mr-1"/>:<Rocket className="h-4 w-4 mr-1"/>}Deploy
        </Button>
      </div>
      <div className="space-y-2">
        <p className="text-xs font-medium text-[var(--gs-muted)] uppercase tracking-wide">Deploy History</p>
        {deploys.length===0?<p className="text-sm text-[var(--gs-muted)] text-center py-6">Abhi tak koi deploy nahi</p>:deploys.map(d=>(
          <div key={d.id} className="flex items-center gap-3 p-3 bg-[var(--gs-surface-2)] rounded-xl">
            {d.status==="live"?<CheckCircle2 className="h-4 w-4 text-emerald-500"/>:d.status==="deploying"?<Loader2 className="h-4 w-4 animate-spin text-blue-500"/>:<AlertCircle className="h-4 w-4 text-rose-500"/>}
            <div className="flex-1"><p className="text-xs font-medium">{d.environment||"production"}</p><p className="text-[10px] text-[var(--gs-muted)]">{d.message}</p></div>
            <span className="text-[10px] text-[var(--gs-muted)]">{d.started_at?new Date(d.started_at).toLocaleString("en-IN"):""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────── AI Tab ───────────────
function AITab({ project }) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(()=>{ api.get(`/projects/${project.id}/ai`).then(r=>setCfg(r.data)).catch(()=>{}); },[project.id]);
  const save = async()=>{setSaving(true);try{await api.put(`/projects/${project.id}/ai`,cfg);toast.success("AI config saved");}catch{toast.error("Error");}finally{setSaving(false);}};
  if (!cfg) return <Loader2 className="h-5 w-5 animate-spin"/>;
  return (
    <div className="space-y-4 max-w-lg">
      <div><label className="text-xs font-medium mb-1 block">Provider</label>
        <Select value={cfg.provider} onValueChange={v=>setCfg(p=>({...p,provider:v}))}>
          <SelectTrigger className="h-9 text-xs"><SelectValue/></SelectTrigger>
          <SelectContent>{["ollama","openai","anthropic","gemini"].map(p=><SelectItem key={p} value={p} className="text-xs">{p}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div><label className="text-xs font-medium mb-1 block">Model</label>
        <Input className="h-9 text-xs" value={cfg.model} onChange={e=>setCfg(p=>({...p,model:e.target.value}))}/></div>
      <div><label className="text-xs font-medium mb-1 block">System Prompt</label>
        <Textarea rows={4} className="text-xs" value={cfg.system_prompt} onChange={e=>setCfg(p=>({...p,system_prompt:e.target.value}))}/></div>
      <div><label className="text-xs font-medium mb-1 block">Temperature: {cfg.temperature}</label>
        <input type="range" min="0" max="1" step="0.1" value={cfg.temperature} onChange={e=>setCfg(p=>({...p,temperature:parseFloat(e.target.value)}))} className="w-full accent-[var(--gs-teal)]"/></div>
      <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save} disabled={saving}>
        {saving?<Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/>:<Save className="h-3.5 w-3.5 mr-1"/>}Save AI Config
      </Button>
    </div>
  );
}

// ─────────────── Settings Tab ───────────────
function ProjectSettings({ project, onDelete, onUpdate }) {
  const [form, setForm] = useState({ icon: project.icon||"📁", color: project.color||"#6366f1", type: project.type||"webapp" });
  const save = async()=>{try{await api.put(`/projects/${project.id}`,form);toast.success("Saved");onUpdate();}catch{toast.error("Error");}};
  const del = async()=>{if(!window.confirm(`"${project.name}" delete karein?`))return;try{await api.delete(`/projects/${project.id}`);onDelete();toast.success("Deleted");}catch{toast.error("Error");}};
  return (
    <div className="space-y-4 max-w-md">
      <div><label className="text-xs font-medium mb-1 block">Icon</label>
        <div className="flex flex-wrap gap-2">{ICONS.map(ic=><button key={ic} onClick={()=>setForm(p=>({...p,icon:ic}))} className={`text-xl p-2 rounded-lg transition-all ${form.icon===ic?"bg-[var(--gs-teal)] shadow-md scale-110":"bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}>{ic}</button>)}</div>
      </div>
      <div><label className="text-xs font-medium mb-1 block">Color</label>
        <div className="flex gap-2">{COLORS.map(c=><button key={c} onClick={()=>setForm(p=>({...p,color:c}))} className={`h-7 w-7 rounded-full transition-all ${form.color===c?"ring-2 ring-offset-2 ring-gray-400 scale-110":""}`} style={{background:c}}/> )}</div>
      </div>
      <div><label className="text-xs font-medium mb-1 block">Type</label>
        <Select value={form.type} onValueChange={v=>setForm(p=>({...p,type:v}))}>
          <SelectTrigger className="h-9 text-xs"><SelectValue/></SelectTrigger>
          <SelectContent>{PROJECT_TYPES.map(t=><SelectItem key={t.value} value={t.value} className="text-xs">{t.icon} {t.label}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save}><Save className="h-3.5 w-3.5 mr-1"/>Save Changes</Button>
      <hr className="border-[var(--gs-border)] my-2"/>
      <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
        <p className="text-sm font-medium text-rose-700 mb-1">Danger Zone</p>
        <p className="text-xs text-rose-500 mb-3">Ye project aur uska sara data permanently delete ho jayega.</p>
        <Button size="sm" variant="destructive" onClick={del}><Trash2 className="h-3.5 w-3.5 mr-1"/>Delete Project</Button>
      </div>
    </div>
  );
}

// ─────────────── Project Workspace ───────────────
function ProjectWorkspace({ project: initial, onBack }) {
  const [project, setProject] = useState(initial);
  const reload = useCallback(async()=>{ try{ const r=await api.get(`/projects/${project.id}`); setProject(r.data); } catch{} },[project.id]);
  const TABS = [
    { id:"overview", label:"Overview", icon:Layers },
    { id:"database", label:"Database", icon:Database },
    { id:"api", label:"API", icon:Zap },
    { id:"env", label:"Env Vars", icon:Key },
    { id:"ai", label:"AI", icon:Cpu },
    { id:"deploy", label:"Deploy", icon:Rocket },
    { id:"analytics", label:"Analytics", icon:BarChart2 },
    { id:"logs", label:"Logs", icon:Terminal },
    { id:"settings", label:"Settings", icon:Settings },
  ];
  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <Button variant="ghost" size="sm" onClick={onBack} className="h-8 px-2"><ArrowLeft className="h-4 w-4"/></Button>
        <div className="h-9 w-9 rounded-xl grid place-items-center text-lg" style={{background:project.color||"#6366f1"}}>{project.icon||"📁"}</div>
        <div>
          <h1 className="font-display text-xl font-bold">{project.name}</h1>
          <p className="text-xs text-[var(--gs-muted)]">{project.type} · {project.description||"No description"}</p>
        </div>
        <StatusPill s={project.status} />
      </div>
      <Tabs defaultValue="overview">
        <TabsList className="h-auto gap-1 flex-wrap">
          {TABS.map(t=><TabsTrigger key={t.id} value={t.id} className="text-xs h-8"><t.icon className="h-3 w-3 mr-1"/>{t.label}</TabsTrigger>)}
        </TabsList>
        <div className="mt-5">
          <TabsContent value="overview"><OverviewTab project={project} onUpdate={reload}/></TabsContent>
          <TabsContent value="database"><DatabaseTab project={project}/></TabsContent>
          <TabsContent value="api"><ApiTab project={project}/></TabsContent>
          <TabsContent value="env"><EnvTab project={project}/></TabsContent>
          <TabsContent value="ai"><AITab project={project}/></TabsContent>
          <TabsContent value="deploy"><DeployTab project={project} onUpdate={reload}/></TabsContent>
          <TabsContent value="analytics"><AnalyticsTab project={project}/></TabsContent>
          <TabsContent value="logs"><LogsTab project={project}/></TabsContent>
          <TabsContent value="settings"><ProjectSettings project={project} onDelete={onBack} onUpdate={reload}/></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

// ─────────────── New Project Dialog ───────────────
function NewProjectDialog({ open, onClose, onCreate }) {
  const [form, setForm] = useState({ name:"", description:"", type:"webapp", icon:"📁", color:"#6366f1" });
  const [creating, setCreating] = useState(false);
  const create = async()=>{
    if (!form.name.trim()) return toast.error("Name chahiye");
    setCreating(true);
    try { const r=await api.post("/projects",form); toast.success("Project created!"); onCreate(r.data); }
    catch { toast.error("Error creating project"); } finally { setCreating(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="font-display text-lg">New Project</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2">
          <div><label className="text-xs font-medium mb-1 block">Project Name *</label>
            <Input placeholder="e.g. Hospital CRM" value={form.name} onChange={e=>setForm(p=>({...p,name:e.target.value}))} className="h-9 text-sm"/></div>
          <div><label className="text-xs font-medium mb-1 block">Description</label>
            <Textarea placeholder="Kya banana hai..." rows={2} value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))} className="text-sm"/></div>
          <div><label className="text-xs font-medium mb-1 block">Type</label>
            <div className="grid grid-cols-4 gap-2">
              {PROJECT_TYPES.map(t=>(
                <button key={t.value} onClick={()=>setForm(p=>({...p,type:t.value}))}
                  className={`p-2.5 rounded-xl text-center text-xs border transition-all ${form.type===t.value?"border-[var(--gs-teal)] bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]":"border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}>
                  <div className="text-xl mb-0.5">{t.icon}</div>{t.label}
                </button>
              ))}
            </div>
          </div>
          <div><label className="text-xs font-medium mb-1 block">Icon</label>
            <div className="flex gap-1.5 flex-wrap">{ICONS.map(ic=><button key={ic} onClick={()=>setForm(p=>({...p,icon:ic}))} className={`text-lg p-1.5 rounded-lg ${form.icon===ic?"bg-[var(--gs-teal-soft)] ring-1 ring-[var(--gs-teal)]":"hover:bg-[var(--gs-surface-2)]"}`}>{ic}</button>)}</div>
          </div>
          <div><label className="text-xs font-medium mb-1 block">Color</label>
            <div className="flex gap-2">{COLORS.map(c=><button key={c} onClick={()=>setForm(p=>({...p,color:c}))} className={`h-6 w-6 rounded-full ${form.color===c?"ring-2 ring-offset-1 ring-gray-400":""}`} style={{background:c}}/> )}</div>
          </div>
          <Button className="w-full bg-[var(--gs-teal)]" onClick={create} disabled={creating}>
            {creating?<Loader2 className="h-4 w-4 animate-spin mr-2"/>:<Plus className="h-4 w-4 mr-2"/>}Create Project
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────── Main Page ───────────────
export default function AdminProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedProject, setSelectedProject] = useState(null);
  const [showNew, setShowNew] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get("/projects"); setProjects(r.data.items||[]); }
    catch { toast.error("Projects load karne mein error"); }
    finally { setLoading(false); }
  },[]);

  useEffect(()=>{ load(); },[load]);

  const filtered = projects.filter(p=>{
    const matchSearch = !search || (p.name||"").toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter==="all" || p.type===typeFilter;
    return matchSearch && matchType;
  });

  if (selectedProject) {
    return <ProjectWorkspace project={selectedProject} onBack={()=>{setSelectedProject(null);load();}}/>;
  }

  return (
    <div className="space-y-5" data-testid="admin-projects-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><FolderOpen className="h-7 w-7 text-[var(--gs-teal)]"/>Projects</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{projects.length} total projects · Har project ek complete application</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Input className="pl-8 h-9 w-52 text-xs" placeholder="Search projects…" value={search} onChange={e=>setSearch(e.target.value)}/>
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="h-9 text-xs w-36"><SelectValue placeholder="All Types"/></SelectTrigger>
            <SelectContent><SelectItem value="all" className="text-xs">All Types</SelectItem>{PROJECT_TYPES.map(t=><SelectItem key={t.value} value={t.value} className="text-xs">{t.icon} {t.label}</SelectItem>)}</SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1.5"/>New Project</Button>
        </div>
      </div>

      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[1,2,3,4].map(i=><div key={i} className="h-44 rounded-2xl bg-[var(--gs-surface-2)] animate-pulse"/>)}
        </div>
      ) : filtered.length===0 ? (
        <Card className="p-12 text-center">
          <FolderOpen className="h-12 w-12 mx-auto mb-3 text-[var(--gs-muted)]"/>
          <p className="text-sm text-[var(--gs-muted)] mb-4">{search?"Koi project nahi mila":"Pehla project banao"}</p>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={()=>setShowNew(true)}><Plus className="h-3.5 w-3.5 mr-1.5"/>New Project</Button>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map(p=>(
            <Card key={p.id} className="p-4 flex flex-col gap-3 hover:shadow-lg transition-all cursor-pointer group" onClick={()=>setSelectedProject(p)}>
              <div className="flex items-start justify-between">
                <div className="h-10 w-10 rounded-xl grid place-items-center text-xl flex-shrink-0" style={{background:p.color||"#6366f1"}}>{p.icon||"📁"}</div>
                <StatusPill s={p.status}/>
              </div>
              <div className="flex-1">
                <div className="font-semibold text-sm line-clamp-1 group-hover:text-[var(--gs-teal)] transition-colors">{p.name}</div>
                <div className="text-[10px] text-[var(--gs-muted)] mt-1 line-clamp-2">{p.description||"No description"}</div>
              </div>
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="text-[10px]">{PROJECT_TYPES.find(t=>t.value===p.type)?.icon||"📁"} {p.type||"webapp"}</Badge>
                <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1"><Clock className="h-2.5 w-2.5"/>{p.created_at?new Date(p.created_at).toLocaleDateString("en-IN"):""}</span>
              </div>
              <Button size="sm" variant="outline" className="h-7 text-xs w-full opacity-0 group-hover:opacity-100 transition-opacity">
                <Eye className="h-3 w-3 mr-1"/>Open Workspace <ChevronRight className="h-3 w-3 ml-auto"/>
              </Button>
            </Card>
          ))}
        </div>
      )}
      <NewProjectDialog open={showNew} onClose={()=>setShowNew(false)} onCreate={p=>{setShowNew(false);setSelectedProject(p);load();}}/>
    </div>
  );
}
