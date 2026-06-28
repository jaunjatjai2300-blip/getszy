import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import * as Icons from "lucide-react";
import { Wand2, RefreshCw, Play, ChevronRight, Sparkles } from "lucide-react";
import { toast } from "sonner";

const CATEGORY_META = {
  commerce:  { label: "Commerce", color: "#9b6a3f" },
  media:     { label: "Media & Content", color: "#c97a87" },
  analytics: { label: "Analytics & Reports", color: "#5d8f8e" },
  devops:    { label: "DevOps & Deploy", color: "#7c3aed" },
  marketing: { label: "Marketing", color: "#e0a458" },
};

export default function AdminSkills() {
  const [skills, setSkills] = useState({ by_category: {}, count: 0 });
  const [active, setActive] = useState(null);
  const [params, setParams] = useState({});
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [runs, setRuns] = useState([]);

  const load = async () => { try { const r = await api.get("/admin/skills"); setSkills(r.data); } catch (e) {} };
  const loadRuns = async () => { try { const r = await api.get("/admin/skills/runs/recent?limit=10"); setRuns(r.data.items || []); } catch (e) {} };
  useEffect(() => { load(); loadRuns(); }, []);

  const openSkill = (skill) => {
    setActive(skill);
    const init = {};
    Object.entries(skill.params || {}).forEach(([k, def]) => { init[k] = def.default ?? ""; });
    setParams(init);
    setResult(null);
  };

  const runSkill = async () => {
    if (!active) return;
    setBusy(true);
    setResult(null);
    toast.loading(`Running ${active.title}…`, { id: "skill", duration: 60000 });
    try {
      const cleaned = {};
      Object.entries(params).forEach(([k, v]) => { if (v !== "" && v !== null && v !== undefined) cleaned[k] = v; });
      const r = await api.post(`/admin/skills/${active.name}/run`, { params: cleaned });
      setResult(r.data);
      if (r.data.status === "ok") toast.success(`${active.title} ✅`, { id: "skill" });
      else toast.error(r.data.error || "Skill failed", { id: "skill" });
      await loadRuns();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Run failed", { id: "skill" });
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-skills-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl">Skills Marketplace</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{skills.count} one-click admin actions · invoke directly or via Copilot</p>
        </div>
      </div>

      {Object.entries(skills.by_category || {}).map(([cat, items]) => {
        const meta = CATEGORY_META[cat] || { label: cat, color: "#666" };
        return (
          <section key={cat} data-testid={`skill-category-${cat}`}>
            <div className="flex items-center gap-2 mb-3">
              <div className="h-2 w-2 rounded-full" style={{ background: meta.color }}/>
              <h2 className="font-semibold text-sm uppercase tracking-wider">{meta.label}</h2>
              <span className="text-xs text-[var(--gs-muted)]">· {items.length}</span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {items.map((s) => {
                const Icon = Icons[s.icon] || Sparkles;
                return (
                  <button key={s.name} onClick={() => openSkill(s)} data-testid={`skill-card-${s.name}`}
                    className="gs-card p-4 text-left hover:bg-[var(--gs-surface-2)] transition">
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: meta.color + "22" }}>
                        <Icon className="h-5 w-5" style={{ color: meta.color }}/>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm">{s.title}</span>
                          {s.badge !== "free" && <Badge variant="outline" className="text-[9px] px-1.5 py-0">{s.badge}</Badge>}
                        </div>
                        <div className="text-[11px] text-[var(--gs-muted)] mt-1 line-clamp-2">{s.description}</div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-[var(--gs-muted)] mt-2 flex-shrink-0"/>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}

      {/* Recent Runs */}
      <div>
        <h3 className="font-display text-xl mb-3">Recent runs</h3>
        {runs.length === 0 ? (
          <div className="gs-card p-6 text-center text-sm text-[var(--gs-muted)]">No runs yet — click any skill to try it.</div>
        ) : (
          <div className="gs-card divide-y" style={{ borderColor: "var(--gs-border)" }}>
            {runs.map((r) => (
              <div key={r.id} className="p-3 flex items-center gap-3 text-sm" data-testid={`skill-run-${r.id}`}>
                <Badge className={r.status === "ok" ? "bg-[var(--gs-teal)]" : "bg-rose-100 text-rose-800"}>{r.status}</Badge>
                <span className="font-semibold">{r.skill}</span>
                <span className="text-xs text-[var(--gs-muted)] ml-auto">{new Date(r.started_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run Skill Dialog */}
      <Dialog open={!!active} onOpenChange={(o) => !o && setActive(null)}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="skill-dialog">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-2xl flex items-center gap-2">
                  <Wand2 className="h-5 w-5 text-[var(--gs-teal)]"/>{active.title}
                </DialogTitle>
              </DialogHeader>
              <p className="text-sm text-[var(--gs-muted)]">{active.description}</p>

              {Object.keys(active.params || {}).length > 0 ? (
                <div className="space-y-3 mt-3">
                  {Object.entries(active.params).map(([key, def]) => (
                    <div key={key}>
                      <label className="text-xs text-[var(--gs-muted)] capitalize">{key.replaceAll("_", " ")}{def.required && <span className="text-rose-500"> *</span>}</label>
                      {def.type === "boolean" ? (
                        <div><input type="checkbox" checked={!!params[key]} onChange={(e) => setParams({ ...params, [key]: e.target.checked })} data-testid={`skill-param-${key}`}/></div>
                      ) : (
                        <Input type={def.type === "integer" ? "number" : "text"} value={params[key] ?? ""} onChange={(e) => setParams({ ...params, [key]: def.type === "integer" ? Number(e.target.value) : e.target.value })} data-testid={`skill-param-${key}`}/>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--gs-muted)] mt-2">This skill takes no parameters.</p>
              )}

              <Button onClick={runSkill} disabled={busy} className="mt-4 gap-2 w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="skill-run-button">
                {busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Play className="h-4 w-4"/>}
                {busy ? "Running…" : "Run skill"}
              </Button>

              {result && (
                <div className="mt-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={result.status === "ok" ? "bg-[var(--gs-teal)]" : "bg-rose-500"}>{result.status}</Badge>
                    <span className="text-xs text-[var(--gs-muted)]">Result</span>
                  </div>
                  <pre className="text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl max-h-72 overflow-auto" data-testid="skill-result">{JSON.stringify(result.result ?? result.error ?? result, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
