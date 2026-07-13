import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Server, Database, HardDrive, Cpu, Activity, RefreshCw, Play,
  Pause, Clock, Trash2, Plus, Search, Filter, Terminal,
  AlertTriangle, CheckCircle2, XCircle, BarChart3, Layers,
  Timer, Zap, Eye, RotateCw
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function StatusDot({ ok }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}/>;
}

const LEVEL_COLORS = {
  error: "bg-rose-100 text-rose-700",
  warn: "bg-amber-100 text-amber-700",
  info: "bg-blue-100 text-blue-700",
  debug: "bg-slate-100 text-slate-600",
};

export default function OperationsCenter() {
  const [containers, setContainers] = useState([]);
  const [redis, setRedis] = useState(null);
  const [mongodb, setMongodb] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [crons, setCrons] = useState([]);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState("containers");
  const [logFilter, setLogFilter] = useState("");
  const [logLevel, setLogLevel] = useState("all");

  const load = async () => {
    setError(false);
    try {
      const [c, r, m, w, cr, l, me] = await Promise.all([
        api.get("/admin/ops/containers").catch(() => ({ data: { items: [] } })),
        api.get("/admin/ops/redis").catch(() => ({ data: null })),
        api.get("/admin/ops/mongodb").catch(() => ({ data: null })),
        api.get("/admin/ops/workers").catch(() => ({ data: { items: [] } })),
        api.get("/admin/ops/cron-jobs").catch(() => ({ data: { items: [] } })),
        api.get("/admin/ops/request-logs?limit=50").catch(() => ({ data: { items: [] } })),
        api.get("/admin/ops/metrics").catch(() => ({ data: null })),
      ]);
      setContainers(c.data?.items || []);
      setRedis(r.data);
      setMongodb(m.data);
      setWorkers(w.data?.items || []);
      setCrons(cr.data?.items || []);
      setLogs(l.data?.items || []);
      setMetrics(me.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const restartContainer = async (id) => {
    try {
      await api.post(`/admin/ops/containers/${id}/restart`);
      await load();
    } catch { /* silent */ }
  };

  const toggleCron = async (id, enabled) => {
    try {
      await api.post(`/admin/ops/cron-jobs/${id}/${enabled ? "enable" : "disable"}`);
      setCrons(prev => prev.map(c => c.id === id ? { ...c, enabled: !enabled } : c));
    } catch { /* silent */ }
  };

  const filteredLogs = logs.filter(log => {
    const matchFilter = !logFilter || log.message?.toLowerCase().includes(logFilter.toLowerCase()) || log.path?.toLowerCase().includes(logFilter.toLowerCase());
    const matchLevel = logLevel === "all" || log.level === logLevel;
    return matchFilter && matchLevel;
  });

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Operations Center</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Containers, Redis, MongoDB, workers, crons & logs</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      {/* System Metrics Charts */}
      {metrics && (
        <div className="grid lg:grid-cols-3 gap-4">
          {[
            { label: "CPU Usage", data: metrics.cpu_history, k: "cpu", color: "#2F7E7A" },
            { label: "RAM Usage", data: metrics.ram_history, k: "ram", color: "#6366F1" },
            { label: "Disk I/O", data: metrics.disk_history, k: "disk", color: "#F59E0B" },
          ].map(ch => (
            <Card key={ch.label} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{ch.label}</span>
                <span className="text-xs font-semibold">{ch.data?.[ch.data.length - 1]?.value ?? "—"}%</span>
              </div>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={ch.data || []}>
                  <defs><linearGradient id={`grad-${ch.k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={ch.color} stopOpacity={0.5}/>
                    <stop offset="100%" stopColor={ch.color} stopOpacity={0}/>
                  </linearGradient></defs>
                  <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
                  <XAxis dataKey="time" stroke="#6B625B" fontSize={10}/>
                  <YAxis stroke="#6B625B" fontSize={10} domain={[0, 100]}/>
                  <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8, fontSize: 11 }}/>
                  <Area type="monotone" dataKey="value" stroke={ch.color} fill={`url(#grad-${ch.k})`}/>
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          ))}
        </div>
      )}

      {/* Redis + MongoDB Status */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5 text-[var(--gs-teal)]"/>Redis
            </span>
            <StatusDot ok={redis?.connected}/>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Keys", value: redis?.keys },
              { label: "Memory", value: redis?.memory },
              { label: "Hits", value: redis?.hit_rate },
              { label: "Uptime", value: redis?.uptime },
            ].map(s => (
              <div key={s.label}>
                <div className="text-[10px] text-[var(--gs-muted)]">{s.label}</div>
                <div className="text-sm font-semibold">{s.value ?? "—"}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5 text-emerald-500"/>MongoDB
            </span>
            <StatusDot ok={mongodb?.connected}/>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Collections", value: mongodb?.collections },
              { label: "Documents", value: mongodb?.documents },
              { label: "Size", value: mongodb?.size },
              { label: "Uptime", value: mongodb?.uptime },
            ].map(s => (
              <div key={s.label}>
                <div className="text-[10px] text-[var(--gs-muted)]">{s.label}</div>
                <div className="text-sm font-semibold">{s.value ?? "—"}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="containers"><Server className="h-3 w-3 mr-1 inline"/>Containers</TabsTrigger>
          <TabsTrigger value="workers"><Zap className="h-3 w-3 mr-1 inline"/>Workers</TabsTrigger>
          <TabsTrigger value="crons"><Clock className="h-3 w-3 mr-1 inline"/>Cron Jobs</TabsTrigger>
          <TabsTrigger value="logs"><Terminal className="h-3 w-3 mr-1 inline"/>Logs</TabsTrigger>
        </TabsList>

        {/* Containers */}
        <TabsContent value="containers" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Server className="h-4 w-4 text-[var(--gs-teal)]"/>Docker Containers
            </h3>
            {containers.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">
                <Server className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi containers nahi
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Image</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Ports</TableHead>
                      <TableHead>Uptime</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {containers.map((c, i) => (
                      <TableRow key={c.id || i}>
                        <TableCell className="text-xs font-semibold font-mono">{c.name}</TableCell>
                        <TableCell className="text-xs font-mono text-[var(--gs-muted)]">{c.image}</TableCell>
                        <TableCell>
                          <Badge className={`text-[10px] ${
                            c.state === "running" ? "bg-emerald-100 text-emerald-700" :
                            c.state === "exited" ? "bg-rose-100 text-rose-700" :
                            "bg-amber-100 text-amber-700"
                          }`}>{c.state}</Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono text-[var(--gs-muted)]">{c.ports || "—"}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{c.uptime || "—"}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => restartContainer(c.id)}>
                            <RotateCw className="h-3 w-3 mr-1"/>Restart
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

        {/* Workers */}
        <TabsContent value="workers" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Zap className="h-4 w-4 text-[var(--gs-teal)]"/>Queue Workers
            </h3>
            {workers.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi workers nahi</div>
            ) : (
              <div className="space-y-2">
                {workers.map((w, i) => (
                  <div key={w.id || i} className="flex items-center gap-3 p-3 rounded-xl border bg-white">
                    <StatusDot ok={w.status === "active"}/>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold">{w.name || w.queue}</div>
                      <div className="text-[11px] text-[var(--gs-muted)]">
                        {w.processed || 0} processed · {w.failed || 0} failed · {w.pending || 0} pending
                      </div>
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${
                      w.status === "active" ? "text-emerald-600" : "text-rose-500"
                    }`}>{w.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Cron Jobs */}
        <TabsContent value="crons" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4 text-[var(--gs-teal)]"/>Cron Jobs
            </h3>
            {crons.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi cron jobs nahi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Schedule</TableHead>
                      <TableHead>Last Run</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {crons.map((c, i) => (
                      <TableRow key={c.id || i}>
                        <TableCell className="text-xs font-semibold">{c.name}</TableCell>
                        <TableCell className="text-xs font-mono text-[var(--gs-muted)]">{c.schedule}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{c.last_run || "Never"}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-[10px] ${c.enabled ? "text-emerald-600" : "text-[var(--gs-muted)]"}`}>
                            {c.enabled ? "Enabled" : "Disabled"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="outline" size="sm" className="h-7 text-[10px]"
                            onClick={() => toggleCron(c.id, c.enabled)}>
                            {c.enabled ? <Pause className="h-3 w-3 mr-1"/> : <Play className="h-3 w-3 mr-1"/>}
                            {c.enabled ? "Disable" : "Enable"}
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

        {/* Logs */}
        <TabsContent value="logs" className="mt-4">
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--gs-muted)]"/>
                <Input placeholder="Filter logs…" value={logFilter} onChange={e => setLogFilter(e.target.value)} className="pl-9 text-xs"/>
              </div>
              <Select value={logLevel} onValueChange={setLogLevel}>
                <SelectTrigger className="w-28 h-8 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Levels</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="warn">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="debug">Debug</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Terminal className="h-4 w-4 text-[var(--gs-teal)]"/>
              Request Logs
              <Badge variant="outline" className="text-[10px]">{filteredLogs.length}</Badge>
            </h3>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Level</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-[var(--gs-muted)] text-sm">
                        Koi logs nahi
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredLogs.map((log, i) => (
                      <TableRow key={log.id || i}>
                        <TableCell>
                          <Badge className={`text-[9px] ${LEVEL_COLORS[log.level] || LEVEL_COLORS.info}`}>{log.level}</Badge>
                        </TableCell>
                        <TableCell className="text-xs max-w-[300px] truncate">{log.message}</TableCell>
                        <TableCell className="text-xs font-mono text-[var(--gs-muted)]">{log.path || "—"}</TableCell>
                        <TableCell>
                          {log.status_code && (
                            <Badge variant="outline" className={`text-[10px] ${
                              log.status_code < 400 ? "text-emerald-600" : log.status_code < 500 ? "text-amber-600" : "text-rose-600"
                            }`}>{log.status_code}</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-[10px] text-[var(--gs-muted)] whitespace-nowrap">{log.time || log.created_at}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
