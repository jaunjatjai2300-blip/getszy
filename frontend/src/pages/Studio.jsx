import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Send, Loader2, Plus, Download, Trash2, Code2, Eye, Wand2, Bot, Zap } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const SUGGESTIONS = [
  "Build a stunning portfolio website for a yoga instructor named Priya",
  "Landing page for an AI productivity tool called FlowMind",
  "Single-page restaurant website for Spice Garden in Mumbai",
  "Personal coach website for a women's career mentor",
  "Boutique online store landing for handmade jewellery brand 'Riya & Co'",
  "Photographer portfolio with gallery and contact section",
];

const STAGES = [
  { key: "plan", label: "Planning", icon: Bot },
  { key: "code", label: "Coding", icon: Code2 },
  { key: "review", label: "Reviewing", icon: Wand2 },
];

export default function Studio() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [active, setActive] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [stageIdx, setStageIdx] = useState(0);
  const [view, setView] = useState("preview"); // preview | code
  const stageTimer = useRef(null);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [user, loading, navigate]);

  useEffect(() => { if (user) loadProjects(); }, [user]);

  const loadProjects = async () => {
    const { data } = await api.get("/builder/projects");
    setProjects(data);
  };

  const loadProject = async (id) => {
    const { data } = await api.get(`/builder/projects/${id}`);
    setActive(data);
  };

  const newChat = () => { setActive(null); setPrompt(""); };

  const animateStages = () => {
    setStageIdx(0);
    let i = 0;
    stageTimer.current = setInterval(() => {
      i = Math.min(i + 1, STAGES.length - 1);
      setStageIdx(i);
    }, 8000);
  };

  const stopStages = () => {
    if (stageTimer.current) clearInterval(stageTimer.current);
    stageTimer.current = null;
  };

  const submit = async () => {
    if (!prompt.trim() || busy) return;
    setBusy(true); animateStages();
    try {
      if (!active) {
        const { data } = await api.post("/builder/projects", { prompt }, { timeout: 600000 });
        setActive(data); setProjects((p) => [data, ...p.filter((x) => x.id !== data.id)]);
        toast.success("Project built ✨");
      } else {
        const { data } = await api.post(`/builder/projects/${active.id}/refine`, { prompt }, { timeout: 600000 });
        setActive(data);
        toast.success("Updated");
      }
      setPrompt("");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Generation failed — try again");
    } finally { stopStages(); setBusy(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this project?")) return;
    await api.delete(`/builder/projects/${id}`);
    if (active?.id === id) setActive(null);
    await loadProjects();
    toast.success("Deleted");
  };

  const download = async (id) => {
    const token = localStorage.getItem("gs_token");
    const r = await fetch(`${API_BASE}/builder/projects/${id}/download`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) return toast.error("Download failed");
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${active?.name || "project"}.zip`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  if (!user) return null;

  return (
    <div className="min-h-screen grid lg:grid-cols-[260px_1fr] bg-[var(--gs-bg)]" data-testid="studio-page">
      {/* Sidebar */}
      <aside className="hidden lg:flex flex-col border-r" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <div className="font-display text-xl">Studio</div>
          <div className="text-xs text-[var(--gs-muted)]">Talk-to-Build · Powered by your VPS</div>
        </div>
        <div className="p-3">
          <Button onClick={newChat} className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="studio-new-button"><Plus className="h-4 w-4 mr-2"/>New project</Button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {projects.length === 0 && <div className="text-xs text-[var(--gs-muted)] p-3">No projects yet. Start with a prompt below.</div>}
          {projects.map((p) => (
            <div key={p.id} className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--gs-surface-2)] cursor-pointer ${active?.id === p.id ? "bg-[var(--gs-surface-2)]" : ""}`} onClick={() => loadProject(p.id)} data-testid={`studio-project-${p.id}`}>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{p.name}</div>
                <div className="text-[10px] text-[var(--gs-muted)]">{new Date(p.updated_at).toLocaleDateString()}</div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); remove(p.id); }} className="opacity-0 group-hover:opacity-100 text-[var(--gs-muted)] hover:text-rose-500"><Trash2 className="h-3.5 w-3.5"/></button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-col h-screen overflow-hidden">
        {/* Header bar */}
        <div className="border-b p-4 flex items-center gap-3 flex-wrap" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
          <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gs-teal-soft)" }}><Sparkles className="h-5 w-5 text-[var(--gs-teal)]"/></div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold truncate">{active ? active.name : "Build something amazing"}</div>
            <div className="text-xs text-[var(--gs-muted)]">{active ? "Refine via chat below" : "Describe what you want in plain English or Hinglish"}</div>
          </div>
          {active && (
            <>
              <div className="flex gap-1 rounded-lg border p-0.5" style={{ borderColor: "var(--gs-border)" }}>
                <button onClick={() => setView("preview")} className={`px-3 py-1.5 text-xs rounded ${view === "preview" ? "bg-[var(--gs-ink)] text-white" : ""}`} data-testid="studio-view-preview"><Eye className="h-3 w-3 inline mr-1"/>Preview</button>
                <button onClick={() => setView("code")} className={`px-3 py-1.5 text-xs rounded ${view === "code" ? "bg-[var(--gs-ink)] text-white" : ""}`} data-testid="studio-view-code"><Code2 className="h-3 w-3 inline mr-1"/>Code</button>
              </div>
              <Button onClick={() => download(active.id)} variant="outline" size="sm" data-testid="studio-download-button"><Download className="h-4 w-4 mr-1"/>Download</Button>
            </>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden grid grid-rows-[1fr_auto]">
          <div className="overflow-auto p-4 sm:p-6 gs-ai-glow">
            {!active && !busy && (
              <div className="max-w-2xl mx-auto text-center py-8">
                <div className="h-14 w-14 mx-auto rounded-2xl grid place-items-center mb-4" style={{ background: "var(--gs-teal-soft)" }}><Wand2 className="h-7 w-7 text-[var(--gs-teal)]"/></div>
                <h1 className="font-display text-3xl sm:text-4xl mb-2">What do you want to build?</h1>
                <p className="text-[var(--gs-muted)] mb-6">Describe your website — AI agents on YOUR VPS will plan, code, and review it. ~2-4 min build time.</p>
                <div className="grid sm:grid-cols-2 gap-2 text-left">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => setPrompt(s)} className="text-sm p-3 rounded-xl border hover:bg-[var(--gs-surface-2)] text-left" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }} data-testid={`studio-suggestion-${s.slice(0,15)}`}>
                      <Zap className="h-3.5 w-3.5 text-[var(--gs-teal)] inline mr-1"/>{s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {busy && (
              <div className="max-w-xl mx-auto text-center py-12" data-testid="studio-building-state">
                <div className="flex items-center justify-center gap-3 mb-6">
                  {STAGES.map((s, i) => {
                    const Icon = s.icon;
                    const done = i < stageIdx; const current = i === stageIdx;
                    return (
                      <div key={s.key} className="flex items-center gap-2">
                        <div className={`h-10 w-10 rounded-full grid place-items-center ${done ? "bg-[var(--gs-teal)] text-white" : current ? "bg-[var(--gs-teal-soft)] text-[var(--gs-teal)] animate-pulse" : "bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"}`}>
                          {current ? <Loader2 className="h-4 w-4 animate-spin"/> : <Icon className="h-4 w-4"/>}
                        </div>
                        {i < STAGES.length - 1 && <div className={`w-10 h-0.5 ${done ? "bg-[var(--gs-teal)]" : "bg-[var(--gs-border)]"}`}/>}
                      </div>
                    );
                  })}
                </div>
                <div className="font-semibold mb-1">{STAGES[stageIdx].label}…</div>
                <p className="text-sm text-[var(--gs-muted)]">AI on your VPS is working. First build can take 2-4 min on CPU.</p>
              </div>
            )}

            {active && !busy && (
              view === "preview" ? (
                <iframe
                  title={active.name}
                  srcDoc={active.html_content}
                  sandbox="allow-scripts allow-same-origin allow-popups"
                  className="w-full h-full min-h-[600px] rounded-2xl border bg-white"
                  style={{ borderColor: "var(--gs-border)" }}
                  data-testid="studio-preview-iframe"
                />
              ) : (
                <pre className="w-full h-full min-h-[400px] rounded-2xl border p-4 overflow-auto text-xs bg-[#0f1419] text-[#f8f8f2] font-mono" style={{ borderColor: "var(--gs-border)" }} data-testid="studio-code-view">{active.html_content}</pre>
              )
            )}
          </div>

          {/* Composer */}
          <div className="border-t p-3 sm:p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)", paddingBottom: "60px" }}>
            <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="max-w-3xl mx-auto flex items-end gap-2">
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={1}
                placeholder={active ? "Refine: e.g., Make hero taller, add testimonials section…" : "Describe your website…"}
                className="resize-none min-h-[48px] max-h-32"
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
                disabled={busy}
                data-testid="studio-prompt-input"
              />
              <Button type="submit" disabled={busy || !prompt.trim()} className="h-12 w-12 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="studio-send-button">
                {busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>}
              </Button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
