import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Film, Sparkles, Wand2, Search, PenTool, Layers, Eye, Loader2,
  Plus, RefreshCw, Lock, Unlock, ChevronRight, TrendingUp,
  Lightbulb, ListChecks, PlayCircle, CheckCircle2, Download, Video,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const STYLES = {
  viral:       { label: "Viral",       color: "bg-rose-500",   emoji: "🔥" },
  educational: { label: "Educational", color: "bg-sky-500",    emoji: "📚" },
  story:       { label: "Story",       color: "bg-violet-500", emoji: "📖" },
  documentary: { label: "Documentary", color: "bg-amber-500",  emoji: "🎬" },
  beginner:    { label: "Beginner",    color: "bg-emerald-500", emoji: "🌱" },
};

const SCENE_ROLE_COLOR = {
  hook: "bg-rose-500/15 text-rose-700 border-rose-200",
  problem: "bg-amber-500/15 text-amber-700 border-amber-200",
  context: "bg-sky-500/15 text-sky-700 border-sky-200",
  example: "bg-emerald-500/15 text-emerald-700 border-emerald-200",
  climax: "bg-violet-500/15 text-violet-700 border-violet-200",
  cta: "bg-[var(--gs-teal)]/15 text-[var(--gs-teal)] border-[var(--gs-teal)]/30",
  transition: "bg-slate-500/15 text-slate-700 border-slate-200",
};

