import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import * as Icons from "lucide-react";
import { Wand2, Loader2, Play, Download, Trash2, ExternalLink, Copy, Sparkles, Plus } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

function useHub() {
  const [hub, setHub] = useState({ counts: {}, categories: [] });
  const load = async () => { try { const r = await api.get("/builder/hub"); setHub(r.data); } catch (e) {} };
  useEffect(() => { load(); }, []);
  return { hub, reload: load };
}

export default function BuildStudio() {
  const { hub, reload: reloadHub } = useHub();
  const [active, setActive] = useState(null); // category id

  return (
    <div className="space-y-6" data-testid="admin-build-studio-page">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2"><Wand2 className="h-7 w-7 text-[var(--gs-teal)]"/> Build Studio</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">One place to build anything — web apps, faceless channels, custom AI agents, mobile apps, full-stack sites, blogs. Preview, download, deploy.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="hub-stats">
        {[["webapps","Web Apps"],["channels","Channels"],["agents","Custom Agents"],["starters","Starters"],["videos","Videos"]].map(([k,l]) => (
          <Card key={k} className="p-4">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase">{l}</div>
            <div className="font-display text-3xl mt-1">{hub.counts?.[k] ?? 0}</div>
          </Card>
        ))}
      </div>

      {/* Categories */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="hub-categories">
        {(hub.categories || []).map((c) => {
          const Icon = Icons[c.icon] || Wand2;
          return (
            <button key={c.id} onClick={() => setActive(c)} data-testid={`build-cat-${c.id}`}
              className="gs-card p-5 text-left hover:bg-[var(--gs-surface-2)] transition group">
              <div className="h-12 w-12 rounded-2xl grid place-items-center" style={{ background: `${c.color}22` }}>
                <Icon className="h-6 w-6" style={{ color: c.color }}/>
              </div>
              <div className="mt-3 font-display text-xl">{c.title}</div>
              <div className="text-xs text-[var(--gs-muted)] mt-1">{c.desc}</div>
              <div className="mt-3 text-xs font-semibold flex items-center gap-1" style={{ color: c.color }}>
                Build <Sparkles className="h-3.5 w-3.5"/>
              </div>
            </button>
          );
        })}
      </div>

      {active && <BuilderDialog category={active} onClose={() => { setActive(null); reloadHub(); }}/>}
    </div>
  );
}

// ============================================================
// Category dialog dispatcher
// ============================================================
function BuilderDialog({ category, onClose }) {
  return (
    <Dialog open={true} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid={`build-dialog-${category.id}`}>
        <DialogHeader>
          <DialogTitle className="font-display text-2xl" style={{ color: category.color }}>{category.title}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-[var(--gs-muted)]">{category.desc}</p>
        {category.id === "webapp"    && <WebAppBuilder color={category.color}/>}
        {category.id === "channel"   && <ChannelBuilder color={category.color}/>}
        {category.id === "agent"     && <AgentBuilder color={category.color}/>}
        {category.id === "mobileapp" && <StarterBuilder color={category.color} kind="mobileapp" placeholder="e.g. Indian food delivery app with tracking + address book"/>}
        {category.id === "fullstack" && <StarterBuilder color={category.color} kind="fullstack" placeholder="e.g. Task manager with categories and due dates"/>}
        {category.id === "blog"      && <StarterBuilder color={category.color} kind="blog" placeholder="e.g. Personal finance blog for Indian millennials"/>}
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// 1) Web App Builder
// ============================================================
function WebAppBuilder({ color }) {
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [projects, setProjects] = useState([]);
  const [previewId, setPreviewId] = useState(null);

  const load = async () => { try { const r = await api.get("/builder/projects"); setProjects(r.data || []); } catch (e) {} };
  useEffect(() => { load(); }, []);

  const build = async () => {
    if (prompt.trim().length < 4) return toast.error("Prompt too short");
    setBusy(true); toast.loading("Building your web app…", { id: "wa", duration: 60000 });
    try {
      const r = await api.post("/builder/projects", { prompt, name });
      toast.success(`Built: ${r.data.name} ✅`, { id: "wa" });
      setPrompt(""); setName(""); setPreviewId(r.data.id); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "wa" }); }
    finally { setBusy(false); }
  };

  const del = async (pid) => { try { await api.delete(`/builder/projects/${pid}`); load(); toast.success("Deleted"); } catch (e) {} };

  return (
    <div className="space-y-4 mt-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Prompt *</label>
        <Textarea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Build a modern landing page for a Kathak dance academy in Jaipur…" data-testid="wa-prompt"/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Name (optional)</label>
        <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="wa-name"/>
      </div>
      <Button onClick={build} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid="wa-build-btn">
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
        {busy ? "Building…" : "Build Web App"}
      </Button>

      <div className="grid md:grid-cols-2 gap-2 max-h-80 overflow-y-auto" data-testid="wa-projects">
        {projects.map((p) => (
          <Card key={p.id} className="p-3 flex items-center gap-2" data-testid={`wa-project-${p.id}`}>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{p.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)] truncate">{p.prompt}</div>
            </div>
            <Button variant="outline" size="sm" onClick={() => setPreviewId(p.id)}><Play className="h-3.5 w-3.5"/></Button>
            <a href={`${BACKEND_URL}/api/builder/projects/${p.id}/download`} className="text-xs" title="Download zip"><Download className="h-4 w-4"/></a>
            <button onClick={() => del(p.id)} className="text-rose-500" data-testid={`wa-del-${p.id}`}><Trash2 className="h-4 w-4"/></button>
          </Card>
        ))}
      </div>

      {previewId && (
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline">Live Preview</Badge>
            <a href={`${BACKEND_URL}/api/builder/projects/${previewId}/preview`} target="_blank" rel="noreferrer" className="text-xs underline flex items-center gap-1"><ExternalLink className="h-3 w-3"/>Open in new tab</a>
          </div>
          <iframe src={`${BACKEND_URL}/api/builder/projects/${previewId}/preview`} className="w-full h-[520px] border rounded-xl bg-white" title="preview" data-testid="wa-preview-iframe"/>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 2) Faceless Channel Builder
// ============================================================
function ChannelBuilder({ color }) {
  const [niche, setNiche] = useState("");
  const [style, setStyle] = useState("energetic");
  const [freq, setFreq] = useState(5);
  const [lang, setLang] = useState("hinglish");
  const [orientation, setOrientation] = useState("9:16");
  const [busy, setBusy] = useState(false);
  const [channels, setChannels] = useState([]);
  const [active, setActive] = useState(null);

  const load = async () => { try { const r = await api.get("/builder/channel"); setChannels(r.data.items || []); } catch (e) {} };
  useEffect(() => { load(); }, []);

  const plan = async () => {
    if (niche.trim().length < 3) return toast.error("Niche too short");
    setBusy(true); toast.loading("Planning your 30-day channel…", { id: "ch", duration: 60000 });
    try {
      const r = await api.post("/builder/channel/plan", { niche, style, posts_per_week: Number(freq), language: lang, orientation });
      toast.success(`Channel "${r.data.plan?.channel_name}" ready ✅`, { id: "ch" });
      setActive(r.data); setNiche(""); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "ch" }); }
    finally { setBusy(false); }
  };

  const execute = async (cid, max) => {
    toast.loading(`Queuing ${max} videos…`, { id: `ex${cid}` });
    try {
      const r = await api.post("/builder/channel/execute", { channel_id: cid, max_videos: max });
      toast.success(`${r.data.count} videos queued → Video Studio ✅`, { id: `ex${cid}` });
      load();
    } catch (e) { toast.error("Execute failed", { id: `ex${cid}` }); }
  };
  const del = async (cid) => { try { await api.delete(`/builder/channel/${cid}`); load(); toast.success("Deleted"); } catch (e) {} };

  return (
    <div className="space-y-4 mt-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Niche *</label>
        <Input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="e.g. AI tools for Indian students · Personal finance · Indian street food" data-testid="ch-niche"/>
      </div>
      <div className="grid md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Style</label>
          <Select value={style} onValueChange={setStyle}><SelectTrigger data-testid="ch-style"><SelectValue/></SelectTrigger>
            <SelectContent>{["energetic","calm","witty","authoritative","inspirational","story-driven"].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Posts / week</label>
          <Input type="number" value={freq} onChange={(e) => setFreq(e.target.value)} min={1} max={7} data-testid="ch-freq"/>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Language</label>
          <Select value={lang} onValueChange={setLang}><SelectTrigger data-testid="ch-lang"><SelectValue/></SelectTrigger>
            <SelectContent><SelectItem value="hinglish">Hinglish</SelectItem><SelectItem value="hindi">Hindi</SelectItem><SelectItem value="english">English</SelectItem></SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Orientation</label>
          <Select value={orientation} onValueChange={setOrientation}><SelectTrigger data-testid="ch-orient"><SelectValue/></SelectTrigger>
            <SelectContent><SelectItem value="9:16">9:16 Shorts</SelectItem><SelectItem value="16:9">16:9 Long</SelectItem><SelectItem value="1:1">1:1 Post</SelectItem></SelectContent>
          </Select>
        </div>
      </div>
      <Button onClick={plan} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid="ch-plan-btn">
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
        {busy ? "Planning…" : "Plan 30-day Channel"}
      </Button>

      <div className="space-y-2 max-h-80 overflow-y-auto" data-testid="ch-list">
        {channels.map((c) => (
          <Card key={c.id} className="p-3" data-testid={`ch-item-${c.id}`}>
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm truncate">{c.plan?.channel_name || c.niche}</div>
                <div className="text-[10px] text-[var(--gs-muted)]">{c.plan?.videos?.length || 0} videos planned · {c.status} · {c.executed_video_ids?.length || 0} executed</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => setActive(c)} data-testid={`ch-view-${c.id}`}>Calendar</Button>
              <Button size="sm" style={{ background: color, color: "white" }} onClick={() => execute(c.id, 5)} data-testid={`ch-exec-${c.id}`}>Execute 5</Button>
              <button onClick={() => del(c.id)} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
            </div>
          </Card>
        ))}
      </div>

      {active && (
        <Card className="p-4 mt-2" data-testid="ch-calendar-panel">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-display text-lg">{active.plan?.channel_name}</h4>
            <button onClick={() => setActive(null)} className="text-[var(--gs-muted)]">✕</button>
          </div>
          <div className="text-xs text-[var(--gs-muted)] mb-3">{active.plan?.channel_bio}</div>
          <div className="grid gap-1 max-h-72 overflow-y-auto">
            {(active.plan?.videos || []).map((v, i) => (
              <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
                <Badge variant="outline" className="text-[9px]">Day {v.day}</Badge>
                <span className="flex-1 truncate">{v.topic}</span>
                <Badge variant="secondary" className="text-[9px]">{v.format || "reel"}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================
// 3) Custom AI Agent Builder
// ============================================================
function AgentBuilder({ color }) {
  const [form, setForm] = useState({ name: "", role: "", system_prompt: "", param_keys_csv: "input", color: color, icon: "Bot" });
  const [busy, setBusy] = useState(false);
  const [agents, setAgents] = useState([]);
  const [active, setActive] = useState(null);
  const [runParams, setRunParams] = useState({});
  const [runOut, setRunOut] = useState(null);
  const [running, setRunning] = useState(false);

  const load = async () => { try { const r = await api.get("/builder/agent"); setAgents(r.data.items || []); } catch (e) {} };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (form.name.trim().length < 2) return toast.error("Name too short");
    if (form.system_prompt.trim().length < 20) return toast.error("System prompt too short");
    setBusy(true); toast.loading("Saving agent…", { id: "ag" });
    try {
      const param_keys = form.param_keys_csv.split(",").map(s => s.trim()).filter(Boolean);
      await api.post("/builder/agent", { ...form, param_keys });
      toast.success(`${form.name} created ✅`, { id: "ag" });
      setForm({ name: "", role: "", system_prompt: "", param_keys_csv: "input", color, icon: "Bot" });
      await load();
    } catch (e) { toast.error("Create failed", { id: "ag" }); }
    finally { setBusy(false); }
  };

  const openRunner = (a) => { setActive(a); setRunOut(null); const p = {}; (a.param_keys || []).forEach(k => p[k] = ""); setRunParams(p); };
  const run = async () => {
    setRunning(true); toast.loading("Running…", { id: "rn" });
    try {
      const r = await api.post(`/builder/agent/${active.id}/run`, { params: runParams });
      setRunOut(r.data); toast.success("Done ✅", { id: "rn" });
    } catch (e) { toast.error("Run failed", { id: "rn" }); }
    finally { setRunning(false); }
  };

  return (
    <div className="space-y-4 mt-4">
      <Card className="p-4 space-y-3">
        <div className="text-sm font-semibold flex items-center gap-2"><Plus className="h-4 w-4"/>Create custom agent</div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Agent name *</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Blog Writer Bot" data-testid="ag-name"/>
          </div>
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Role description</label>
            <Input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="Writes SEO-optimized Hindi blog posts" data-testid="ag-role"/>
          </div>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">System prompt *</label>
          <Textarea rows={4} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            placeholder="You are a blog writer for Indian audiences. Given a topic, output JSON: {title, intro, sections:[{h2, body}], conclusion, tags}."
            data-testid="ag-sys"/>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Input parameter names (comma-separated)</label>
          <Input value={form.param_keys_csv} onChange={(e) => setForm({ ...form, param_keys_csv: e.target.value })} placeholder="topic, audience, tone" data-testid="ag-params"/>
        </div>
        <Button onClick={create} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid="ag-create-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Plus className="h-4 w-4 mr-2"/>}
          {busy ? "Saving…" : "Create Agent"}
        </Button>
      </Card>

      <div className="space-y-2">
        <div className="text-sm font-semibold">Your custom agents · {agents.length}</div>
        {agents.length === 0 && <Card className="p-4 text-center text-xs text-[var(--gs-muted)]">No custom agents yet.</Card>}
        <div className="grid md:grid-cols-2 gap-2">
          {agents.map((a) => (
            <Card key={a.id} className="p-3 flex items-center gap-2" data-testid={`ag-card-${a.id}`}>
              <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: `${a.color}22` }}>
                <Icons.Bot className="h-4 w-4" style={{ color: a.color }}/>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{a.name}</div>
                <div className="text-[10px] text-[var(--gs-muted)] truncate">{a.role}</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => openRunner(a)} data-testid={`ag-run-${a.id}`}><Play className="h-3.5 w-3.5"/></Button>
              <button onClick={async () => { await api.delete(`/builder/agent/${a.id}`); load(); }} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
            </Card>
          ))}
        </div>
      </div>

      {active && (
        <Card className="p-4 mt-2" data-testid="ag-runner-panel">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-display text-lg">{active.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)]">{active.role}</div>
            </div>
            <button onClick={() => setActive(null)} className="text-[var(--gs-muted)]">✕</button>
          </div>
          {(active.param_keys || []).map((k) => (
            <div key={k} className="mb-2">
              <label className="text-xs text-[var(--gs-muted)] capitalize">{k}</label>
              <Textarea rows={2} value={runParams[k] ?? ""} onChange={(e) => setRunParams({ ...runParams, [k]: e.target.value })} data-testid={`ag-param-${k}`}/>
            </div>
          ))}
          <Button onClick={run} disabled={running} className="w-full text-white" style={{ background: color }} data-testid="ag-run-btn">
            {running ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Play className="h-4 w-4 mr-2"/>}Run
          </Button>
          {runOut && (
            <pre className="mt-3 text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl max-h-64 overflow-auto" data-testid="ag-output">
              {JSON.stringify(runOut.parsed || runOut, null, 2)}
            </pre>
          )}
        </Card>
      )}
    </div>
  );
}

// ============================================================
// 4-6) Starter Kit builders (mobileapp / fullstack / blog)
// ============================================================
function StarterBuilder({ color, kind, placeholder }) {
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState([]);

  const load = async () => { try { const r = await api.get("/builder/starter"); setItems((r.data.items || []).filter(x => x.kind === kind)); } catch (e) {} };
  useEffect(() => { load(); }, [kind]);

  const build = async () => {
    if (prompt.trim().length < 4) return toast.error("Prompt too short");
    setBusy(true); toast.loading("Generating starter kit…", { id: "st", duration: 60000 });
    try {
      const r = await api.post("/builder/starter", { kind, prompt, app_name: name });
      toast.success(`Ready · ${(r.data.size_bytes / 1024).toFixed(1)} KB ✅`, { id: "st" });
      setPrompt(""); setName(""); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "st" }); }
    finally { setBusy(false); }
  };

  const del = async (sid) => { try { await api.delete(`/builder/starter/${sid}`); load(); toast.success("Deleted"); } catch (e) {} };

  return (
    <div className="space-y-4 mt-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Prompt *</label>
        <Textarea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder={placeholder} data-testid={`st-${kind}-prompt`}/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">App name (optional)</label>
        <Input value={name} onChange={(e) => setName(e.target.value)} data-testid={`st-${kind}-name`}/>
      </div>
      <Button onClick={build} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid={`st-${kind}-build`}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Download className="h-4 w-4 mr-2"/>}
        {busy ? "Building starter…" : "Generate Starter Kit"}
      </Button>

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {items.map((it) => (
          <Card key={it.id} className="p-3 flex items-center gap-2" data-testid={`st-${kind}-item-${it.id}`}>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{it.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)] truncate">{it.prompt}</div>
            </div>
            <Badge variant="outline" className="text-[10px]">{(it.size_bytes / 1024).toFixed(1)} KB</Badge>
            <a href={`${BACKEND_URL}${it.download_url}`} download className="text-xs" title="Download"><Download className="h-4 w-4"/></a>
            <button onClick={() => del(it.id)} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
          </Card>
        ))}
      </div>

      {kind === "mobileapp" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to run:</strong> Unzip → <code>npm install</code> → <code>npx expo start</code> → scan QR with Expo Go app.
        </div>
      )}
      {kind === "fullstack" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to run:</strong> Unzip → <code>docker compose up --build</code> → Backend at :8001, Frontend at :5173.
        </div>
      )}
      {kind === "blog" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to deploy:</strong> Unzip → drag folder to Netlify/Vercel drop, or open <code>index.html</code> locally.
        </div>
      )}
    </div>
  );
}
