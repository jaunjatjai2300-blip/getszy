import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Layers, Play, Save, Trash2, RefreshCw, CheckCircle2, AlertCircle, FileCode2, Plus } from "lucide-react";
import { toast } from "sonner";

const SAMPLE_YAML = `name: "Diwali Mega Sale 2026"
audience: [women, girls]
description: "Curate trending Diwali products, enforce 40% margin, generate brand assets."

steps:
  - skill: scan_trending
    params: { count: 12 }

  - skill: import_trending
    params: { count: 6, min_score: 82 }

  - skill: enforce_margins
    params: { dry_run: false }

  - skill: generate_logo
    params:
      brand: "Diwali Mega Sale"
      style: festive

  - skill: generate_hero_image
    params:
      prompt: "festive diwali sale banner with marigold flowers and diyas"
      style: cinematic

  - skill: ai_insights
`;

export default function AdminStacks() {
  const [stacks, setStacks] = useState([]);
  const [yamlText, setYamlText] = useState(SAMPLE_YAML);
  const [activeStack, setActiveStack] = useState(null);
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState(null);

  const load = async () => { try { const r = await api.get("/admin/stacks"); setStacks(r.data.items || []); } catch (e) {} };
  useEffect(() => { load(); }, []);

  const parse = async () => {
    try { const r = await api.post("/admin/stacks/parse", { yaml: yamlText }); toast.success(`Valid — ${r.data.step_count} steps`); }
    catch (e) { toast.error(e?.response?.data?.detail || "Invalid YAML"); }
  };

  const save = async () => {
    try { await api.post("/admin/stacks/save", { yaml: yamlText }); toast.success("Stack saved"); await load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const runOnce = async () => {
    setBusy(true); setRun(null);
    toast.loading("Executing stack… (each step runs sequentially)", { id: "stack", duration: 120000 });
    try {
      const r = await api.post("/admin/stacks/run-once", { yaml: yamlText });
      setRun(r.data);
      toast.success(`Stack ${r.data.overall_status === "ok" ? "completed" : "partial"}`, { id: "stack" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Stack failed", { id: "stack" });
    } finally { setBusy(false); }
  };

  const runSaved = async (stackId) => {
    setBusy(true); setRun(null);
    toast.loading("Running saved stack…", { id: "stack", duration: 120000 });
    try {
      const r = await api.post(`/admin/stacks/${stackId}/run`);
      setRun(r.data);
      toast.success(`Stack ${r.data.overall_status}`, { id: "stack" });
    } catch (e) { toast.error("Failed", { id: "stack" }); }
    finally { setBusy(false); }
  };

  const remove = async (stackId) => {
    if (!confirm("Delete this stack?")) return;
    try { await api.delete(`/admin/stacks/${stackId}`); toast.success("Deleted"); await load(); }
    catch (e) { toast.error("Delete failed"); }
  };

  const loadStack = async (s) => { setActiveStack(s); setYamlText(s.yaml); setRun(null); };

  return (
    <div className="space-y-6" data-testid="admin-stacks-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Layers className="h-6 w-6 text-[var(--gs-teal)]"/>Campaign Stacks</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Describe an entire campaign in YAML — we&apos;ll run every step in sequence.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={async () => {
            try {
              const r = await api.post("/admin/stacks/seed-templates");
              toast.success(`${r.data.seeded.length} templates seeded, ${r.data.skipped.length} already existed`);
              await load();
            } catch (e) { toast.error("Seed failed"); }
          }} data-testid="stacks-seed-button" className="gap-2 text-xs">
            <RefreshCw className="h-3.5 w-3.5"/>Load Templates
          </Button>
          <Button variant="outline" onClick={() => { setActiveStack(null); setYamlText(SAMPLE_YAML); setRun(null); }} data-testid="stacks-new-button" className="gap-2"><Plus className="h-4 w-4"/>New</Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-4">
          <div className="gs-card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2"><FileCode2 className="h-4 w-4 text-[var(--gs-teal)]"/><span className="font-semibold">{activeStack?.name || "New Stack"}</span></div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={parse} data-testid="stacks-parse-button">Validate</Button>
                <Button size="sm" variant="outline" onClick={save} className="gap-1" data-testid="stacks-save-button"><Save className="h-3 w-3"/>Save</Button>
                <Button size="sm" onClick={runOnce} disabled={busy} className="gap-1 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="stacks-run-button">{busy ? <RefreshCw className="h-3 w-3 animate-spin"/> : <Play className="h-3 w-3"/>}Run</Button>
              </div>
            </div>
            <Textarea value={yamlText} onChange={(e) => setYamlText(e.target.value)} rows={20} className="font-mono text-xs" data-testid="stacks-yaml-editor" spellCheck={false}/>
          </div>

          {run && (
            <div className="gs-card p-4 space-y-3" data-testid="stacks-run-result">
              <div className="flex items-center gap-2">
                <Badge className={run.overall_status === "ok" ? "bg-[var(--gs-teal)]" : "bg-amber-500"}>{run.overall_status}</Badge>
                <h3 className="font-display text-lg">{run.stack_name}</h3>
                <span className="text-xs text-[var(--gs-muted)] ml-auto">{run.steps.length} steps</span>
              </div>
              <div className="space-y-2">
                {run.steps.map((step, i) => (
                  <div key={i} className="border rounded-xl p-3" style={{ borderColor: "var(--gs-border)" }}>
                    <div className="flex items-center gap-2 text-sm">
                      {step.status === "ok" ? <CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)]"/> : <AlertCircle className="h-4 w-4 text-rose-500"/>}
                      <span className="font-semibold">{step.skill}</span>
                      <span className="text-xs text-[var(--gs-muted)] ml-auto">step {i + 1}</span>
                    </div>
                    {step.error ? (
                      <div className="mt-2 text-xs text-rose-700">{step.error}</div>
                    ) : (
                      <pre className="mt-2 text-[10px] bg-[var(--gs-surface-2)] p-2 rounded max-h-40 overflow-auto">{JSON.stringify(step.result, null, 2)}</pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm uppercase tracking-wider text-[var(--gs-muted)]">Saved stacks ({stacks.length})</h3>
          </div>
          {stacks.length === 0 ? (
            <div className="gs-card p-4 text-xs text-[var(--gs-muted)] space-y-2">
              <div>Nothing saved yet.</div>
              <Button size="sm" variant="outline" className="w-full text-xs" onClick={async () => {
                try { const r = await api.post("/admin/stacks/seed-templates"); toast.success(`${r.data.seeded.length} templates loaded!`); await load(); }
                catch (e) { toast.error("Seed failed"); }
              }}>Load 6 pre-built templates</Button>
            </div>
          ) : (
            stacks.map((s) => (
              <div key={s.id} className={`gs-card p-3 ${activeStack?.id === s.id ? "ring-2 ring-[var(--gs-teal)]" : ""}`}>
                <div className="flex items-start gap-2">
                  <button onClick={() => loadStack(s)} className="flex-1 text-left min-w-0" data-testid={`stack-load-${s.id}`}>
                    <div className="font-semibold text-sm line-clamp-1">{s.name}</div>
                    <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{(s.parsed?.steps || []).length} steps · {new Date(s.updated_at).toLocaleDateString()}</div>
                  </button>
                  <button onClick={() => runSaved(s.id)} className="p-1.5 rounded hover:bg-[var(--gs-surface-2)]" title="Run" data-testid={`stack-run-${s.id}`}><Play className="h-3.5 w-3.5 text-[var(--gs-teal)]"/></button>
                  <button onClick={() => remove(s.id)} className="p-1.5 rounded hover:bg-rose-50 text-rose-500" title="Delete" data-testid={`stack-delete-${s.id}`}><Trash2 className="h-3.5 w-3.5"/></button>
                </div>
              </div>
            ))
          )}
        </aside>
      </div>
    </div>
  );
}