export default function VideoStudio() {
  const [projects, setProjects] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [project, setProject] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState("enhanced");

  const loadProjects = useCallback(async () => {
    try {
      const r = await api.get("/video-factory/projects");
      setProjects(r.data.items || []);
    } catch (e) { /* silent */ }
  }, []);

  const loadProject = useCallback(async (id) => {
    if (!id) return;
    try {
      const r = await api.get(`/video-factory/project/${id}`);
      setProject(r.data);
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects]);
  useEffect(() => { if (activeId) loadProject(activeId); }, [activeId, loadProject]);

  // Auto-refresh when processing
  useEffect(() => {
    if (project?.status === "processing") {
      const iv = setInterval(() => loadProject(project.id), 4000);
      return () => clearInterval(iv);
    }
  }, [project?.status, project?.id, loadProject]);

  const createProject = async () => {
    if (prompt.trim().length < 8) { toast.error("Prompt zaruri hai (min 8 chars)"); return; }
    setCreating(true);
    try {
      const r = await api.post("/video-factory/project", { prompt: prompt.trim(), language: "hinglish", auto_run: true });
      toast.success("Neo AI Factory started — takes 30-60 sec");
      setPrompt("");
      setActiveId(r.data.id);
      await loadProjects();
    } catch (e) { toast.error("Create failed"); }
    finally { setCreating(false); }
  };

  const rerun = async (endpoint, label) => {
    if (!project) return;
    toast.loading(`Regenerating ${label}...`, { id: endpoint });
    try {
      await api.post(`/video-factory/project/${project.id}/${endpoint}`);
      toast.success(`${label} updated`, { id: endpoint });
      await loadProject(project.id);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Regen failed", { id: endpoint });
    }
  };

  const selectScript = async (scriptId) => {
    try {
      await api.post(`/video-factory/project/${project.id}/select-script`, { script_id: scriptId });
      toast.success("Script selected");
      await loadProject(project.id);
    } catch (e) { toast.error("Selection failed"); }
  };

  const toggleLock = async (scene) => {
    try {
      await api.patch(`/video-factory/project/${project.id}/scene/${scene.id}`, { locked: !scene.locked });
      await loadProject(project.id);
    } catch (e) { toast.error("Lock toggle failed"); }
  };

  const regenScene = async (scene) => {
    toast.loading(`Regenerating scene ${scene.index}...`, { id: `scene-${scene.id}` });
    try {
      await api.post(`/video-factory/project/${project.id}/scene/${scene.id}/regenerate`);
      toast.success("Scene regenerated", { id: `scene-${scene.id}` });
      await loadProject(project.id);
    } catch (e) { toast.error(e?.response?.data?.detail || "Regen failed", { id: `scene-${scene.id}` }); }
  };

  const stages = project?.stages || {};
  const selectedScript = (stages.script_variants || []).find(v => v.id === project?.selected_script_id) || (stages.script_variants || [])[0];

  return (
    <div className="grid grid-cols-12 gap-4 h-[calc(100vh-120px)]" data-testid="video-studio-page">
      {/* Sidebar: Projects list + new project */}
      <Card className="col-span-3 flex flex-col overflow-hidden">
        <div className="p-3 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Film className="h-4 w-4 text-[var(--gs-teal)]"/>
            <div className="font-display text-sm font-bold">AI Video Factory</div>
            <Badge className="ml-auto text-[9px] bg-[var(--gs-teal)]">v2</Badge>
          </div>
          <Textarea
            placeholder="Video idea (e.g. 'Explain AI agents in 5 min Hinglish for students')"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="text-xs mb-2"
            data-testid="video-prompt-input"
          />
          <Button
            onClick={createProject}
            disabled={creating || prompt.trim().length < 8}
            className="w-full bg-[var(--gs-teal)] gap-1 h-9"
            data-testid="video-create-btn"
          >
            {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin"/> : <Sparkles className="h-3.5 w-3.5"/>}
            Start factory
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          <div className="text-[10px] uppercase text-[var(--gs-muted)] px-2 mb-1 tracking-wider">Projects ({projects.length})</div>
          {projects.length === 0 ? (
            <div className="text-xs text-[var(--gs-muted)] p-4 text-center">No projects yet</div>
          ) : (
            projects.map(p => (
              <button
                key={p.id}
                onClick={() => setActiveId(p.id)}
                className={`w-full text-left p-2 rounded-lg mb-1 text-xs ${activeId === p.id ? "bg-[var(--gs-teal)]/15 text-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`}
                data-testid={`video-proj-${p.id}`}
              >
                <div className="font-medium line-clamp-1">{p.title}</div>
                <div className="flex items-center gap-1 text-[10px] mt-0.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${p.status === "ready" ? "bg-emerald-500" : p.status === "processing" ? "bg-amber-500 animate-pulse" : p.status === "error" ? "bg-rose-500" : "bg-slate-400"}`}/>
                  {p.status}
                </div>
              </button>
            ))
          )}
        </div>
      </Card>

      {/* Main workspace */}
      <div className="col-span-9 overflow-hidden flex flex-col">
        {!project ? (
          <Card className="flex-1 grid place-items-center text-center p-12">
            <div>
              <Film className="h-14 w-14 mx-auto text-[var(--gs-teal)] mb-3 opacity-40"/>
              <h3 className="font-display text-2xl mb-2">Turn any idea into a production-ready video</h3>
              <p className="text-sm text-[var(--gs-muted)] max-w-md">
                Type your topic on the left. Neo AI runs 6 specialist agents:
                Research → Script Variants → Hooks → Storyboard → Visual Plan.
                Aap har stage regenerate, edit, ya lock kar sakte ho.
              </p>
            </div>
          </Card>
        ) : (
          <Card className="flex-1 flex flex-col overflow-hidden">
            <div className="p-3 border-b flex items-center gap-3" style={{ borderColor: "var(--gs-border)" }}>
              <div className="flex-1 min-w-0">
                <div className="font-display text-lg line-clamp-1" data-testid="video-project-title">{project.title}</div>
                <div className="text-[10px] text-[var(--gs-muted)] line-clamp-1">{project.prompt_raw}</div>
              </div>
              <Badge className={project.status === "ready" ? "bg-emerald-500" : project.status === "processing" ? "bg-amber-500" : "bg-slate-500"} data-testid="video-project-status">
                {project.status === "processing" && <Loader2 className="h-3 w-3 animate-spin mr-1"/>}
                {project.status}
              </Badge>
              <button onClick={() => loadProject(project.id)} className="text-[var(--gs-muted)] hover:text-[var(--gs-teal)]" title="Refresh" data-testid="video-refresh-btn">
                <RefreshCw className="h-4 w-4"/>
              </button>
            </div>

            <Tabs value={tab} onValueChange={setTab} className="flex flex-col flex-1 overflow-hidden">
              <TabsList className="mx-3 mt-2 justify-start bg-[var(--gs-surface-2)] p-0.5 h-auto flex-wrap">
                {[
                  { v: "enhanced", label: "Brief", Icon: Lightbulb },
                  { v: "research",  label: "Research", Icon: Search },
                  { v: "scripts",   label: "Scripts", Icon: PenTool },
                  { v: "hooks",     label: "Hooks", Icon: Wand2 },
                  { v: "storyboard", label: "Storyboard", Icon: Layers },
                  { v: "visuals",   label: "Visuals", Icon: Eye },
                  { v: "render",    label: "Render", Icon: Video },
                ].map(t => (
                  <TabsTrigger key={t.v} value={t.v} className="text-xs gap-1 data-[state=active]:bg-[var(--gs-teal)] data-[state=active]:text-white" data-testid={`vf-tab-${t.v}`}>
                    <t.Icon className="h-3 w-3"/>{t.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              <div className="flex-1 overflow-y-auto p-4">
                <TabsContent value="enhanced" className="m-0" data-testid="vf-enhanced-content">
                  {stages.enhanced ? (
                    <div className="space-y-3">
                      <StageHeader title="Enhanced Brief" onRegen={() => rerun("enhance", "Brief")}/>
                      <div className="grid grid-cols-2 gap-3">
                        <InfoCard label="Topic" value={stages.enhanced.enhanced_topic}/>
                        <InfoCard label="Angle" value={stages.enhanced.angle}/>
                        <InfoCard label="Target audience" value={stages.enhanced.target_audience}/>
                        <InfoCard label="Duration" value={`${stages.enhanced.estimated_duration_seconds}s`}/>
                        <InfoCard label="Hook direction" value={stages.enhanced.hook_direction} className="col-span-2"/>
                      </div>
                      {stages.enhanced.improvements && (
                        <div>
                          <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Improvements</div>
                          <ul className="text-xs space-y-0.5">
                            {stages.enhanced.improvements.map((it, i) => <li key={i}>• {it}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : <PendingState label="Brief" status={project.status}/>}
                </TabsContent>

                <TabsContent value="research" className="m-0" data-testid="vf-research-content">
                  {stages.research ? (
                    <div className="space-y-3">
                      <StageHeader title="Research Report" onRegen={() => rerun("research", "Research")}/>
                      <FactList title="Key Facts" items={stages.research.key_facts}/>
                      <FactList title="Statistics" items={stages.research.statistics}/>
                      <FactList title="FAQs to address" items={stages.research.faqs}/>
                      <FactList title="Competitor gaps" items={stages.research.competitor_gaps}/>
                      <div>
                        <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Trending keywords</div>
                        <div className="flex flex-wrap gap-1">
                          {(stages.research.trending_keywords || []).map(k => (
                            <Badge key={k} variant="outline" className="text-[10px]">{k}</Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : <PendingState label="Research" status={project.status}/>}
                </TabsContent>

                <TabsContent value="scripts" className="m-0" data-testid="vf-scripts-content">
                  {(stages.script_variants || []).length > 0 ? (
                    <div>
                      <StageHeader title="Script Variants (5)" onRegen={() => rerun("scripts", "Scripts")}/>
                      <div className="grid grid-cols-1 gap-2 mt-2">
                        {(stages.script_variants || []).map(v => {
                          const st = STYLES[v.style_id] || { label: v.style_id, color: "bg-slate-500", emoji: "🎬" };
                          const on = project.selected_script_id === v.id;
                          return (
                            <button
                              key={v.id}
                              onClick={() => selectScript(v.id)}
                              className={`text-left rounded-lg border p-3 transition ${on ? "border-[var(--gs-teal)] bg-[var(--gs-teal)]/5" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}
                              data-testid={`vf-script-${v.style_id}`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${st.color} text-white`}>{st.emoji} {st.label}</span>
                                {on && <CheckCircle2 className="h-3.5 w-3.5 text-[var(--gs-teal)] ml-auto"/>}
                                <span className="text-[10px] text-[var(--gs-muted)] ml-auto">{v.estimated_word_count || "—"} words</span>
                              </div>
                              <div className="text-xs italic text-[var(--gs-teal)] mb-1">"{v.hook}"</div>
                              <div className="text-xs text-[var(--gs-muted)] line-clamp-3">{v.narration}</div>
                              {v.cta && <div className="text-[10px] mt-1 text-[var(--gs-fg)]"><b>CTA:</b> {v.cta}</div>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ) : <PendingState label="Scripts" status={project.status}/>}
                </TabsContent>

                <TabsContent value="hooks" className="m-0" data-testid="vf-hooks-content">
                  {(stages.hooks || []).length > 0 ? (
                    <div>
                      <StageHeader title="Hook Options (ranked by expected score)" onRegen={() => rerun("hooks", "Hooks")}/>
                      <div className="space-y-1.5">
                        {(stages.hooks || []).map((h, i) => (
                          <div key={i} className="p-2.5 rounded-lg bg-[var(--gs-surface-2)] flex items-start gap-2" data-testid={`vf-hook-${i}`}>
                            <div className="text-lg font-display text-[var(--gs-teal)] w-8 text-center shrink-0">{h.expected_score || "—"}</div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium">{h.text}</div>
                              <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">
                                <Badge variant="outline" className="text-[9px] mr-1">{h.type}</Badge>
                                {h.why}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : <PendingState label="Hooks" status={project.status}/>}
                </TabsContent>

                <TabsContent value="storyboard" className="m-0" data-testid="vf-storyboard-content">
                  {(stages.storyboard || []).length > 0 ? (
                    <div>
                      <StageHeader title="Storyboard" onRegen={() => rerun("storyboard", "Storyboard")}/>
                      <div className="space-y-2 mt-2">
                        <AnimatePresence>
                          {(stages.storyboard || []).map(scene => (
                            <motion.div
                              key={scene.id}
                              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -6 }}
                              className={`rounded-lg border p-3 ${scene.locked ? "bg-amber-50 border-amber-200" : "border-[var(--gs-border)] bg-white"}`}
                              data-testid={`vf-scene-${scene.index}`}
                            >
                              <div className="flex items-center gap-2 mb-1.5">
                                <div className="text-[10px] font-mono bg-[var(--gs-surface-2)] px-1.5 py-0.5 rounded">#{scene.index}</div>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${SCENE_ROLE_COLOR[scene.role] || "bg-slate-100"}`}>{scene.role}</span>
                                <Badge variant="outline" className="text-[10px]">{scene.duration_s}s</Badge>
                                <Badge variant="outline" className="text-[10px]">{scene.pacing_note}</Badge>
                                <div className="ml-auto flex items-center gap-1">
                                  <button onClick={() => toggleLock(scene)} className={`p-1 rounded ${scene.locked ? "text-amber-600" : "text-[var(--gs-muted)] hover:text-[var(--gs-teal)]"}`} title={scene.locked ? "Unlock" : "Lock"} data-testid={`vf-scene-lock-${scene.index}`}>
                                    {scene.locked ? <Lock className="h-3 w-3"/> : <Unlock className="h-3 w-3"/>}
                                  </button>
                                  <button onClick={() => regenScene(scene)} disabled={scene.locked} className="p-1 rounded text-[var(--gs-muted)] hover:text-[var(--gs-teal)] disabled:opacity-30" title="Regenerate visual" data-testid={`vf-scene-regen-${scene.index}`}>
                                    <RefreshCw className="h-3 w-3"/>
                                  </button>
                                </div>
                              </div>
                              <div className="text-sm mb-1">{scene.narration_chunk}</div>
                              {scene.visual_intent && <div className="text-[11px] text-[var(--gs-muted)] italic"><b>Visual:</b> {scene.visual_intent}</div>}
                            </motion.div>
                          ))}
                        </AnimatePresence>
                      </div>
                    </div>
                  ) : <PendingState label="Storyboard" status={project.status}/>}
                </TabsContent>

                <TabsContent value="visuals" className="m-0" data-testid="vf-visuals-content">
                  {(stages.visual_plan || []).length > 0 ? (
                    <div>
                      <StageHeader title="Visual Plan (per scene)" onRegen={() => rerun("visuals", "Visuals")}/>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        {(stages.visual_plan || []).map(v => (
                          <div key={v.scene_index} className="p-3 rounded-lg bg-[var(--gs-surface-2)]" data-testid={`vf-visual-${v.scene_index}`}>
                            <div className="flex items-center gap-2 mb-1.5">
                              <div className="text-[10px] font-mono bg-white px-1.5 py-0.5 rounded">#{v.scene_index}</div>
                              <Badge className="bg-[var(--gs-teal)] text-[10px]">{v.kind}</Badge>
                              <Badge variant="outline" className="text-[10px]">{v.aspect_ratio}</Badge>
                            </div>
                            <div className="text-xs mb-1">{v.generation_prompt}</div>
                            <div className="text-[10px] text-[var(--gs-muted)]">
                              <b>Style:</b> {v.style_ref}
                              {v.notes && <span> · {v.notes}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : <PendingState label="Visual plan" status={project.status}/>}
                </TabsContent>

                <TabsContent value="render" className="m-0" data-testid="vf-render-content">
                  <RenderTab project={project} onRefresh={() => loadProject(project.id)}/>
                </TabsContent>
              </div>
            </Tabs>
          </Card>
        )}
      </div>
    </div>
  );
}

function StageHeader({ title, onRegen }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <h3 className="font-display text-lg">{title}</h3>
      <Button size="sm" variant="outline" onClick={onRegen} className="ml-auto text-xs h-7 gap-1" data-testid="vf-regen-btn">
        <RefreshCw className="h-3 w-3"/> Regenerate
      </Button>
    </div>
  );
}

function InfoCard({ label, value, className = "" }) {
  return (
    <div className={`p-3 rounded-lg bg-[var(--gs-surface-2)] ${className}`}>
      <div className="text-[10px] uppercase text-[var(--gs-muted)] tracking-wider mb-1">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
  );
}

function FactList({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1 tracking-wider">{title}</div>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li key={i} className="text-xs p-2 rounded bg-[var(--gs-surface-2)]">• {it}</li>
        ))}
      </ul>
    </div>
  );
}

function PendingState({ label, status }) {
  if (status === "processing") {
    return (
      <div className="text-center py-16" data-testid="vf-pending">
        <Loader2 className="h-8 w-8 mx-auto animate-spin text-[var(--gs-teal)] mb-3"/>
        <div className="text-sm text-[var(--gs-muted)]">{label} generation in progress...</div>
      </div>
    );
  }
  return (
    <div className="text-center py-16 text-sm text-[var(--gs-muted)]" data-testid="vf-pending">
      {label} not generated yet. Click Regenerate above or wait for auto-run to complete.
    </div>
  );
}

function RenderTab({ project, onRefresh }) {
  const [orientation, setOrientation] = useState("16:9");
  const [busy, setBusy] = useState(false);
  const status = project.render_status;
  const progress = project.render_progress || 0;
  const backend = process.env.REACT_APP_BACKEND_URL || "";
  const isRendering = ["queued", "generating_images", "generating_voice", "assembling"].includes(status);
  const isComplete = status === "complete" && project.final_video_size > 0;
  const hasError = status === "error";
  const stages = project.stages || {};
  const hasPipeline = (stages.storyboard || []).length > 0 && (stages.visual_plan || []).length > 0;

  useEffect(() => {
    if (isRendering) {
      const iv = setInterval(() => onRefresh(), 3000);
      return () => clearInterval(iv);
    }
  }, [isRendering, onRefresh]);

  const generate = async () => {
    if (!hasPipeline) { toast.error("Pipeline (storyboard + visuals) chahiye pehle"); return; }
    setBusy(true);
    try {
      await api.post(`/video-factory/project/${project.id}/generate-assets`, { orientation });
      toast.success("Asset generation started — 2-5 minutes lagenge");
      onRefresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to start"); }
    finally { setBusy(false); }
  };

  const STATUS_LABEL = {
    queued: "Queued...",
    generating_images: "Generating scene images (AI)...",
    generating_voice: "Synthesizing voice-over...",
    assembling: "Assembling final video (ffmpeg)...",
    complete: "Video ready ✅",
    error: "Render failed",
  };

  return (
    <div data-testid="vf-render">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="font-display text-lg">Final Video Render</h3>
        {isRendering && <Badge className="bg-amber-500 gap-1"><Loader2 className="h-3 w-3 animate-spin"/> {STATUS_LABEL[status]}</Badge>}
        {isComplete && <Badge className="bg-emerald-500">{STATUS_LABEL[status]}</Badge>}
        {hasError && <Badge className="bg-rose-500">Error</Badge>}
      </div>

      {!hasPipeline && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800 mb-3">
          Pipeline complete karo pehle — Storyboard aur Visuals tabs mein data ready hone chahiye.
        </div>
      )}

      {hasError && project.render_error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 mb-3">
          <b>Error:</b> {project.render_error}
        </div>
      )}

      {isRendering && (
        <div className="mb-4">
          <div className="text-xs text-[var(--gs-muted)] mb-1">Progress: {progress}%</div>
          <div className="h-2 rounded-full bg-[var(--gs-surface-2)] overflow-hidden">
            <div className="h-full bg-[var(--gs-teal)] transition-all" style={{ width: `${progress}%` }}/>
          </div>
        </div>
      )}

      {!isComplete && !isRendering && hasPipeline && (
        <div className="p-4 rounded-lg bg-[var(--gs-teal)]/8 border border-[var(--gs-teal)]/20 mb-3">
          <div className="text-sm font-semibold mb-2">Ready to render your video</div>
          <div className="text-xs text-[var(--gs-muted)] mb-3">
            Neo will generate {(stages.storyboard || []).length} scene images (Pollinations AI), synthesize voice-over (edge-tts), and assemble into a downloadable MP4.
          </div>
          <div className="flex items-center gap-2 mb-3">
            <div className="text-xs text-[var(--gs-muted)]">Orientation:</div>
            {["16:9", "9:16", "1:1"].map(o => (
              <button key={o} onClick={() => setOrientation(o)}
                className={`text-xs px-3 py-1 rounded ${orientation === o ? "bg-[var(--gs-teal)] text-white" : "bg-white border"}`}
                style={{ borderColor: "var(--gs-border)" }}
                data-testid={`vf-orient-${o}`}>
                {o} {o === "16:9" ? "(YouTube)" : o === "9:16" ? "(Reels/Shorts)" : "(Square)"}
              </button>
            ))}
          </div>
          <Button onClick={generate} disabled={busy} className="bg-[var(--gs-teal)] gap-2" data-testid="vf-generate-btn">
            {busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <Video className="h-4 w-4"/>}
            Generate video
          </Button>
        </div>
      )}

      {isComplete && (
        <div className="space-y-3" data-testid="vf-complete">
          <div className="rounded-lg overflow-hidden bg-black">
            <video controls className="w-full" src={`${backend}/api/video-factory/project/${project.id}/download`}/>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <a
              href={`${backend}/api/video-factory/project/${project.id}/download`}
              download
              className="text-sm px-4 py-2 bg-[var(--gs-teal)] text-white rounded-lg flex items-center gap-2 hover:opacity-90"
              data-testid="vf-download-btn"
            >
              <Download className="h-4 w-4"/> Download MP4
            </a>
            <Badge variant="outline" className="text-xs">
              {Math.round((project.final_video_size || 0) / 1024 / 1024 * 10) / 10} MB
            </Badge>
            <Badge variant="outline" className="text-xs">{project.scenes_rendered || 0} scenes</Badge>
            <Badge variant="outline" className="text-xs">Voice: {project.voice_used || "—"}</Badge>
            <Button variant="outline" size="sm" onClick={generate} disabled={busy} className="ml-auto text-xs gap-1" data-testid="vf-regen-video-btn">
              <RefreshCw className="h-3 w-3"/> Re-render
            </Button>
          </div>
        </div>
      )}

      {/* Scene image thumbnails (available after render or partial) */}
      {(stages.storyboard || []).some(s => s.image_path) && (
        <div className="mt-6">
          <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-2 tracking-wider">Rendered scene images</div>
          <div className="grid grid-cols-4 gap-2">
            {(stages.storyboard || []).filter(s => s.image_path).map(s => (
              <div key={s.id} className="relative aspect-video rounded-lg overflow-hidden bg-[var(--gs-surface-2)]" data-testid={`vf-scene-img-${s.index}`}>
                <img src={`${backend}/api/video-factory/project/${project.id}/scene-image/${s.index}`}
                     alt={`Scene ${s.index}`}
                     className="w-full h-full object-cover"/>
                <div className="absolute bottom-1 left-1 text-[10px] px-1.5 py-0.5 rounded bg-black/60 text-white">#{s.index} · {s.role}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
