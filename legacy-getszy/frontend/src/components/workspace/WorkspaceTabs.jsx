import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import {
  Sparkles, ListChecks, ClipboardList, FolderOpen, Eye, Clock, GitBranch,
  Rocket, Plus, Trash2, Check, Circle, CircleDot, Loader2, RefreshCw,
  ExternalLink, FileText, Film, PenTool, Globe, Youtube, Bot, Layers,
  TrendingUp, Zap, Flame, Briefcase, Package, Smartphone, BookOpen,
  Pin, PinOff, Download, Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { ListSkeleton, EmptyState } from "@/components/ux/Skeletons";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const KIND_ICONS = {
  script: PenTool, hook_score: Zap, viral_score: Flame, trends: TrendingUp,
  competitor_gap: TrendingUp, video_job: Film, channel_plan: Youtube,
  webapp: Globe, starter_mobileapp: Smartphone, starter_fullstack: Layers,
  starter_blog: BookOpen, workforce_run: Briefcase, sourcing_scan: Package,
  error: Zap,
};

const STATUS_META = {
  todo:    { label: "To do",   Icon: Circle,     color: "text-[var(--gs-muted)]" },
  doing:   { label: "Doing",   Icon: CircleDot,  color: "text-[var(--gs-teal)]" },
  done:    { label: "Done",    Icon: Check,      color: "text-emerald-600" },
  blocked: { label: "Blocked", Icon: Zap,        color: "text-rose-600" },
};

// ============================================================
// Root
// ============================================================
export default function WorkspaceTabs({ projectId, assets, activeAsset, setActiveAsset, renderAssetPreview }) {
  const [tab, setTab] = useState("preview");
  const [ws, setWs] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadWorkspace = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const r = await api.get(`/workspace/${projectId}`);
      setWs(r.data);
    } catch (e) { /* silent */ }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { loadWorkspace(); }, [loadWorkspace]);

  const tabItems = [
    { v: "preview",     label: "Preview",     Icon: Eye },
    { v: "plan",        label: "Plan",        Icon: ClipboardList },
    { v: "tasks",       label: "Tasks",       Icon: ListChecks },
    { v: "files",       label: "Files",       Icon: FolderOpen },
    { v: "timeline",    label: "Timeline",    Icon: Clock },
    { v: "versions",    label: "Versions",    Icon: GitBranch },
    { v: "deployments", label: "Deploy",      Icon: Rocket },
  ];

  return (
    <Card className="col-span-12 lg:col-span-5 flex flex-col overflow-hidden" data-testid="workspace-tabs-panel">
      <Tabs value={tab} onValueChange={setTab} className="flex flex-col h-full">
        <div className="p-2 border-b flex items-center gap-2" style={{ borderColor: "var(--gs-border)" }}>
          <Sparkles className="h-4 w-4 text-[var(--gs-teal)] shrink-0"/>
          <div className="font-semibold text-sm mr-2">Workspace</div>
          <TabsList className="bg-[var(--gs-surface-2)] p-0.5 gap-0.5 h-auto flex-wrap">
            {tabItems.map(t => (
              <TabsTrigger key={t.v} value={t.v}
                className="text-[10px] px-2 py-1 gap-1 data-[state=active]:bg-[var(--gs-teal)] data-[state=active]:text-white"
                data-testid={`ws-tab-${t.v}`}>
                <t.Icon className="h-3 w-3"/>{t.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <button onClick={loadWorkspace} className="ml-auto text-[var(--gs-muted)] hover:text-[var(--gs-teal)] p-1" title="Refresh" data-testid="ws-refresh">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <TabsContent value="preview" className="p-3 m-0" data-testid="ws-preview-content">
            <PreviewTab assets={assets} activeAsset={activeAsset} setActiveAsset={setActiveAsset} renderAssetPreview={renderAssetPreview}/>
          </TabsContent>
          <TabsContent value="plan" className="p-3 m-0" data-testid="ws-plan-content">
            <PlanTab projectId={projectId} plan={ws?.plan} onSaved={loadWorkspace} loading={loading}/>
          </TabsContent>
          <TabsContent value="tasks" className="p-3 m-0" data-testid="ws-tasks-content">
            <TasksTab projectId={projectId} tasks={ws?.tasks || []} onChanged={loadWorkspace} loading={loading}/>
          </TabsContent>
          <TabsContent value="files" className="p-3 m-0" data-testid="ws-files-content">
            <FilesTab projectId={projectId} assets={assets} setActiveAsset={(a) => { setActiveAsset(a); setTab("preview"); }} onChanged={loadWorkspace} loading={loading && !ws}/>
          </TabsContent>
          <TabsContent value="timeline" className="p-3 m-0" data-testid="ws-timeline-content">
            <TimelineTab projectId={projectId}/>
          </TabsContent>
          <TabsContent value="versions" className="p-3 m-0" data-testid="ws-versions-content">
            <VersionsTab projectId={projectId} versions={ws?.versions || []} onChanged={loadWorkspace} loading={loading}/>
          </TabsContent>
          <TabsContent value="deployments" className="p-3 m-0" data-testid="ws-deployments-content">
            <DeploymentsTab projectId={projectId} deployments={ws?.deployments || []} assets={assets} loading={loading} onChanged={loadWorkspace}/>
          </TabsContent>
        </div>
      </Tabs>
    </Card>
  );
}

// ============================================================
// Preview tab (existing asset preview + tab strip)
// ============================================================
function PreviewTab({ assets, activeAsset, setActiveAsset, renderAssetPreview }) {
  if (!assets || assets.length === 0) {
    return <EmptyState icon={Eye} title="No preview yet" subtitle="Neo se kuch bhi banao — script, video, webapp — output yahan preview hoga."/>;
  }
  return (
    <div>
      <div className="flex flex-wrap gap-1 mb-3 pb-2 border-b" style={{ borderColor: "var(--gs-border)" }} data-testid="preview-asset-strip">
        {assets.map((a) => {
          const Icon = KIND_ICONS[a.kind] || Sparkles;
          const on = activeAsset?.id === a.id;
          return (
            <button key={a.id} onClick={() => setActiveAsset(a)}
              className={`text-[10px] px-2 py-1 rounded-lg flex items-center gap-1 transition ${on ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}
              data-testid={`preview-strip-${a.id}`}>
              <Icon className="h-3 w-3"/>
              <span className="truncate max-w-[100px]">{a.title || a.kind}</span>
            </button>
          );
        })}
      </div>
      {activeAsset ? renderAssetPreview(activeAsset) : (
        <div className="text-center text-xs text-[var(--gs-muted)] py-8">Select an asset above.</div>
      )}
    </div>
  );
}

// ============================================================
// Plan tab
// ============================================================
function PlanTab({ projectId, plan, onSaved, loading }) {
  const [summary, setSummary] = useState("");
  const [steps, setSteps] = useState("");
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [edit, setEdit] = useState(false);

  useEffect(() => {
    setSummary(plan?.summary || "");
    setSteps((plan?.steps || []).join("\n"));
  }, [plan?.summary, plan?.steps]);

  const save = async () => {
    if (!summary.trim()) { toast.error("Summary khaali nahi ho sakta"); return; }
    setSaving(true);
    try {
      const arr = steps.split("\n").map(s => s.trim()).filter(Boolean);
      await api.put(`/workspace/${projectId}/plan`, { summary: summary.trim(), steps: arr });
      toast.success("Plan saved");
      setEdit(false);
      await onSaved?.();
    } catch (e) { toast.error("Save failed"); }
    finally { setSaving(false); }
  };

  const generateFromChat = async () => {
    setGenerating(true);
    toast.loading("Neo generating plan from chat…", { id: "plangen", duration: 30000 });
    try {
      const r = await api.post(`/workspace/${projectId}/plan/generate`);
      toast.success("Plan generated", { id: "plangen" });
      setSummary(r.data.summary || "");
      setSteps((r.data.steps || []).join("\n"));
      setEdit(false);
      await onSaved?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Generation failed", { id: "plangen" });
    } finally { setGenerating(false); }
  };

  if (loading && !plan) return <ListSkeleton rows={4}/>;

  if (!plan && !edit) {
    return (
      <div>
        <EmptyState icon={ClipboardList} title="No plan yet"
          subtitle="Apne project ka roadmap yahan likho — Neo bhi isko refer karega."/>
        <div className="text-center mt-3 flex justify-center gap-2 flex-wrap">
          <Button size="sm" onClick={() => setEdit(true)} data-testid="plan-create-btn">
            <Plus className="h-3 w-3 mr-1"/>Create manually
          </Button>
          <Button size="sm" onClick={generateFromChat} disabled={generating} variant="outline" data-testid="plan-generate-btn">
            {generating ? <Loader2 className="h-3 w-3 mr-1 animate-spin"/> : <Wand2 className="h-3 w-3 mr-1"/>}
            Generate from chat
          </Button>
        </div>
      </div>
    );
  }

  if (edit) {
    return (
      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
        <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Summary</div>
        <Textarea rows={3} value={summary} onChange={(e) => setSummary(e.target.value)}
          placeholder="One-paragraph project summary…" className="mb-3" data-testid="plan-summary-input"/>
        <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Steps (one per line)</div>
        <Textarea rows={8} value={steps} onChange={(e) => setSteps(e.target.value)}
          placeholder={"1. Research topic\n2. Write script\n3. Generate video"} className="mb-3 font-mono text-xs" data-testid="plan-steps-input"/>
        <div className="flex gap-2">
          <Button size="sm" onClick={save} disabled={saving} className="bg-[var(--gs-teal)]" data-testid="plan-save-btn">
            {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1"/> : <Check className="h-3 w-3 mr-1"/>}Save
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEdit(false)} data-testid="plan-cancel-btn">Cancel</Button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.2 }}>
      <div className="flex items-start gap-2 mb-3">
        <div className="flex-1 text-sm whitespace-pre-wrap" data-testid="plan-summary-view">{plan.summary}</div>
        <div className="flex flex-col gap-1 shrink-0">
          <Button size="sm" variant="outline" onClick={() => setEdit(true)} data-testid="plan-edit-btn">Edit</Button>
          <Button size="sm" variant="ghost" onClick={generateFromChat} disabled={generating} className="text-[10px] h-7" data-testid="plan-regen-btn">
            {generating ? <Loader2 className="h-3 w-3 mr-1 animate-spin"/> : <Wand2 className="h-3 w-3 mr-1"/>}
            Regenerate
          </Button>
        </div>
      </div>
      {plan.steps?.length > 0 && (
        <ol className="space-y-1.5 mt-2" data-testid="plan-steps-view">
          {plan.steps.map((s, i) => (
            <li key={i} className="text-xs flex items-start gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
              <Badge variant="outline" className="text-[9px] shrink-0 mt-0.5">{i + 1}</Badge>
              <span>{s}</span>
            </li>
          ))}
        </ol>
      )}
      {plan.updated_at && (
        <div className="text-[10px] text-[var(--gs-muted)] mt-3">Updated {new Date(plan.updated_at).toLocaleString()}</div>
      )}
    </motion.div>
  );
}

// ============================================================
// Tasks tab
// ============================================================
function TasksTab({ projectId, tasks, onChanged, loading }) {
  const [title, setTitle] = useState("");
  const [adding, setAdding] = useState(false);
  const [filter, setFilter] = useState("all");

  const grouped = useMemo(() => {
    const g = { todo: [], doing: [], done: [], blocked: [] };
    (tasks || []).forEach(t => (g[t.status] || g.todo).push(t));
    return g;
  }, [tasks]);

  const shown = filter === "all" ? (tasks || []) : ((tasks || []).filter(t => t.status === filter));

  const add = async () => {
    const t = title.trim();
    if (t.length < 2) return;
    setAdding(true);
    try {
      await api.post(`/workspace/${projectId}/task`, { title: t });
      setTitle("");
      await onChanged?.();
    } catch (e) { toast.error("Add failed"); }
    finally { setAdding(false); }
  };

  const cycleStatus = async (task) => {
    const order = ["todo", "doing", "done", "blocked"];
    const next = order[(order.indexOf(task.status) + 1) % order.length];
    try {
      await api.patch(`/workspace/${projectId}/task/${task.id}`, { status: next });
      await onChanged?.();
    } catch (e) { toast.error("Update failed"); }
  };

  const del = async (task) => {
    try {
      await api.delete(`/workspace/${projectId}/task/${task.id}`);
      toast.success("Task deleted");
      await onChanged?.();
    } catch (e) { toast.error("Delete failed"); }
  };

  if (loading && (!tasks || tasks.length === 0)) return <ListSkeleton rows={4}/>;

  return (
    <div>
      <div className="flex gap-1 mb-3" data-testid="tasks-add-row">
        <Input value={title} onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") add(); }}
          placeholder="Add a task…" className="text-xs h-9" data-testid="tasks-add-input"/>
        <Button size="sm" onClick={add} disabled={adding || title.trim().length < 2} className="bg-[var(--gs-teal)]" data-testid="tasks-add-btn">
          {adding ? <Loader2 className="h-3 w-3 animate-spin"/> : <Plus className="h-3 w-3"/>}
        </Button>
      </div>

      <div className="flex flex-wrap gap-1 mb-3 text-[10px]">
        {["all", "todo", "doing", "done", "blocked"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-2 py-0.5 rounded-full uppercase tracking-wider ${filter === f ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}
            data-testid={`tasks-filter-${f}`}>
            {f} {f !== "all" && `(${grouped[f]?.length || 0})`}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <EmptyState icon={ListChecks} title="No tasks" subtitle={filter === "all" ? "Pehla task add karo upar." : `No ${filter} tasks.`}/>
      ) : (
        <AnimatePresence initial={false}>
          <ul className="space-y-1.5" data-testid="tasks-list">
            {shown.map(task => {
              const S = STATUS_META[task.status] || STATUS_META.todo;
              return (
                <motion.li key={task.id}
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -6 }}
                  transition={{ duration: 0.15 }}
                  className="group text-xs p-2 rounded-lg bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] flex items-center gap-2"
                  data-testid={`task-${task.id}`}>
                  <button onClick={() => cycleStatus(task)} className={S.color} title={`Status: ${S.label}`} data-testid={`task-status-${task.id}`}>
                    <S.Icon className="h-4 w-4"/>
                  </button>
                  <span className={`flex-1 ${task.status === "done" ? "line-through text-[var(--gs-muted)]" : ""}`}>{task.title}</span>
                  <Badge variant="outline" className="text-[9px]">{S.label}</Badge>
                  <button onClick={() => del(task)} className="opacity-0 group-hover:opacity-100 text-rose-500" title="Delete" data-testid={`task-del-${task.id}`}>
                    <Trash2 className="h-3 w-3"/>
                  </button>
                </motion.li>
              );
            })}
          </ul>
        </AnimatePresence>
      )}
    </div>
  );
}

// ============================================================
// Files tab
// ============================================================
function FilesTab({ projectId, assets, setActiveAsset, onChanged, loading }) {
  const [filter, setFilter] = useState("all"); // all | pinned
  const backend = process.env.REACT_APP_BACKEND_URL || "";

  const shown = useMemo(() => {
    const list = assets || [];
    const filtered = filter === "pinned" ? list.filter(a => a.pinned) : list;
    // pinned first
    return [...filtered].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
  }, [assets, filter]);

  const pinnedCount = (assets || []).filter(a => a.pinned).length;

  const togglePin = async (a) => {
    try {
      await api.patch(`/workspace/${projectId}/asset/${a.id}/pin`, { pinned: !a.pinned });
      toast.success(a.pinned ? "Unpinned" : "Pinned");
      await onChanged?.();
    } catch (e) { toast.error("Pin toggle failed"); }
  };

  const downloadUrl = (a) => {
    const d = a.data || {};
    if (a.kind === "webapp" && d.project_id) return `${backend}/api/builder/projects/${d.project_id}/download`;
    if (a.kind?.startsWith("starter_") && d.download_url) return `${backend}${d.download_url}`;
    if (a.kind === "video_job" && d.status_endpoint) return null; // video handled in preview
    return null;
  };

  if (loading) return <ListSkeleton rows={4}/>;
  if (!assets || assets.length === 0) {
    return <EmptyState icon={FolderOpen} title="No files" subtitle="Assets (scripts, videos, webapps) yahan appear honge jaise Neo banayega."/>;
  }
  return (
    <div>
      <div className="flex gap-1 mb-3 text-[10px]" data-testid="files-filters">
        <button onClick={() => setFilter("all")}
          className={`px-2 py-0.5 rounded-full uppercase tracking-wider ${filter === "all" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}
          data-testid="files-filter-all">All ({assets.length})</button>
        <button onClick={() => setFilter("pinned")}
          className={`px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1 ${filter === "pinned" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)]"}`}
          data-testid="files-filter-pinned"><Pin className="h-2.5 w-2.5"/>Pinned ({pinnedCount})</button>
      </div>
      {shown.length === 0 ? (
        <EmptyState icon={Pin} title="No pinned files" subtitle="Kisi bhi file ko pin karo — quick access ke liye."/>
      ) : (
        <div className="space-y-1.5" data-testid="files-list">
          {shown.map(a => {
            const Icon = KIND_ICONS[a.kind] || FileText;
            const dl = downloadUrl(a);
            return (
              <div key={a.id} className="group text-xs p-2.5 rounded-lg bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] flex items-center gap-2 transition"
                data-testid={`file-${a.id}`}>
                <button onClick={() => setActiveAsset(a)} className="h-8 w-8 shrink-0 rounded-lg grid place-items-center bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/20">
                  <Icon className="h-4 w-4"/>
                </button>
                <button onClick={() => setActiveAsset(a)} className="flex-1 min-w-0 text-left">
                  <div className="font-medium truncate flex items-center gap-1">
                    {a.pinned && <Pin className="h-2.5 w-2.5 text-amber-500 shrink-0"/>}
                    {a.title || a.kind}
                  </div>
                  <div className="text-[10px] text-[var(--gs-muted)]">{a.kind} · {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}</div>
                </button>
                <button onClick={() => togglePin(a)}
                  className={`shrink-0 p-1 rounded ${a.pinned ? "text-amber-500 hover:text-amber-600" : "text-[var(--gs-muted)] opacity-0 group-hover:opacity-100 hover:text-[var(--gs-teal)]"}`}
                  title={a.pinned ? "Unpin" : "Pin"} data-testid={`file-pin-${a.id}`}>
                  {a.pinned ? <PinOff className="h-3.5 w-3.5"/> : <Pin className="h-3.5 w-3.5"/>}
                </button>
                {dl && (
                  <a href={dl} download onClick={(e) => e.stopPropagation()}
                    className="shrink-0 p-1 rounded text-[var(--gs-muted)] opacity-0 group-hover:opacity-100 hover:text-[var(--gs-teal)]"
                    title="Download" data-testid={`file-dl-${a.id}`}>
                    <Download className="h-3.5 w-3.5"/>
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Timeline tab
// ============================================================
function TimelineTab({ projectId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const r = await api.get(`/workspace/${projectId}/timeline?limit=100`);
      setItems(r.data.items || []);
    } catch (e) { /* silent */ }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <ListSkeleton rows={5}/>;
  if (items.length === 0) return <EmptyState icon={Clock} title="Timeline empty" subtitle="Messages, assets, events sab yahan chronologically dikhega."/>;

  const TYPE_META = {
    message:    { color: "bg-[var(--gs-teal)]",  label: "Message" },
    asset:      { color: "bg-emerald-500",       label: "Asset" },
    event:      { color: "bg-amber-500",         label: "Event" },
    deployment: { color: "bg-violet-500",        label: "Deploy" },
  };

  return (
    <div className="relative pl-4" data-testid="timeline-list">
      <div className="absolute left-1.5 top-1 bottom-1 w-px bg-[var(--gs-border)]"/>
      <ul className="space-y-3">
        {items.map((it, i) => {
          const meta = TYPE_META[it.type] || TYPE_META.event;
          const d = it.data || {};
          let label = "";
          if (it.type === "message") label = `${d.role === "user" ? "You" : "Neo"}: ${(d.content || "").slice(0, 120)}`;
          else if (it.type === "asset") label = `Created ${d.kind}${d.title ? ` — ${d.title}` : ""}`;
          else if (it.type === "event") label = `${d.kind || "event"}${d.payload?.msg ? " — " + d.payload.msg : ""}`;
          else if (it.type === "deployment") label = `Deployed ${d.kind || ""} → ${d.target || ""}`;
          return (
            <li key={i} className="relative text-xs" data-testid={`timeline-${i}`}>
              <span className={`absolute -left-3.5 top-1 h-2.5 w-2.5 rounded-full ${meta.color} ring-2 ring-white`}/>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[9px]">{meta.label}</Badge>
                <span className="text-[10px] text-[var(--gs-muted)]">{it.at ? new Date(it.at).toLocaleString() : ""}</span>
              </div>
              <div className="mt-1 text-[var(--gs-fg)]">{label}</div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ============================================================
// Versions tab
// ============================================================
function VersionsTab({ projectId, versions, onChanged, loading }) {
  const [label, setLabel] = useState("");
  const [snap, setSnap] = useState(false);

  const create = async () => {
    setSnap(true);
    try {
      await api.post(`/workspace/${projectId}/version`, { label: label.trim() || null });
      toast.success("Snapshot saved");
      setLabel("");
      await onChanged?.();
    } catch (e) { toast.error("Snapshot failed"); }
    finally { setSnap(false); }
  };

  return (
    <div>
      <div className="flex gap-1 mb-3">
        <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (optional)" className="text-xs h-9" data-testid="versions-label-input"/>
        <Button size="sm" onClick={create} disabled={snap} className="bg-[var(--gs-teal)]" data-testid="versions-snap-btn">
          {snap ? <Loader2 className="h-3 w-3 animate-spin"/> : <><GitBranch className="h-3 w-3 mr-1"/>Snapshot</>}
        </Button>
      </div>
      {loading && (!versions || versions.length === 0) ? <ListSkeleton rows={3}/> :
        versions.length === 0 ? <EmptyState icon={GitBranch} title="No versions" subtitle="Snapshot lo taaki wapas iss state pe aa sako."/> :
        <ul className="space-y-1.5" data-testid="versions-list">
          {versions.map(v => (
            <li key={v.id} className="text-xs p-2 rounded-lg bg-[var(--gs-surface-2)]" data-testid={`version-${v.id}`}>
              <div className="flex items-center gap-2">
                <GitBranch className="h-3.5 w-3.5 text-[var(--gs-teal)]"/>
                <span className="font-semibold">{v.label}</span>
                <Badge variant="outline" className="text-[9px] ml-auto">{v.message_count} msg · {v.asset_count} asset</Badge>
              </div>
              <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{new Date(v.created_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      }
    </div>
  );
}

// ============================================================
// Deployments tab
// ============================================================
function DeploymentsTab({ projectId, deployments, assets, loading, onChanged }) {
  const [sites, setSites] = useState([]);
  const [busy, setBusy] = useState(false);
  const [caddy, setCaddy] = useState("");
  const [showCaddy, setShowCaddy] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [slugDraft, setSlugDraft] = useState("");

  const backend = process.env.REACT_APP_BACKEND_URL || "";

  const webappAssets = useMemo(() => (assets || []).filter(a => a.kind === "webapp"), [assets]);

  useEffect(() => {
    if (webappAssets.length && !selectedAssetId) setSelectedAssetId(webappAssets[0].id);
  }, [webappAssets, selectedAssetId]);

  const loadSites = useCallback(async () => {
    try {
      const r = await api.get("/hosting/list");
      const projectSites = (r.data.items || []).filter(s => s.project_id === projectId);
      setSites(projectSites);
    } catch (e) { /* silent */ }
  }, [projectId]);

  useEffect(() => { loadSites(); }, [loadSites]);

  const deploy = async () => {
    if (!selectedAssetId) { toast.error("Select a webapp asset"); return; }
    setBusy(true);
    try {
      const r = await api.post("/hosting/deploy", {
        project_id: projectId,
        asset_id: selectedAssetId,
        slug: slugDraft.trim() || null,
      });
      toast.success(`Deployed → ${r.data.slug}.getszy.com`);
      setSlugDraft("");
      await loadSites();
      await onChanged?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Deploy failed");
    } finally { setBusy(false); }
  };

  const undeploy = async (slug) => {
    if (!confirm(`Undeploy ${slug}? URL will stop working.`)) return;
    try {
      await api.delete(`/hosting/${slug}`);
      toast.success("Undeployed");
      await loadSites();
      await onChanged?.();
    } catch (e) { toast.error("Undeploy failed"); }
  };

  const copyUrl = async (url) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("URL copied");
    } catch (e) { toast.error("Copy failed"); }
  };

  const loadCaddy = async () => {
    if (caddy) { setShowCaddy(s => !s); return; }
    try {
      const r = await api.get("/hosting/caddy-snippet", { responseType: "text" });
      setCaddy(typeof r.data === "string" ? r.data : String(r.data));
      setShowCaddy(true);
    } catch (e) { toast.error("Failed to load Caddy snippet"); }
  };

  if (loading && (!deployments || deployments.length === 0) && sites.length === 0) return <ListSkeleton rows={3}/>;

  return (
    <div>
      {/* Deploy form */}
      <div className="p-3 rounded-lg bg-[var(--gs-teal)]/8 border border-[var(--gs-teal)]/20 mb-3" data-testid="deploy-form">
        <div className="flex items-center gap-2 mb-2">
          <Rocket className="h-4 w-4 text-[var(--gs-teal)]"/>
          <div className="font-semibold text-sm">One-click deploy</div>
        </div>
        {webappAssets.length === 0 ? (
          <div className="text-[11px] text-[var(--gs-muted)]">
            Build a webapp first (Neo se "build a landing page…" bolo), phir yahan deploy button aayega.
          </div>
        ) : (
          <div className="space-y-2">
            <div>
              <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Choose webapp</div>
              <select value={selectedAssetId} onChange={(e) => setSelectedAssetId(e.target.value)}
                className="w-full text-xs h-9 rounded-lg border bg-white px-2" style={{ borderColor: "var(--gs-border)" }}
                data-testid="deploy-asset-select">
                {webappAssets.map(a => <option key={a.id} value={a.id}>{a.title || a.kind}</option>)}
              </select>
            </div>
            <div>
              <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Subdomain (optional)</div>
              <div className="flex items-center gap-1">
                <Input value={slugDraft} onChange={(e) => setSlugDraft(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                  placeholder="my-project" className="text-xs h-9 flex-1" data-testid="deploy-slug-input"/>
                <span className="text-[11px] text-[var(--gs-muted)]">.getszy.com</span>
              </div>
              <div className="text-[10px] text-[var(--gs-muted)] mt-1">3-40 chars: letters, digits, hyphens. Auto-generated if empty.</div>
            </div>
            <Button size="sm" onClick={deploy} disabled={busy} className="bg-[var(--gs-teal)] w-full" data-testid="deploy-submit-btn">
              {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1"/> : <Rocket className="h-3 w-3 mr-1"/>}
              Deploy
            </Button>
          </div>
        )}
      </div>

      {/* Live sites */}
      {sites.length > 0 && (
        <div className="mb-3" data-testid="deploy-sites">
          <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1.5 tracking-wider">Live sites</div>
          <ul className="space-y-1.5">
            {sites.map(s => {
              const previewUrl = `${backend}/api/host/${s.slug}/`;
              const prodUrl = `https://${s.slug}.getszy.com`;
              return (
                <li key={s.id} className="text-xs p-2.5 rounded-lg bg-[var(--gs-surface-2)]" data-testid={`live-site-${s.slug}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"/>
                    <span className="font-semibold">{s.title || s.slug}</span>
                    <Badge variant="outline" className="text-[9px] ml-auto">{Math.round(s.size_bytes / 1024)} KB</Badge>
                  </div>
                  <div className="text-[10px] text-[var(--gs-muted)] mb-1.5">Updated {new Date(s.updated_at).toLocaleString()}</div>
                  <div className="flex flex-wrap gap-1">
                    <a href={previewUrl} target="_blank" rel="noreferrer"
                      className="text-[10px] px-2 py-1 rounded-md bg-[var(--gs-teal)] text-white flex items-center gap-1 hover:opacity-90"
                      data-testid={`site-open-${s.slug}`}>
                      <ExternalLink className="h-3 w-3"/>Open preview
                    </a>
                    <button onClick={() => copyUrl(prodUrl)}
                      className="text-[10px] px-2 py-1 rounded-md bg-white border flex items-center gap-1 hover:bg-[var(--gs-surface-3)]"
                      style={{ borderColor: "var(--gs-border)" }} data-testid={`site-copy-${s.slug}`}>
                      <FileText className="h-3 w-3"/>Copy prod URL
                    </button>
                    <button onClick={() => undeploy(s.slug)}
                      className="text-[10px] px-2 py-1 rounded-md text-rose-600 hover:bg-rose-50 flex items-center gap-1 ml-auto"
                      data-testid={`site-undeploy-${s.slug}`}>
                      <Trash2 className="h-3 w-3"/>Undeploy
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Caddy snippet for production */}
      <div className="mt-3">
        <button onClick={loadCaddy} className="text-[10px] text-[var(--gs-muted)] hover:text-[var(--gs-teal)] underline" data-testid="deploy-caddy-toggle">
          {showCaddy ? "Hide" : "Show"} Caddy config for production wildcard hosting
        </button>
        {showCaddy && (
          <pre className="mt-2 p-3 bg-[var(--gs-surface-2)] rounded-lg text-[10px] whitespace-pre-wrap overflow-x-auto max-h-64" data-testid="deploy-caddy-snippet">
{caddy}
          </pre>
        )}
      </div>

      {/* Deployment history (older entries from workspace_deployments) */}
      {deployments && deployments.length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1.5 tracking-wider">History</div>
          <ul className="space-y-1" data-testid="deployments-history">
            {deployments.map(d => (
              <li key={d.id} className="text-[11px] p-2 rounded-md bg-[var(--gs-surface-2)]/60 flex items-center gap-2" data-testid={`deploy-hist-${d.id}`}>
                <Rocket className="h-3 w-3 text-violet-600 shrink-0"/>
                <span className="truncate flex-1">{d.target}</span>
                <Badge variant="outline" className="text-[9px]">{d.status || "recorded"}</Badge>
                <span className="text-[9px] text-[var(--gs-muted)]">{new Date(d.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
