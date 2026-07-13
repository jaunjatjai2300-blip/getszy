import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Shield, AlertTriangle, MonitorSmartphone, Key, Lock, Globe,
  Clock, Users, RefreshCw, Plus, RotateCw, Trash2, CheckCircle2,
  XCircle, Eye, EyeOff, BarChart3, Smartphone, Laptop, Server,
  Fingerprint, Activity, Search, Copy
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

function HealthDot({ ok }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}/>;
}

function SeverityBadge({ level }) {
  const styles = {
    critical: "bg-rose-100 text-rose-700",
    high: "bg-orange-100 text-orange-700",
    medium: "bg-amber-100 text-amber-700",
    low: "bg-blue-100 text-blue-700",
    info: "bg-slate-100 text-slate-600",
  };
  return <Badge className={`text-[10px] ${styles[level] || styles.info}`}>{level}</Badge>;
}

function GaugeRing({ value, label, color = "var(--gs-teal)" }) {
  const pct = Math.min(value || 0, 100);
  const radius = 32;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (pct / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="#E7D9CE" strokeWidth="6"/>
        <circle cx="40" cy="40" r={radius} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 40 40)" className="transition-all duration-500"/>
        <text x="40" y="40" textAnchor="middle" dominantBaseline="central" className="text-sm font-bold fill-[var(--gs-ink)]">{pct}%</text>
      </svg>
      <span className="text-[10px] text-[var(--gs-muted)] text-center">{label}</span>
    </div>
  );
}

