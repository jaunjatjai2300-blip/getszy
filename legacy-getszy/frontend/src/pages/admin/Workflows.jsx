import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Workflow, Plus, RefreshCw, Play, Trash2, ToggleLeft, ToggleRight,
  Zap, Clock, Video, Users, ShoppingCart, Bell, Share2, Mail,
  Globe, Sparkles, CheckCircle2, XCircle, AlertCircle, Loader2,
  ChevronRight, Package
} from "lucide-react";
import { toast } from "sonner";

const TRIGGER_META = {
  video_ready:   { icon: Video,        color: "text-[var(--gs-teal)]",  bg: "bg-[var(--gs-teal-soft)]",  label: "Video Ready" },
  new_product:   { icon: Package,      color: "text-violet-600",        bg: "bg-violet-50",               label: "New Product" },
  new_user:      { icon: Users,        color: "text-blue-600",          bg: "bg-blue-50",                 label: "New User Signup" },
  cron:          { icon: Clock,        color: "text-amber-600",         bg: "bg-amber-50",                label: "Schedule" },
  manual:        { icon: Play,         color: "text-emerald-600",       bg: "bg-emerald-50",              label: "Manual" },
  credit_low:    { icon: Zap,          color: "text-orange-600",        bg: "bg-orange-50",               label: "Low Credits" },
  order_placed:  { icon: ShoppingCart, color: "text-rose-600",          bg: "bg-rose-50",                 label: "Order Placed" },
};

const ACTION_META = {
  post_social:      { icon: Share2,    color: "text-pink-600",          label: "Post to Social" },
  grant_credits:    { icon: Zap,       color: "text-amber-600",         label: "Grant Credits" },
  send_email:       { icon: Mail,      color: "text-blue-600",          label: "Send Email" },
  generate_content: { icon: Sparkles,  color: "text-[var(--gs-teal)]",  label: "Generate Content" },
  webhook:          { icon: Globe,     color: "text-violet-600",        label: "Webhook" },
  notify_slack:     { icon: Bell,      color: "text-emerald-600",       label: "Slack Notify" },
};

function RunStatusBadge({ s }) {
  if (!s) return null;
  if (s === "success") return <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-2.5 w-2.5 mr-1"/>Success</Badge>;
  if (s === "running") return <Badge className="bg-blue-100 text-blue-700 text-[10px]"><Loader2 className="h-2.5 w-2.5 mr-1 animate-spin"/>Running</Badge>;
  if (s === "failed")  return <Badge className="bg-rose-100 text-rose-700 text-[10px]"><XCircle className="h-2.5 w-2.5 mr-1"/>Failed</Badge>;
  if (s === "partial") return <Badge className="bg-orange-100 text-orange-700 text-[10px]"><AlertCircle className="h-2.5 w-2.5 mr-1"/>Partial</Badge>;
  return <Badge variant="outline" className="text-[10px]">{s}</Badge>;
}

const DEFAULT_FORM = {
  name: "", description: "", trigger: "manual",
  trigger_config: {}, actions: [], enabled: true
};

