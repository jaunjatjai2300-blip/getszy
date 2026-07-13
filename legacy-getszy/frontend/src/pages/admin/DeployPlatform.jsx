import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Rocket, RefreshCw, ArrowLeft, Undo2, Eye, Terminal, Globe,
  Lock, Unlock, Plus, Trash2, ChevronDown, ChevronRight, CheckCircle2,
  XCircle, Clock, Loader2, AlertTriangle, Server, FileCode2, Copy,
  EyeOff, File
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const STATUS_STYLES = {
  pending: "bg-amber-100 text-amber-700",
  building: "bg-blue-100 text-blue-700",
  deploying: "bg-violet-100 text-violet-700",
  live: "bg-emerald-100 text-emerald-700",
  failed: "bg-rose-100 text-rose-700",
  stopped: "bg-slate-100 text-slate-600",
};

const STATUS_ICONS = {
  pending: Clock,
  building: Loader2,
  deploying: Rocket,
  live: CheckCircle2,
  failed: XCircle,
  stopped: AlertTriangle,
};

export default function DeployPlatform() {
  const [deployments, setDeployments] = useState([]);
  const [releases, setReleases] = useState([]);
  const [envVars, setEnvVars] = useState([]);
  const [domains, setDomains] = useState([]);
  const [selectedDeploy, setSelectedDeploy] = useState(null);
  const [deployLogs, setDeployLogs] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState("deployments");
  const [deploying, setDeploying] = useState(false);

  const load = async () => {
    setError(false);
    try {
      const [d, r, e, dm] = await Promise.all([
        api.get("/admin/deploy-platform/deployments").catch(() => ({ data: { items: [] } })),
        api.get("/admin/deploy-platform/releases").catch(() => ({ data: { items: [] } })),
        api.get("/admin/deploy-platform/env-vars").catch(() => ({ data: { items: [] } })),
        api.get("/admin/deploy-platform/domains").catch(() => ({ data: { items: [] } })),
      ]);
      setDeployments(d.data?.items || []);
      setReleases(r.data?.items || []);
      setEnvVars(e.data?.items || []);
      setDomains(dm.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const triggerDeploy = async () => {
    setDeploying(true);
    try {
      const r = await api.post("/admin/deploy-platform/deploy");
      if (r.data?.id) setDeployments(prev => [r.data, ...prev]);
      await load();
    } catch { /* silent */ }
    setDeploying(false);
  };

  const viewLogs = async (id) => {
    try {
      const r = await api.get(`/admin/deploy-platform/deployments/${id}/logs`);
      setDeployLogs(r.data?.logs || "");
      setSelectedDeploy(id);
    } catch { /* silent */ }
  };

  const rollback = async (id) => {
    try {
      await api.post(`/admin/deploy-platform/deployments/${id}/rollback`);
      await load();
    } catch { /* silent */ }
  };

  const addEnvVar = async (key, value) => {
    try {
      const r = await api.post("/admin/deploy-platform/env-vars", { key, value });
      setEnvVars(prev => [...prev, r.data?.item].filter(Boolean));
    } catch { /* silent */ }
  };

  const deleteEnvVar = async (id) => {
    try {
      await api.delete(`/admin/deploy-platform/env-vars/${id}`);
      setEnvVars(prev => prev.filter(e => e.id !== id));
    } catch { /* silent */ }
  };

  const addDomain = async (domain) => {
    try {
      const r = await api.post("/admin/deploy-platform/domains", { domain });
      setDomains(prev => [...prev, r.data?.item].filter(Boolean));
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
          <h1 className="font-display text-3xl">Deployment Platform</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Deploy, rollback, manage env vars & domains</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={triggerDeploy} disabled={deploying}>
            <Rocket className={`h-3.5 w-3.5 mr-1 ${deploying ? "animate-spin" : ""}`}/>
            {deploying ? "Deploying…" : "Deploy Now"}
          </Button>
          <Button variant="outline" size="sm" className="h-8" onClick={load}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="deployments">Deployments</TabsTrigger>
          <TabsTrigger value="releases">Releases</TabsTrigger>
          <TabsTrigger value="envvars">Env Vars</TabsTrigger>
          <TabsTrigger value="domains">Domains</TabsTrigger>
        </TabsList>

        <TabsContent value="deployments" className="mt-4 space-y-4">
          <Card className="p-5">
            {selectedDeploy && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-[var(--gs-teal)]"/>Deploy Logs — #{selectedDeploy}
                  </h3>
                  <Button variant="ghost" size="sm" className="h-7" onClick={() => setSelectedDeploy(null)}>
                    <ArrowLeft className="h-3 w-3 mr-1"/>Close
                  </Button>
                </div>
                <pre className="p-4 rounded-lg bg-black text-green-400 text-xs font-mono max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {deployLogs || "No logs available"}
                </pre>
              </div>
            )}

            <h3 className="font-semibold text-sm mb-4">Recent Deployments</h3>
            {deployments.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">
                <Rocket className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi deployments nahi — Deploy Now pe click karo
              </div>
            ) : (
              <div className="space-y-2">
                {deployments.map((d, i) => {
                  const StatusIcon = STATUS_ICONS[d.status] || Clock;
                  return (
                    <div key={d.id || i} className="flex items-center gap-3 p-3 rounded-xl border bg-white">
                      <StatusIcon className={`h-4 w-4 flex-shrink-0 ${d.status === "live" ? "text-emerald-500" : d.status === "failed" ? "text-rose-500" : "text-[var(--gs-muted)]"}`}/>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold">#{d.id || d.version}</span>
                          <Badge className={`text-[10px] ${STATUS_STYLES[d.status] || STATUS_STYLES.pending}`}>{d.status}</Badge>
                        </div>
                        <div className="text-[11px] text-[var(--gs-muted)]">{d.commit || d.branch || "main"} · {d.created_at}</div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => viewLogs(d.id)}>
                          <Eye className="h-3 w-3 mr-1"/>Logs
                        </Button>
                        {d.status === "failed" && (
                          <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => rollback(d.id)}>
                            <Undo2 className="h-3 w-3 mr-1"/>Rollback
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="releases" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4">Releases</h3>
            {releases.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi releases nahi</div>
            ) : (
              <div className="space-y-2">
                {releases.map((r, i) => (
                  <div key={r.id || i} className="flex items-center gap-3 p-3 rounded-xl border bg-white">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0"/>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono font-semibold">{r.version}</span>
                        {r.is_current && <Badge className="bg-[var(--gs-teal)] text-white text-[10px]">Current</Badge>}
                      </div>
                      <div className="text-[11px] text-[var(--gs-muted)]">{r.notes || r.description} · {r.created_at}</div>
                    </div>
                    <Badge variant="outline" className="text-[10px">{r.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="envvars" className="mt-4">
          <EnvVarsManager envVars={envVars} onAdd={addEnvVar} onDelete={deleteEnvVar}/>
        </TabsContent>

        <TabsContent value="domains" className="mt-4">
          <DomainManager domains={domains} onAdd={addDomain}/>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EnvVarsManager({ envVars, onAdd, onDelete }) {
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [showValues, setShowValues] = useState({});

  const toggleShow = (id) => setShowValues(prev => ({ ...prev, [id]: !prev[id] }));

  const handleAdd = () => {
    if (!newKey.trim()) return;
    onAdd(newKey, newValue);
    setNewKey("");
    setNewValue("");
  };

  return (
    <Card className="p-5">
      <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
        <File className="h-4 w-4 text-[var(--gs-teal)]"/>Environment Variables
      </h3>

      <div className="flex items-center gap-2 mb-4">
        <Input placeholder="KEY" value={newKey} onChange={e => setNewKey(e.target.value)} className="flex-1 font-mono text-xs"/>
        <Input placeholder="value" value={newValue} onChange={e => setNewValue(e.target.value)} className="flex-1 font-mono text-xs"/>
        <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={handleAdd}>
          <Plus className="h-3.5 w-3.5 mr-1"/>Add
        </Button>
      </div>

      {envVars.length === 0 ? (
        <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi env vars nahi</div>
      ) : (
        <div className="space-y-1.5">
          {envVars.map((ev, i) => (
            <div key={ev.id || i} className="flex items-center gap-2 p-2.5 rounded-lg bg-[var(--gs-surface-2)]">
              <span className="text-xs font-mono font-semibold text-[var(--gs-teal)] min-w-[120px]">{ev.key}</span>
              <span className="text-xs font-mono flex-1">{showValues[ev.id] ? ev.value : "••••••••"}</span>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => toggleShow(ev.id)}>
                {showValues[ev.id] ? <EyeOff className="h-3 w-3"/> : <Eye className="h-3 w-3"/>}
              </Button>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-rose-500" onClick={() => onDelete(ev.id)}>
                <Trash2 className="h-3 w-3"/>
              </Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function DomainManager({ domains, onAdd }) {
  const [newDomain, setNewDomain] = useState("");

  const handleAdd = () => {
    if (!newDomain.trim()) return;
    onAdd(newDomain);
    setNewDomain("");
  };

  return (
    <Card className="p-5">
      <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
        <Globe className="h-4 w-4 text-[var(--gs-teal)]"/>Domain Manager
      </h3>

      <div className="flex items-center gap-2 mb-4">
        <Input placeholder="yourdomain.com" value={newDomain} onChange={e => setNewDomain(e.target.value)} className="flex-1 text-xs"/>
        <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={handleAdd}>
          <Plus className="h-3.5 w-3.5 mr-1"/>Add Domain
        </Button>
      </div>

      {domains.length === 0 ? (
        <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi domains nahi</div>
      ) : (
        <div className="space-y-2">
          {domains.map((d, i) => (
            <div key={d.id || i} className="flex items-center gap-3 p-3 rounded-xl border bg-white">
              <Globe className="h-4 w-4 text-[var(--gs-teal)] flex-shrink-0"/>
              <div className="flex-1">
                <div className="text-sm font-semibold">{d.domain}</div>
                <div className="text-[11px] text-[var(--gs-muted)]">Added {d.created_at}</div>
              </div>
              <div className="flex items-center gap-1.5">
                {d.ssl ? <Lock className="h-3.5 w-3.5 text-emerald-500"/> : <Unlock className="h-3.5 w-3.5 text-amber-500"/>}
                <Badge variant="outline" className={`text-[10px] ${d.ssl ? "text-emerald-600" : "text-amber-600"}`}>
                  {d.ssl ? "SSL Active" : "No SSL"}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
