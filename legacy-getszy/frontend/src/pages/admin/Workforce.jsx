import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import * as Icons from "lucide-react";
import { Briefcase, Loader2, Play, Copy } from "lucide-react";
import { toast } from "sonner";

export default function Workforce() {
  const [agents, setAgents] = useState([]);
  const [active, setActive] = useState(null);
  const [params, setParams] = useState({});
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [history, setHistory] = useState([]);

  const load = async () => {
    try { const r = await api.get("/workforce/agents"); setAgents(r.data.agents || []); } catch (e) {}
    try { const r = await api.get("/workforce/history?limit=15"); setHistory(r.data.items || []); } catch (e) {}
  };
  useEffect(() => { load(); }, []);

  const open = (a) => {
    setActive(a); setOut(null);
    const init = {};
    Object.entries(a.params || {}).forEach(([k, def]) => { init[k] = def.default ?? ""; });
    setParams(init);
  };

  const runTask = async () => {
    if (!active) return;
    setBusy(true); setOut(null);
    toast.loading(`${active.name} is working…`, { id: "wf", duration: 60000 });
    try {
      const r = await api.post(`/workforce/${active.id}/task`, { params });
      setOut(r.data.output);
      toast.success(`${active.name} ✅`, { id: "wf" });
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Task failed", { id: "wf" });
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-workforce-page">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2"><Briefcase className="h-7 w-7 text-[var(--gs-teal)]"/> AI Workforce</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">10 specialist agents — Editor, Designer, SEO, Thumbnail artist, Captions, Translator, Researcher, Strategist, Community manager, Analyst.</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3" data-testid="workforce-grid">
        {agents.map((a) => {
          const Icon = Icons[a.icon] || Briefcase;
          return (
            <button key={a.id} onClick={() => open(a)} data-testid={`agent-card-${a.id}`}
              className="gs-card p-4 text-left hover:bg-[var(--gs-surface-2)] transition">
              <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: `${a.color}22` }}>
                <Icon className="h-5 w-5" style={{ color: a.color }}/>
              </div>
              <div className="mt-3 font-semibold text-sm">{a.name}</div>
              <div className="text-[11px] text-[var(--gs-muted)] mt-1 line-clamp-3">{a.role}</div>
            </button>
          );
        })}
      </div>

      {/* History */}
      <div>
        <h3 className="font-display text-xl mb-3">Recent runs</h3>
        {history.length === 0 ? (
          <Card className="p-6 text-center text-sm text-[var(--gs-muted)]">No runs yet — pick an agent above.</Card>
        ) : (
          <div className="space-y-2" data-testid="workforce-history">
            {history.map(h => (
              <Card key={h.id} className="p-3 flex items-center gap-3 text-sm">
                <Badge variant="outline" className="text-[10px]">{h.agent_id}</Badge>
                <span className="truncate flex-1">{Object.values(h.params || {})[0] || h.id}</span>
                <span className="text-[10px] text-[var(--gs-muted)]">{new Date(h.created_at).toLocaleString()}</span>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={!!active} onOpenChange={(o) => !o && setActive(null)}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="agent-dialog">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-2xl">{active.name}</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-[var(--gs-muted)]">{active.role}</p>
              <div className="space-y-3 mt-3">
                {Object.entries(active.params || {}).map(([k, def]) => (
                  <div key={k}>
                    <label className="text-xs text-[var(--gs-muted)] capitalize">{k.replaceAll("_", " ")}{def.required && <span className="text-rose-500"> *</span>}</label>
                    <Textarea rows={2} value={params[k] ?? ""} onChange={(e) => setParams({ ...params, [k]: e.target.value })} data-testid={`agent-param-${k}`}/>
                  </div>
                ))}
              </div>
              <Button onClick={runTask} disabled={busy} className="mt-4 w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="agent-run-btn">
                {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Play className="h-4 w-4 mr-2"/>}
                {busy ? "Working…" : "Run"}
              </Button>
              {out && (
                <div className="mt-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">{out.agent || active.id}</Badge>
                    <button onClick={() => { navigator.clipboard.writeText(JSON.stringify(out.parsed || out, null, 2)); toast.success("Copied"); }} className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1 ml-auto"><Copy className="h-3 w-3"/>copy</button>
                  </div>
                  <pre className="text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl max-h-72 overflow-auto" data-testid="agent-result">{JSON.stringify(out.parsed || out, null, 2)}</pre>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