export default function AdminWorkflows() {
  const [workflows,  setWorkflows]  = useState([]);
  const [meta,       setMeta]       = useState({ triggers: [], actions: [] });
  const [loading,    setLoading]    = useState(true);
  const [showNew,    setShowNew]    = useState(false);
  const [form,       setForm]       = useState(DEFAULT_FORM);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [running,    setRunning]    = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [wf, mt] = await Promise.allSettled([
      api.get("/admin/workflows"),
      api.get("/admin/workflows/triggers"),
    ]);
    if (wf.status === "fulfilled") setWorkflows(wf.value.data.items || []);
    if (mt.status === "fulfilled") setMeta(mt.value.data);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const addAction = (type) => {
    setForm(f => ({
      ...f,
      actions: [...f.actions, { type, config: {} }]
    }));
  };

  const removeAction = (idx) => {
    setForm(f => ({ ...f, actions: f.actions.filter((_, i) => i !== idx) }));
  };

  const updateActionConfig = (idx, key, val) => {
    setForm(f => {
      const actions = [...f.actions];
      actions[idx] = { ...actions[idx], config: { ...actions[idx].config, [key]: val } };
      return { ...f, actions };
    });
  };

  const createWorkflow = async () => {
    if (!form.name.trim()) return toast.error("Workflow ka naam daalo");
    if (!form.trigger) return toast.error("Trigger chuno");
    if (!form.actions.length) return toast.error("Kam se kam ek action add karo");
    setSubmitBusy(true);
    try {
      await api.post("/admin/workflows", form);
      toast.success("Workflow created!");
      setShowNew(false);
      setForm(DEFAULT_FORM);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Create failed");
    } finally { setSubmitBusy(false); }
  };

  const toggleEnabled = async (wf) => {
    try {
      await api.patch(`/admin/workflows/${wf.id}`, { enabled: !wf.enabled });
      toast.success(wf.enabled ? "Disabled" : "Enabled");
      await load();
    } catch (e) { toast.error("Update failed"); }
  };

  const runWorkflow = async (wf) => {
    setRunning(wf.id);
    try {
      await api.post(`/admin/workflows/${wf.id}/run`);
      toast.success(`"${wf.name}" trigger kiya!`);
      setTimeout(load, 1500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Run failed");
    } finally { setRunning(null); }
  };

  const deleteWorkflow = async (wf) => {
    if (!window.confirm(`Delete "${wf.name}"?`)) return;
    try {
      await api.delete(`/admin/workflows/${wf.id}`);
      toast.success("Deleted"); await load();
    } catch (e) { toast.error("Delete failed"); }
  };

  const TriggerIcon = ({ type, size = "h-4 w-4" }) => {
    const m = TRIGGER_META[type] || { icon: Zap, color: "text-[var(--gs-muted)]", bg: "bg-gray-100" };
    return <m.icon className={`${size} ${m.color}`}/>;
  };

  return (
    <div className="space-y-5" data-testid="admin-workflows-page">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Workflow className="h-7 w-7 text-[var(--gs-teal)]"/>Workflow Builder
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            Automation chains — trigger → action(s) · {workflows.filter(w => w.enabled).length} active
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
          </Button>
          <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
            onClick={() => setShowNew(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5"/>New Workflow
          </Button>
        </div>
      </div>

      {/* Quick templates */}
      <div className="grid sm:grid-cols-3 gap-3">
        {[
          { name: "Video → Auto Post",  trigger: "video_ready", actions: [{ type: "post_social", config: {} }], desc: "Video ready hote hi social pe post karo" },
          { name: "New User → Credits", trigger: "new_user",    actions: [{ type: "grant_credits", config: { amount: 25 } }], desc: "Signup bonus 25 credits dena" },
          { name: "Order → Notify",     trigger: "order_placed",actions: [{ type: "send_email", config: {} }], desc: "New order aaye toh email karo" },
        ].map(t => (
          <button key={t.name} onClick={() => { setForm({ ...DEFAULT_FORM, name: t.name, trigger: t.trigger, actions: t.actions }); setShowNew(true); }}
            className="text-left p-3 rounded-xl border hover:border-[var(--gs-teal)] hover:bg-[var(--gs-teal-soft)] transition-colors group"
            style={{ borderColor: "var(--gs-border)" }}>
            <div className="flex items-center gap-2 mb-1">
              <TriggerIcon type={t.trigger}/>
              <span className="text-sm font-semibold group-hover:text-[var(--gs-teal)]">{t.name}</span>
            </div>
            <div className="text-[10px] text-[var(--gs-muted)]">{t.desc}</div>
          </button>
        ))}
      </div>

      {/* Workflows list */}
      {loading ? (
        <div className="grid sm:grid-cols-2 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-36 rounded-2xl bg-[var(--gs-surface-2)] animate-pulse"/>)}
        </div>
      ) : workflows.length === 0 ? (
        <Card className="p-10 text-center">
          <Workflow className="h-12 w-12 mx-auto mb-3 text-[var(--gs-muted)] opacity-40"/>
          <p className="text-sm text-[var(--gs-muted)] mb-3">Koi workflows nahi hain</p>
          <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
            onClick={() => setShowNew(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5"/>Pehla workflow banao
          </Button>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {workflows.map(wf => {
            const tm = TRIGGER_META[wf.trigger] || { icon: Zap, color: "text-[var(--gs-muted)]", bg: "bg-gray-100", label: wf.trigger };
            return (
              <Card key={wf.id} className={`p-4 flex flex-col gap-3 ${!wf.enabled ? "opacity-60" : ""}`}>
                {/* Top row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className={`h-9 w-9 rounded-xl ${tm.bg} grid place-items-center flex-shrink-0`}>
                      <tm.icon className={`h-4 w-4 ${tm.color}`}/>
                    </div>
                    <div>
                      <div className="font-semibold text-sm">{wf.name}</div>
                      <div className="text-[10px] text-[var(--gs-muted)]">{wf.description || tm.label}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <RunStatusBadge s={wf.last_run_status}/>
                    <Switch checked={wf.enabled} onCheckedChange={() => toggleEnabled(wf)}/>
                  </div>
                </div>

                {/* Trigger → Actions chain */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${tm.bg} ${tm.color}`}>
                    {tm.label}
                  </span>
                  <ChevronRight className="h-3 w-3 text-[var(--gs-muted)] flex-shrink-0"/>
                  {(wf.actions || []).map((a, i) => {
                    const am = ACTION_META[a.type] || { icon: Zap, color: "text-[var(--gs-muted)]", label: a.type };
                    return (
                      <span key={i} className={`text-[10px] px-2 py-0.5 rounded-full bg-[var(--gs-surface-2)] ${am.color} font-medium`}>
                        {am.label}
                      </span>
                    );
                  })}
                </div>

                {/* Stats */}
                <div className="flex items-center gap-3 text-[10px] text-[var(--gs-muted)]">
                  <span>Run {wf.run_count || 0}×</span>
                  {wf.last_run && <span>Last: {new Date(wf.last_run).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 mt-auto">
                  <Button size="sm" variant="outline" className="flex-1 text-xs h-7"
                    disabled={running === wf.id}
                    onClick={() => runWorkflow(wf)}>
                    {running === wf.id ? <Loader2 className="h-3 w-3 mr-1 animate-spin"/> : <Play className="h-3 w-3 mr-1"/>}
                    Run Now
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500"
                    onClick={() => deleteWorkflow(wf)}>
                    <Trash2 className="h-3 w-3"/>
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── New Workflow Dialog ── */}
      <Dialog open={showNew} onOpenChange={o => { if (!o) { setShowNew(false); setForm(DEFAULT_FORM); } }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Workflow className="h-5 w-5 text-[var(--gs-teal)]"/>New Workflow
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Workflow naam *</label>
              <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Video Auto-Post"/>
            </div>
            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Description</label>
              <Input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Short description"/>
            </div>

            {/* Trigger picker */}
            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-2">Trigger chuno *</label>
              <div className="grid grid-cols-2 gap-2">
                {(meta.triggers || Object.entries(TRIGGER_META).map(([id, m]) => ({ id, label: m.label, desc: "" }))).map(t => {
                  const m = TRIGGER_META[t.id] || { icon: Zap, color: "text-[var(--gs-muted)]", bg: "bg-gray-100" };
                  const active = form.trigger === t.id;
                  return (
                    <button key={t.id} onClick={() => setForm(f => ({ ...f, trigger: t.id }))}
                      className={`flex items-center gap-2 p-2.5 rounded-xl border text-left transition-colors ${
                        active ? "border-[var(--gs-teal)] bg-[var(--gs-teal-soft)]" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"
                      }`}>
                      <div className={`h-7 w-7 rounded-lg ${m.bg} grid place-items-center flex-shrink-0`}>
                        <m.icon className={`h-3.5 w-3.5 ${m.color}`}/>
                      </div>
                      <div>
                        <div className={`text-xs font-semibold ${active ? "text-[var(--gs-teal)]" : ""}`}>{t.label}</div>
                        {t.desc && <div className="text-[10px] text-[var(--gs-muted)] leading-tight">{t.desc}</div>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Cron config */}
            {form.trigger === "cron" && (
              <div>
                <label className="text-xs text-[var(--gs-muted)] block mb-1">Cron Expression</label>
                <Input value={form.trigger_config.cron || ""} onChange={e => setForm(f => ({ ...f, trigger_config: { ...f.trigger_config, cron: e.target.value } }))}
                  placeholder="0 9 * * 1 = Every Monday 9am"/>
                <div className="text-[10px] text-[var(--gs-muted)] mt-1">
                  Examples: <code>0 9 * * *</code> (daily 9am) · <code>0 9 * * 1</code> (every Monday)
                </div>
              </div>
            )}

            {/* Actions */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs text-[var(--gs-muted)]">Actions * (in order)</label>
              </div>

              {/* Added actions */}
              {form.actions.map((a, idx) => {
                const am = ACTION_META[a.type] || { icon: Zap, color: "text-[var(--gs-muted)]", label: a.type };
                return (
                  <div key={idx} className="mb-2 p-3 rounded-xl border bg-[var(--gs-surface-2)] space-y-2" style={{ borderColor: "var(--gs-border)" }}>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-semibold ${am.color}`}>{idx+1}. {am.label}</span>
                      <button onClick={() => removeAction(idx)} className="text-rose-400 hover:text-rose-600">
                        <XCircle className="h-3.5 w-3.5"/>
                      </button>
                    </div>
                    {a.type === "grant_credits" && (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-[var(--gs-muted)]">Amount</label>
                          <Input type="number" value={a.config.amount || ""} className="h-7 text-xs"
                            onChange={e => updateActionConfig(idx, "amount", Number(e.target.value))} placeholder="25"/>
                        </div>
                        <div>
                          <label className="text-[10px] text-[var(--gs-muted)]">Email (optional)</label>
                          <Input value={a.config.email || ""} className="h-7 text-xs"
                            onChange={e => updateActionConfig(idx, "email", e.target.value)} placeholder="Sab users"/>
                        </div>
                      </div>
                    )}
                    {a.type === "webhook" && (
                      <div>
                        <label className="text-[10px] text-[var(--gs-muted)]">Webhook URL</label>
                        <Input value={a.config.url || ""} className="h-7 text-xs"
                          onChange={e => updateActionConfig(idx, "url", e.target.value)} placeholder="https://…"/>
                      </div>
                    )}
                    {a.type === "send_email" && (
                      <div>
                        <label className="text-[10px] text-[var(--gs-muted)]">Subject</label>
                        <Input value={a.config.subject || ""} className="h-7 text-xs"
                          onChange={e => updateActionConfig(idx, "subject", e.target.value)} placeholder="Email subject"/>
                      </div>
                    )}
                    {a.type === "post_social" && (
                      <div className="text-[10px] text-amber-600 bg-amber-50 p-2 rounded-lg">
                        Social post automation video_ready trigger ke saath kaam karta hai
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Add action picker */}
              <div className="grid grid-cols-3 gap-1.5 mt-2">
                {(meta.actions || Object.entries(ACTION_META).map(([id, m]) => ({ id, label: m.label }))).map(a => {
                  const am = ACTION_META[a.id] || { icon: Zap, color: "text-[var(--gs-muted)]", label: a.id };
                  return (
                    <button key={a.id} onClick={() => addAction(a.id)}
                      className="flex items-center gap-1.5 text-[10px] p-2 rounded-lg border hover:bg-[var(--gs-teal-soft)] hover:border-[var(--gs-teal)] transition-colors"
                      style={{ borderColor: "var(--gs-border)" }}>
                      <am.icon className={`h-3 w-3 ${am.color} flex-shrink-0`}/>
                      <span className="truncate">{a.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <Button onClick={createWorkflow} disabled={submitBusy || !form.name || !form.trigger || !form.actions.length}
              className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {submitBusy ? <Loader2 className="h-4 w-4 mr-2 animate-spin"/> : <Plus className="h-4 w-4 mr-2"/>}
              Create Workflow
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
