import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Rocket, Bot, Wand2, Palette, Code2, ShieldCheck, GitBranch, Globe, RefreshCw, CheckCircle2, AlertCircle, Sparkles, Clock } from "lucide-react";
import { toast } from "sonner";

const AGENTS = [
  { key: "planner", name: "Planner", icon: Bot, color: "#9b6a3f" },
  { key: "designer", name: "Designer", icon: Palette, color: "#c97a87" },
  { key: "coder", name: "Coder", icon: Code2, color: "#5d8f8e" },
  { key: "reviewer", name: "Reviewer", icon: ShieldCheck, color: "#9b6a3f" },
];

const TARGETS = [
  { id: "page", label: "Storefront Page" },
  { id: "landing", label: "Landing Page" },
  { id: "tool", label: "AI Tool" },
  { id: "bundle", label: "Subscription Bundle" },
];

export default function AdminDeploy() {
  const [status, setStatus] = useState(null);
  const [brief, setBrief] = useState("Build a Diwali sale landing page featuring our top 8 trending products with a countdown timer and a 'Shop the Look' carousel.");
  const [target, setTarget] = useState("landing");
  const [autopush, setAutopush] = useState(false);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState(null);
  const [jobs, setJobs] = useState([]);

  const loadStatus = async () => { try { const r = await api.get("/admin/deploy/status"); setStatus(r.data); } catch (e) {} };
  const loadJobs = async () => { try { const r = await api.get("/admin/deploy/jobs?limit=10"); setJobs(r.data.items || []); } catch (e) {} };
  useEffect(() => { loadStatus(); loadJobs(); }, []);

  const runSwarm = async () => {
    if (brief.trim().length < 8) { toast.error("Brief is too short"); return; }
    setBusy(true);
    setJob(null);
    toast.loading("Agent swarm orchestrating… (~15s)", { id: "swarm", duration: 45000 });
    try {
      const r = await api.post("/admin/deploy/build", { brief, target, autopush });
      setJob(r.data);
      toast.success(autopush ? "Swarm complete + pushed to GitHub" : "Swarm complete", { id: "swarm" });
      await loadJobs();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Swarm failed", { id: "swarm" });
    } finally { setBusy(false); }
  };

  const pushToGithub = async () => {
    if (!job) return;
    toast.loading("Pushing to GitHub…", { id: "push" });
    try {
      const r = await api.post(`/admin/deploy/${job.id}/push`);
      if (r.data.ok) {
        toast.success(`Committed: ${r.data.commit_sha?.slice(0, 7) || "ok"}`, { id: "push" });
        setJob({ ...job, deploy_status: r.data, status: "pushed" });
        await loadJobs();
      } else {
        toast.error(r.data.message || "Push failed", { id: "push" });
      }
    } catch (e) {
      toast.error("Push failed", { id: "push" });
    }
  };

  const triggerWebhook = async () => {
    if (!job) return;
    toast.loading("Triggering VPS deploy webhook…", { id: "hook" });
    try {
      const r = await api.post(`/admin/deploy/${job.id}/webhook`);
      if (r.data.ok) toast.success("Webhook delivered", { id: "hook" });
      else toast.error(r.data.message || "Webhook failed", { id: "hook" });
    } catch (e) { toast.error("Webhook failed", { id: "hook" }); }
  };

  return (
    <div className="space-y-6" data-testid="admin-deploy-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl">Master Build &amp; Deploy</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Describe what to build. The agent swarm plans, drafts, reviews, then deploys to Getszy.</p>
        </div>
        {status && (
          <div className="flex items-center gap-3">
            <Pill enabled={status.github.configured} label="GitHub" sublabel={status.github.repo} icon={GitBranch}/>
            <Pill enabled={status.webhook.configured} label="VPS Webhook" sublabel={status.webhook.configured ? "Active" : "Add DEPLOY_WEBHOOK_URL"} icon={Globe}/>
          </div>
        )}
      </div>

      {/* Agent strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="agent-strip">
        {AGENTS.map((a) => {
          const Icon = a.icon;
          const out = job?.agents?.[a.key];
          const isActive = busy && !out;
          return (
            <div key={a.key} className={`gs-card p-4 relative overflow-hidden ${isActive ? "ring-2 ring-[var(--gs-teal)]" : ""}`}>
              <div className="absolute inset-x-0 top-0 h-1" style={{ background: a.color }}/>
              <div className="flex items-center gap-2 mb-1">
                <Icon className="h-4 w-4" style={{ color: a.color }}/>
                <span className="font-semibold text-sm">{a.name}</span>
                {isActive && <RefreshCw className="h-3 w-3 animate-spin text-[var(--gs-muted)] ml-auto"/>}
                {out && <CheckCircle2 className="h-3 w-3 text-[var(--gs-teal)] ml-auto"/>}
              </div>
              <div className="text-[11px] text-[var(--gs-muted)] line-clamp-4 whitespace-pre-wrap">{out || "Idle — awaiting brief"}</div>
            </div>
          );
        })}
      </div>

      {/* Brief form */}
      <div className="gs-card p-5 space-y-4">
        <div>
          <label className="text-xs text-[var(--gs-muted)]">What do you want to build &amp; deploy?</label>
          <Textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={4} data-testid="deploy-brief-input"/>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] mr-2">Target</label>
            {TARGETS.map((t) => (
              <button key={t.id} onClick={() => setTarget(t.id)} className={`mr-1.5 px-3 py-1.5 rounded-full text-xs border ${target === t.id ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`} data-testid={`deploy-target-${t.id}`}>
                {t.label}
              </button>
            ))}
          </div>
          <label className="ml-auto flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autopush} onChange={(e) => setAutopush(e.target.checked)} data-testid="deploy-autopush-toggle"/>
            Auto-push plan to GitHub
          </label>
          <Button onClick={runSwarm} disabled={busy} className="gap-2" data-testid="deploy-run-swarm-button">
            {busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Wand2 className="h-4 w-4"/>}
            {busy ? "Orchestrating…" : "Run Agent Swarm"}
          </Button>
        </div>
      </div>

      {/* Current Job result */}
      {job && (
        <div className="gs-card p-5 space-y-3" data-testid="deploy-current-job">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-[var(--gs-teal)]"/><h3 className="font-display text-xl">Plan ready</h3>
                <Badge className="bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">{job.status}</Badge>
              </div>
              <div className="text-xs text-[var(--gs-muted)] mt-1">Job ID: {job.id?.slice(0, 8)}</div>
            </div>
            <div className="flex gap-2">
              <Button onClick={pushToGithub} variant="outline" className="gap-2" data-testid="deploy-push-button"><GitBranch className="h-4 w-4"/>Push to GitHub</Button>
              <Button onClick={triggerWebhook} className="gap-2" data-testid="deploy-webhook-button"><Rocket className="h-4 w-4"/>Deploy to VPS</Button>
            </div>
          </div>
          {job.deploy_status && (
            <div className={`p-3 rounded-xl text-xs ${job.deploy_status.ok ? "bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]" : "bg-amber-50 text-amber-900 border border-amber-200"}`}>
              {job.deploy_status.ok ? (
                <span className="flex items-center gap-2"><CheckCircle2 className="h-3 w-3"/>Committed to GitHub · {job.deploy_status.path || job.deploy_status.commit_sha?.slice(0, 7)}</span>
              ) : (
                <span className="flex items-center gap-2"><AlertCircle className="h-3 w-3"/>{job.deploy_status.message || "Push not yet attempted"}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Job history */}
      <div>
        <h3 className="font-display text-xl mb-3 flex items-center gap-2"><Clock className="h-4 w-4 text-[var(--gs-teal)]"/>Recent deploy jobs</h3>
        {jobs.length === 0 ? (
          <div className="gs-card p-8 text-center text-sm text-[var(--gs-muted)]">No jobs yet — run your first swarm above.</div>
        ) : (
          <div className="gs-card divide-y" style={{ borderColor: "var(--gs-border)" }}>
            {jobs.map((j) => (
              <div key={j.id} className="p-4 flex items-start gap-3" data-testid={`job-${j.id}`}>
                <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: j.status === "pushed" ? "var(--gs-teal-soft)" : "var(--gs-surface-2)" }}>
                  {j.status === "pushed" ? <CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)]"/> : <Wand2 className="h-4 w-4 text-[var(--gs-muted)]"/>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold line-clamp-1">{j.brief}</div>
                  <div className="text-[11px] text-[var(--gs-muted)] mt-0.5">{j.target} · {new Date(j.created_at).toLocaleString()}</div>
                </div>
                <Badge className={j.status === "pushed" ? "bg-[var(--gs-teal)]" : "bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"}>{j.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Pill({ enabled, label, sublabel, icon: Icon }) {
  return (
    <div className="gs-card px-3 py-2 flex items-center gap-2">
      <div className="h-8 w-8 rounded-lg grid place-items-center" style={{ background: enabled ? "var(--gs-teal-soft)" : "var(--gs-surface-2)" }}>
        <Icon className={`h-4 w-4 ${enabled ? "text-[var(--gs-teal)]" : "text-[var(--gs-muted)]"}`}/>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">{label}</div>
        <div className="text-xs font-semibold">{sublabel}</div>
      </div>
    </div>
  );
}
