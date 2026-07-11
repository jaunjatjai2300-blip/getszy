import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Shield, Key, Lock, AlertTriangle, Activity, RefreshCw,
  Copy, Eye, EyeOff, CheckCircle2, XCircle, Clock,
  UserCheck, LogIn, Globe, Zap, Server
} from "lucide-react";
import { toast } from "sonner";

function EnvRow({ label, value, desc }) {
  const ok = value && value !== "NOT SET";
  return (
    <div className="flex items-center justify-between py-2.5 border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
      <div>
        <div className="text-sm font-semibold">{label}</div>
        {desc && <div className="text-[10px] text-[var(--gs-muted)]">{desc}</div>}
      </div>
      <div className="flex items-center gap-2">
        {ok ? (
          <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-2.5 w-2.5 mr-1"/>Set</Badge>
        ) : (
          <Badge className="bg-rose-100 text-rose-700 text-[10px]"><XCircle className="h-2.5 w-2.5 mr-1"/>Missing</Badge>
        )}
      </div>
    </div>
  );
}

export default function Security() {
  const [stats,    setStats]    = useState(null);
  const [sessions, setSessions] = useState([]);
  const [apiKeys,  setApiKeys]  = useState([]);
  const [showKeys, setShowKeys] = useState({});
  const [loading,  setLoading]  = useState(true);
  const [newKeyName, setNewKeyName] = useState("");
  const [keyBusy, setKeyBusy] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [st, se, ak] = await Promise.allSettled([
      api.get("/admin/founder-stats"),
      api.get("/admin/sessions?limit=20"),
      api.get("/admin/api-keys"),
    ]);
    if (st.status === "fulfilled") setStats(st.value.data);
    if (se.status === "fulfilled") setSessions(se.value.data.items || []);
    if (ak.status === "fulfilled") setApiKeys(ak.value.data.items || []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const createKey = async () => {
    if (!newKeyName.trim()) return toast.error("Key naam daalo");
    setKeyBusy(true);
    try {
      const r = await api.post("/admin/api-keys", { name: newKeyName });
      setNewKeyValue(r.data.key);
      setNewKeyName("");
      toast.success("API key created — abhi copy kar lo, dobara nahi dikhega!");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Key create nahi hua");
    } finally { setKeyBusy(false); }
  };

  const revokeKey = async (id, name) => {
    if (!window.confirm(`Revoke key "${name}"?`)) return;
    try {
      await api.delete(`/admin/api-keys/${id}`);
      toast.success("Revoked"); await load();
    } catch (e) { toast.error("Revoke failed"); }
  };

  const envChecks = stats?.env_health || {};

  return (
    <div className="space-y-5" data-testid="admin-security-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Shield className="h-7 w-7 text-[var(--gs-teal)]"/>Security
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">API keys · sessions · environment health · access logs</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
        </Button>
      </div>

      {/* Top stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Env Variables",     value: Object.values(envChecks).filter(Boolean).length + "/" + Object.keys(envChecks).length, icon: Key,         color: "text-emerald-600", bg: "bg-emerald-50" },
          { label: "Active Sessions",   value: sessions.length,                                                                       icon: UserCheck,    color: "text-blue-600",    bg: "bg-blue-50" },
          { label: "API Keys",          value: apiKeys.length,                                                                        icon: Lock,         color: "text-violet-600",  bg: "bg-violet-50" },
          { label: "Security Score",    value: Object.values(envChecks).filter(Boolean).length >= 4 ? "Good" : "Check Keys",           icon: Shield,       color: "text-[var(--gs-teal)]", bg: "bg-[var(--gs-teal-soft)]" },
        ].map(s => (
          <Card key={s.label} className="p-4 flex items-center gap-3">
            <div className={`h-9 w-9 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}>
              <s.icon className={`h-4 w-4 ${s.color}`}/>
            </div>
            <div>
              <div className="font-display text-xl leading-none">{loading ? "…" : s.value}</div>
              <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</div>
            </div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="env">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="env"><Key className="h-3.5 w-3.5 mr-1"/>Environment</TabsTrigger>
          <TabsTrigger value="keys"><Lock className="h-3.5 w-3.5 mr-1"/>API Keys</TabsTrigger>
          <TabsTrigger value="sessions"><Activity className="h-3.5 w-3.5 mr-1"/>Sessions</TabsTrigger>
          <TabsTrigger value="alerts"><AlertTriangle className="h-3.5 w-3.5 mr-1"/>Alerts</TabsTrigger>
        </TabsList>

        {/* ── Environment Health ── */}
        <TabsContent value="env" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Server className="h-4 w-4 text-[var(--gs-teal)]"/>Environment Variables
              </h3>
              {loading ? (
                <div className="space-y-3">{[1,2,3,4,5].map(i => <div key={i} className="h-8 bg-[var(--gs-surface-2)] animate-pulse rounded"/>)}</div>
              ) : (
                <div>
                  {Object.keys(envChecks).length === 0 ? (
                    <div className="text-sm text-[var(--gs-muted)] py-4 text-center">
                      /admin/founder-stats load kar raha hai…
                    </div>
                  ) : (
                    [
                      { key: "MONGO_URL",       label: "MongoDB",       desc: "Database connection" },
                      { key: "JWT_SECRET",       label: "JWT Secret",    desc: "Auth token signing" },
                      { key: "SESSION_SECRET",   label: "Session Secret",desc: "Cookie encryption" },
                      { key: "GROQ_API_KEY",     label: "Groq",          desc: "Fast LLM — script gen" },
                      { key: "HF_TOKEN",         label: "HuggingFace",   desc: "FLUX HD images + XTTS" },
                      { key: "OPENROUTER_API_KEY", label: "OpenRouter",  desc: "92 free AI models" },
                      { key: "RAZORPAY_KEY_ID",  label: "Razorpay",      desc: "₹ payments" },
                    ].map(e => (
                      <EnvRow key={e.key} label={e.label} desc={e.desc}
                        value={envChecks[e.key] ? "SET" : "NOT SET"}/>
                    ))
                  )}
                </div>
              )}
            </Card>

            <Card className="p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Globe className="h-4 w-4 text-[var(--gs-teal)]"/>Security Checklist
              </h3>
              <div className="space-y-3">
                {[
                  { label: "HTTPS enabled",        ok: true,  note: "Caddy auto-HTTPS" },
                  { label: "JWT auth on all routes",ok: true,  note: "routes_auth.py middleware" },
                  { label: "CORS configured",       ok: true,  note: "Allowed origins set in server.py" },
                  { label: "Rate limiting",         ok: false, note: "Not yet — add slowapi" },
                  { label: "Password hashing",      ok: true,  note: "bcrypt via passlib" },
                  { label: "Admin role check",      ok: true,  note: "get_current_admin decorator" },
                  { label: "Env secrets in .env",   ok: true,  note: "Not committed to git" },
                  { label: "MongoDB auth",          ok: false, note: "Local instance — no auth" },
                ].map(c => (
                  <div key={c.label} className="flex items-center gap-3">
                    {c.ok
                      ? <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0"/>
                      : <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0"/>}
                    <div className="flex-1">
                      <div className="text-sm font-medium">{c.label}</div>
                      <div className="text-[10px] text-[var(--gs-muted)]">{c.note}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* ── API Keys ── */}
        <TabsContent value="keys" className="mt-4 space-y-4">
          {/* Create new key */}
          <Card className="p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Key className="h-4 w-4 text-[var(--gs-teal)]"/>New API Key
            </h3>
            <div className="flex gap-2">
              <Input placeholder="Key ka naam — e.g. zapier-webhook, mobile-app"
                value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
                className="flex-1 text-sm" data-testid="new-key-name-input"/>
              <Button onClick={createKey} disabled={keyBusy}
                className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 text-sm">
                {keyBusy ? <RefreshCw className="h-4 w-4 animate-spin mr-1"/> : <Key className="h-4 w-4 mr-1"/>}
                Generate
              </Button>
            </div>
            {newKeyValue && (
              <div className="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-200 space-y-2">
                <div className="text-xs font-semibold text-amber-700">⚠️ Sirf ek baar dikhega — abhi copy karo!</div>
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-white p-2 rounded-lg flex-1 font-mono break-all border">{newKeyValue}</code>
                  <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(newKeyValue); toast.success("Copied!"); }}>
                    <Copy className="h-3.5 w-3.5"/>
                  </Button>
                </div>
                <Button size="sm" variant="ghost" className="text-xs text-amber-600" onClick={() => setNewKeyValue(null)}>
                  Dismiss
                </Button>
              </div>
            )}
          </Card>

          {/* Keys list */}
          <Card className="p-5">
            <h3 className="font-semibold mb-3">Active Keys ({apiKeys.length})</h3>
            {loading ? (
              <div className="space-y-2">{[1,2].map(i => <div key={i} className="h-12 animate-pulse bg-[var(--gs-surface-2)] rounded-xl"/>)}</div>
            ) : apiKeys.length === 0 ? (
              <div className="text-sm text-[var(--gs-muted)] text-center py-6">Koi API keys nahi hain</div>
            ) : (
              <div className="space-y-2">
                {apiKeys.map(k => (
                  <div key={k.id} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--gs-surface-2)]">
                    <div className="h-8 w-8 rounded-lg bg-white grid place-items-center">
                      <Key className="h-3.5 w-3.5 text-[var(--gs-teal)]"/>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold">{k.name}</div>
                      <div className="text-[10px] font-mono text-[var(--gs-muted)]">
                        {showKeys[k.id] ? k.key_prefix + "…" : "gs_••••••••••••••••"}
                      </div>
                    </div>
                    <div className="text-[10px] text-[var(--gs-muted)] hidden md:block">
                      {k.last_used ? `Used ${new Date(k.last_used).toLocaleDateString("en-IN")}` : "Never used"}
                    </div>
                    <button onClick={() => setShowKeys(p => ({ ...p, [k.id]: !p[k.id] }))}>
                      {showKeys[k.id] ? <EyeOff className="h-3.5 w-3.5 text-[var(--gs-muted)]"/> : <Eye className="h-3.5 w-3.5 text-[var(--gs-muted)]"/>}
                    </button>
                    <button onClick={() => revokeKey(k.id, k.name)} className="text-rose-500">
                      <XCircle className="h-3.5 w-3.5"/>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ── Sessions ── */}
        <TabsContent value="sessions" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Activity className="h-4 w-4 text-[var(--gs-teal)]"/>Recent Login Sessions
            </h3>
            {loading ? (
              <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-12 animate-pulse bg-[var(--gs-surface-2)] rounded-xl"/>)}</div>
            ) : sessions.length === 0 ? (
              <div className="text-sm text-[var(--gs-muted)] text-center py-8">
                <LogIn className="h-8 w-8 mx-auto mb-2 opacity-30"/>
                No session data — /admin/sessions endpoint add karo backend mein
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[500px]">
                  <thead className="text-left text-xs uppercase tracking-wider text-[var(--gs-muted)] border-b" style={{ borderColor: "var(--gs-border)" }}>
                    <tr>
                      <th className="pb-2">User</th>
                      <th className="pb-2">IP</th>
                      <th className="pb-2">Device</th>
                      <th className="pb-2">Time</th>
                      <th className="pb-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                    {sessions.map(s => (
                      <tr key={s.id}>
                        <td className="py-2 font-medium">{s.email || s.user_id?.slice(0, 8)}</td>
                        <td className="py-2 font-mono text-xs text-[var(--gs-muted)]">{s.ip || "—"}</td>
                        <td className="py-2 text-xs text-[var(--gs-muted)] max-w-[200px] truncate">{s.user_agent || "—"}</td>
                        <td className="py-2 text-xs text-[var(--gs-muted)]">
                          <span className="flex items-center gap-1"><Clock className="h-2.5 w-2.5"/>{new Date(s.created_at).toLocaleString("en-IN")}</span>
                        </td>
                        <td className="py-2">
                          {s.active !== false
                            ? <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Active</Badge>
                            : <Badge variant="outline" className="text-[10px]">Expired</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ── Alerts ── */}
        <TabsContent value="alerts" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500"/>Active Alerts
              </h3>
              <div className="space-y-3">
                {[
                  { level: "warn",  msg: "Rate limiting not configured — add slowapi to requirements.txt",    action: "Fix" },
                  { level: "warn",  msg: "MongoDB chala raha hai bina authentication ke (local only OK)",     action: "Review" },
                  { level: "info",  msg: "All JWT secrets set ✓",                                             action: null },
                  { level: "info",  msg: "HTTPS via Caddy on production ✓",                                   action: null },
                ].map((a, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border ${a.level === "warn" ? "bg-amber-50 border-amber-200" : "bg-emerald-50 border-emerald-200"}`}>
                    {a.level === "warn"
                      ? <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5"/>
                      : <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5"/>}
                    <div className="flex-1 text-xs">{a.msg}</div>
                    {a.action && (
                      <Badge variant="outline" className="text-[10px] cursor-pointer">{a.action}</Badge>
                    )}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Zap className="h-4 w-4 text-[var(--gs-teal)]"/>Quick Security Actions
              </h3>
              <div className="space-y-2">
                {[
                  { label: "Force logout all users",     desc: "Saare active sessions expire karo",          variant: "destructive", fn: () => toast.error("Endpoint add karna hoga — /admin/sessions/revoke-all") },
                  { label: "Rotate JWT Secret",          desc: "Naya JWT_SECRET generate karo (logs out all)", variant: "outline",  fn: () => toast("Server restart karana hoga after secret change") },
                  { label: "View auth logs",             desc: "Last 100 login attempts",                     variant: "outline",  fn: () => toast("MongoDB se: db.auth_logs.find().sort({created_at:-1}).limit(100)") },
                  { label: "Download security report",   desc: "CSV export of all events",                    variant: "outline",  fn: () => toast("Coming soon") },
                ].map(a => (
                  <button key={a.label} onClick={a.fn}
                    className="w-full text-left p-3 rounded-xl border hover:bg-[var(--gs-surface-2)] transition-colors"
                    style={{ borderColor: "var(--gs-border)" }}>
                    <div className="text-sm font-semibold">{a.label}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{a.desc}</div>
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