export default function EnterpriseSecurity() {
  const [threats, setThreats] = useState([]);
  const [devices, setDevices] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [compliance, setCompliance] = useState(null);
  const [sso, setSso] = useState(null);
  const [sessionChart, setSessionChart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeySecret, setNewKeySecret] = useState("");
  const [revealedKeys, setRevealedKeys] = useState({});
  const [tab, setTab] = useState("threats");

  const load = async () => {
    setError(false);
    try {
      const [t, d, k, c, s, sc] = await Promise.all([
        api.get("/admin/enterprise-security/threats").catch(() => ({ data: { items: [] } })),
        api.get("/admin/enterprise-security/devices").catch(() => ({ data: { items: [] } })),
        api.get("/admin/enterprise-security/api-keys").catch(() => ({ data: { items: [] } })),
        api.get("/admin/enterprise-security/compliance").catch(() => ({ data: null })),
        api.get("/admin/enterprise-security/sso").catch(() => ({ data: null })),
        api.get("/admin/enterprise-security/session-analytics").catch(() => ({ data: null })),
      ]);
      setThreats(t.data?.items || []);
      setDevices(d.data?.items || []);
      setApiKeys(k.data?.items || []);
      setCompliance(c.data);
      setSso(s.data);
      setSessionChart(sc.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const revokeDevice = async (id) => {
    try {
      await api.post(`/admin/enterprise-security/devices/${id}/revoke`);
      setDevices(prev => prev.map(d => d.id === id ? { ...d, status: "revoked" } : d));
    } catch { /* silent */ }
  };

  const createApiKey = async () => {
    if (!newKeyName.trim()) return;
    try {
      const r = await api.post("/admin/enterprise-security/api-keys", { name: newKeyName });
      setNewKeySecret(r.data?.key || "");
      setApiKeys(prev => [...prev, r.data?.item].filter(Boolean));
      setNewKeyName("");
      setShowKeyDialog(true);
    } catch { /* silent */ }
  };

  const rotateKey = async (id) => {
    try {
      const r = await api.post(`/admin/enterprise-security/api-keys/${id}/rotate`);
      setNewKeySecret(r.data?.key || "");
      setApiKeys(prev => prev.map(k => k.id === id ? { ...k, ...r.data?.item } : k));
      setShowKeyDialog(true);
    } catch { /* silent */ }
  };

  const revokeKey = async (id) => {
    try {
      await api.post(`/admin/enterprise-security/api-keys/${id}/revoke`);
      setApiKeys(prev => prev.map(k => k.id === id ? { ...k, status: "revoked" } : k));
    } catch { /* silent */ }
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Enterprise Security</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Threat detection, device management, API keys & compliance</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      {/* Compliance Gauges */}
      {compliance && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Compliance Dashboard</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="p-5 flex justify-center">
              <GaugeRing value={compliance.mfa_percent} label="MFA Adoption" color="#2F7E7A"/>
            </Card>
            <Card className="p-5 flex justify-center">
              <GaugeRing value={compliance.password_strength} label="Password Strength" color="#10B981"/>
            </Card>
            <Card className="p-5 flex justify-center">
              <GaugeRing value={compliance.session_freshness} label="Session Freshness" color="#6366F1"/>
            </Card>
            <Card className="p-5 flex justify-center">
              <GaugeRing value={compliance.overall_score} label="Overall Score" color="#2F7E7A"/>
            </Card>
          </div>
        </div>
      )}

      {/* SSO Status */}
      {sso && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">SSO Status</div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { name: "Google", configured: sso.google_configured, icon: Globe },
              { name: "GitHub", configured: sso.github_configured, icon: Server },
            ].map(p => (
              <Card key={p.name} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <p.icon className="h-4 w-4 text-[var(--gs-muted)]"/>
                    <span className="text-sm font-semibold">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <HealthDot ok={p.configured}/>
                    <span className={`text-xs ${p.configured ? "text-emerald-600" : "text-[var(--gs-muted)]"}`}>
                      {p.configured ? "Configured" : "Not configured"}
                    </span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="threats">Threats ({threats.length})</TabsTrigger>
          <TabsTrigger value="devices">Devices ({devices.length})</TabsTrigger>
          <TabsTrigger value="apikeys">API Keys ({apiKeys.length})</TabsTrigger>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
        </TabsList>

        <TabsContent value="threats" className="mt-4">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-rose-500"/>Threat Detection
              </h3>
            </div>
            {threats.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">
                <Shield className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi threats detected nahi
              </div>
            ) : (
              <div className="space-y-2">
                {threats.map((t, i) => (
                  <div key={t.id || i} className="flex items-center gap-3 p-3 rounded-xl border bg-white">
                    <AlertTriangle className="h-4 w-4 text-rose-500 flex-shrink-0"/>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{t.title || t.type}</div>
                      <div className="text-[11px] text-[var(--gs-muted)] truncate">{t.description || t.detail}</div>
                    </div>
                    <SeverityBadge level={t.severity}/>
                    <span className="text-[10px] text-[var(--gs-muted)] flex-shrink-0">{t.time || t.created_at}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="devices" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <MonitorSmartphone className="h-4 w-4 text-[var(--gs-teal)]"/>Device Management
            </h3>
            {devices.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi devices nahi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Device</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead>Last Active</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {devices.map((d, i) => (
                      <TableRow key={d.id || i}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {d.os?.includes("Windows") ? <Laptop className="h-4 w-4"/> : <Smartphone className="h-4 w-4"/>}
                            <span className="text-xs">{d.device || d.browser}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">{d.user_name || d.user_email}</TableCell>
                        <TableCell className="text-xs font-mono">{d.ip}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{d.last_active}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-[10px] ${d.status === "active" ? "text-emerald-600" : "text-rose-500"}`}>
                            {d.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          {d.status === "active" && (
                            <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => revokeDevice(d.id)}>
                              <Trash2 className="h-3 w-3 mr-1"/>Revoke
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="apikeys" className="mt-4">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Key className="h-4 w-4 text-[var(--gs-teal)]"/>API Keys
              </h3>
              <Dialog open={showKeyDialog} onOpenChange={setShowKeyDialog}>
                <DialogTrigger asChild>
                  <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]">
                    <Plus className="h-3 w-3 mr-1"/>Create Key
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create API Key</DialogTitle>
                  </DialogHeader>
                  {newKeySecret ? (
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800">
                        Copy this key now — it won't be shown again.
                      </div>
                      <code className="block p-3 rounded-lg bg-[var(--gs-surface-2)] text-xs font-mono break-all">{newKeySecret}</code>
                      <Button size="sm" onClick={() => { navigator.clipboard.writeText(newKeySecret); }}>
                        <Copy className="h-3 w-3 mr-1"/>Copy
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <Input placeholder="Key name" value={newKeyName} onChange={e => setNewKeyName(e.target.value)}/>
                      <Button size="sm" className="bg-[var(--gs-teal)]" onClick={createApiKey}>Generate</Button>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </div>
            {apiKeys.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi API keys nahi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Key</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiKeys.map((k, i) => (
                      <TableRow key={k.id || i}>
                        <TableCell className="text-xs font-semibold">{k.name}</TableCell>
                        <TableCell className="text-xs font-mono">{k.key_preview || k.prefix || "••••••••"}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{k.created_at}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{k.last_used || "Never"}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-[10px] ${k.status === "active" ? "text-emerald-600" : "text-rose-500"}`}>
                            {k.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right space-x-1">
                          <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => rotateKey(k.id)}>
                            <RotateCw className="h-3 w-3"/>
                          </Button>
                          <Button variant="outline" size="sm" className="h-7 text-[10px] text-rose-500" onClick={() => revokeKey(k.id)}>
                            <Trash2 className="h-3 w-3"/>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="sessions" className="mt-4">
          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                <Clock className="h-4 w-4 text-[var(--gs-teal)]"/>Sessions by Device
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={sessionChart?.by_device || []}>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="device" stroke="#6B625B" fontSize={11}/>
                  <YAxis stroke="#6B625B" fontSize={11} allowDecimals={false}/>
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
                  <Bar dataKey="count" fill="#2F7E7A" radius={[4, 4, 0, 0]}/>
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                <Activity className="h-4 w-4 text-[var(--gs-teal)]"/>Sessions by Hour
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={sessionChart?.by_hour || []}>
                  <defs><linearGradient id="sessGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.5}/>
                    <stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/>
                  </linearGradient></defs>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="hour" stroke="#6B625B" fontSize={11}/>
                  <YAxis stroke="#6B625B" fontSize={11} allowDecimals={false}/>
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
                  <Area type="monotone" dataKey="count" stroke="#2F7E7A" fill="url(#sessGrad)"/>
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
