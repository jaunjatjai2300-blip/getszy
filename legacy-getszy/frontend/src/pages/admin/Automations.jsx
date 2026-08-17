import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "sonner";
import { Zap, Plus, Trash2, Play, Save, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";

const OPS = ["==", "!=", ">", "<", ">=", "<=", "contains", "in", "exists"];
const ACTION_TYPES = ["notify", "webhook", "tag", "log"];

const emptyForm = () => ({
  name: "",
  trigger: "order_created",
  match: "all",
  conditions: [{ field: "total", op: ">", value: "" }],
  actions: [{ type: "notify", title: "", message: "", target_user: "", type_notif: "info", url: "", tag: "", note: "" }],
});

export default function Automations() {
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [form, setForm] = useState(emptyForm());
  const [test, setTest] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, r, l] = await Promise.all([
        api.get("/admin/automations/triggers"),
        api.get("/admin/automations"),
        api.get("/admin/automations/logs?limit=30").catch(() => ({ data: { items: [] } })),
      ]);
      setTriggers(t.data?.triggers || []);
      setRules(r.data?.items || []);
      setLogs(l.data?.items || []);
    } catch (e) {
      toast.error("Failed to load automations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const setCond = (i, k, v) => setForm((f) => ({
    ...f, conditions: f.conditions.map((c, j) => (j === i ? { ...c, [k]: v } : c)),
  }));
  const addCond = () => setForm((f) => ({ ...f, conditions: [...f.conditions, { field: "", op: "==", value: "" }] }));
  const removeCond = (i) => setForm((f) => ({ ...f, conditions: f.conditions.filter((_, j) => j !== i) }));

  const setAct = (i, k, v) => setForm((f) => ({
    ...f, actions: f.actions.map((a, j) => (j === i ? { ...a, [k]: v } : a)),
  }));
  const addAct = () => setForm((f) => ({ ...f, actions: [...f.actions, { type: "notify", title: "", message: "", target_user: "", type_notif: "info", url: "", tag: "", note: "" }] }));
  const removeAct = (i) => setForm((f) => ({ ...f, actions: f.actions.filter((_, j) => j !== i) }));

  const save = async () => {
    if (!form.name.trim()) { toast.error("Name required"); return; }
    try {
      await api.post("/admin/automations", form);
      toast.success("Automation saved");
      setForm(emptyForm());
      setTest(null);
      load();
    } catch (e) {
      toast.error("Save failed");
    }
  };

  const runTest = async () => {
    try {
      const { data } = await api.post("/admin/automations/test", form);
      setTest(data);
    } catch (e) {
      toast.error("Test failed");
    }
  };

  const del = async (id) => {
    if (!confirm("Delete this automation?")) return;
    try {
      await api.delete(`/admin/automations/${id}`);
      toast.success("Deleted");
      load();
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  const toggle = async (rule) => {
    try {
      await api.put(`/admin/automations/${rule.id}`, { ...rule, enabled: !rule.enabled });
      load();
    } catch (e) {
      toast.error("Update failed");
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-automations-page">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="h-5 w-5 text-[var(--gs-teal)]" />
          <h2 className="text-lg font-semibold">Automation Builder</h2>
          <Button size="sm" variant="ghost" className="ml-auto" onClick={load}><RefreshCw className="h-3.5 w-3.5" /></Button>
        </div>
        <p className="text-xs text-[var(--gs-muted)] mb-4">When an event happens, run actions automatically. e.g. "Order over ₹5,000 → notify me".</p>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <Input placeholder="Rule name" value={form.name} onChange={(e) => setField("name", e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <Select value={form.trigger} onValueChange={(v) => setField("trigger", v)}>
                <SelectTrigger><SelectValue placeholder="Trigger" /></SelectTrigger>
                <SelectContent>
                  {(triggers.length ? triggers : ["order_created", "refund_issued", "user_signup", "failed_login", "ip_blocked", "low_stock"]).map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={form.match} onValueChange={(v) => setField("match", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Match ALL</SelectItem>
                  <SelectItem value="any">Match ANY</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-1">Conditions</div>
              {form.conditions.map((c, i) => (
                <div key={i} className="flex gap-1 mb-1">
                  <Input className="flex-1" placeholder="field (e.g. total)" value={c.field} onChange={(e) => setCond(i, "field", e.target.value)} />
                  <Select value={c.op} onValueChange={(v) => setCond(i, "op", v)}>
                    <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                    <SelectContent>{OPS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
                  </Select>
                  <Input className="w-24" placeholder="value" value={c.value ?? ""} onChange={(e) => setCond(i, "value", e.target.value)} />
                  <Button size="sm" variant="ghost" onClick={() => removeCond(i)}><Trash2 className="h-3.5 w-3.5 text-rose-500" /></Button>
                </div>
              ))}
              <Button size="sm" variant="outline" onClick={addCond}><Plus className="h-3.5 w-3.5 mr-1" />Add condition</Button>
            </div>
          </div>

          <div className="space-y-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Actions</div>
            {form.actions.map((a, i) => (
              <div key={i} className="rounded-lg border border-[var(--gs-border)] p-2 space-y-2">
                <div className="flex gap-1">
                  <Select value={a.type} onValueChange={(v) => setAct(i, "type", v)}>
                    <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                    <SelectContent>{ACTION_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                  </Select>
                  <Button size="sm" variant="ghost" className="ml-auto" onClick={() => removeAct(i)}><Trash2 className="h-3.5 w-3.5 text-rose-500" /></Button>
                </div>
                {a.type === "notify" && (
                  <div className="space-y-1">
                    <Input placeholder="Title" value={a.title ?? ""} onChange={(e) => setAct(i, "title", e.target.value)} />
                    <Input placeholder="Message" value={a.message ?? ""} onChange={(e) => setAct(i, "message", e.target.value)} />
                    <Input placeholder="Target user id (blank = all admins)" value={a.target_user ?? ""} onChange={(e) => setAct(i, "target_user", e.target.value)} />
                  </div>
                )}
                {a.type === "webhook" && <Input placeholder="https://..." value={a.url ?? ""} onChange={(e) => setAct(i, "url", e.target.value)} />}
                {a.type === "tag" && <Input placeholder="Tag name" value={a.tag ?? ""} onChange={(e) => setAct(i, "tag", e.target.value)} />}
                {a.type === "log" && <Input placeholder="Note" value={a.note ?? ""} onChange={(e) => setAct(i, "note", e.target.value)} />}
              </div>
            ))}
            <Button size="sm" variant="outline" onClick={addAct}><Plus className="h-3.5 w-3.5 mr-1" />Add action</Button>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button onClick={save}><Save className="h-3.5 w-3.5 mr-1" />Save automation</Button>
          <Button variant="outline" onClick={runTest}><Play className="h-3.5 w-3.5 mr-1" />Test match</Button>
        </div>

        {test && (
          <div className={`mt-3 p-3 rounded-lg text-xs ${test.would_match ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
            <div className="font-semibold flex items-center gap-1">
              {test.would_match ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
              Sample event would {test.would_match ? "MATCH" : "NOT match"}
            </div>
            <pre className="mt-1 text-[10px] overflow-x-auto">{JSON.stringify(test.condition_eval, null, 2)}</pre>
          </div>
        )}
      </Card>

      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3">Active Automations ({rules.length})</h3>
        {loading ? <div className="text-xs text-[var(--gs-muted)]">Loading…</div> : rules.length === 0 ? (
          <div className="text-xs text-[var(--gs-muted)] py-6 text-center">No automations yet. Create one above.</div>
        ) : (
          <div className="space-y-2">
            {rules.map((r) => (
              <div key={r.id} className="flex items-center gap-3 p-3 rounded-xl border border-[var(--gs-border)]">
                <Zap className={`h-4 w-4 ${r.enabled ? "text-[var(--gs-teal)]" : "text-gray-400"}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{r.name}</div>
                  <div className="text-[10px] text-[var(--gs-muted)]">
                    {r.trigger} · {r.match} · {Array.isArray(r.actions) ? r.actions.length : 0} action(s)
                  </div>
                </div>
                <Badge variant={r.enabled ? "default" : "outline"} onClick={() => toggle(r)} className="cursor-pointer">
                  {r.enabled ? "On" : "Off"}
                </Badge>
                <Button size="sm" variant="ghost" onClick={() => del(r.id)}><Trash2 className="h-3.5 w-3.5 text-rose-500" /></Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-5">
        <h3 className="font-semibold text-sm mb-3">Recent Runs</h3>
        {logs.length === 0 ? (
          <div className="text-xs text-[var(--gs-muted)] py-6 text-center">No runs yet — trigger an event to see automations fire.</div>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {logs.map((l, i) => (
              <div key={i} className="text-xs rounded-lg bg-[var(--gs-surface-2)] p-2">
                <span className="font-medium">{l.rule_name || l.rule_id}</span>
                <span className="text-[var(--gs-muted)]"> · {l.event_type} · {l.ts ? new Date(l.ts).toLocaleTimeString() : ""}</span>
                <pre className="mt-1 text-[10px] text-[var(--gs-muted)] overflow-x-auto">{JSON.stringify(l.results, null, 2)}</pre>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
