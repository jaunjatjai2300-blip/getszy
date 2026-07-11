import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Server, Cpu, HardDrive, Activity, RefreshCw, CheckCircle2,
  XCircle, AlertTriangle, Wifi, Database, Clock, Zap, Globe,
  Container, MemoryStick, BarChart3, Terminal
} from "lucide-react";
import { toast } from "sonner";

function StatusDot({ ok, pulse }) {
  if (ok === null) return <span className="inline-block h-2 w-2 rounded-full bg-gray-300"/>;
  return (
    <span className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"} ${pulse ? "animate-pulse" : ""}`}/>
  );
}

function StatCard({ icon: Icon, label, value, sub, color = "text-[var(--gs-teal)]", bg = "bg-[var(--gs-teal-soft)]", loading }) {
  return (
    <Card className="p-4 flex items-center gap-3">
      <div className={`h-10 w-10 rounded-xl ${bg} grid place-items-center flex-shrink-0`}>
        <Icon className={`h-5 w-5 ${color}`}/>
      </div>
      <div>
        <div className="font-display text-xl leading-none">{loading ? "…" : value}</div>
        <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{label}</div>
        {sub && <div className="text-[9px] text-[var(--gs-muted)]">{sub}</div>}
      </div>
    </Card>
  );
}

function GaugeBar({ pct, color = "bg-[var(--gs-teal)]" }) {
  const c = pct >= 90 ? "bg-rose-500" : pct >= 70 ? "bg-amber-500" : color;
  return (
    <div className="h-1.5 w-full rounded-full bg-[var(--gs-surface-2)] overflow-hidden">
      <div className={`h-full rounded-full ${c} transition-all`} style={{ width: `${Math.min(pct, 100)}%` }}/>
    </div>
  );
}

export default function Servers() {
  const [health, setHealth] = useState(null);
  const [sysStats, setSysStats] = useState(null);
  const [envHealth, setEnvHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sysR, envR] = await Promise.allSettled([
        api.get("/admin/system-stats"),
        api.get("/admin/env-health"),
      ]);
      if (sysR.status === "fulfilled") { setSysStats(sysR.value.data); setHealth(sysR.value.data); }
      if (envR.status === "fulfilled") setEnvHealth(envR.value.data?.env || {});
      setLastRefresh(new Date());
    } catch (e) {
      toast.error("Server health fetch failed");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  const env = envHealth || {};
  const ram = sysStats?.ram;
  const disk = sysStats?.disk;
  const cpu = sysStats?.cpu_load;
  const mongo = sysStats?.mongo;
  const gpu = sysStats?.gpu;

  const formatUptime = (s) => {
    if (!s) return "—";
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  };

  const containers = [
    { name: "getszy-backend",  port: "8001", role: "FastAPI / Python",     ok: !!health,                        icon: Zap,      color: "text-[var(--gs-teal)]",  bg: "bg-[var(--gs-teal-soft)]" },
    { name: "getszy-frontend", port: "3000", role: "React / Node",          ok: true,                            icon: Globe,    color: "text-blue-600",           bg: "bg-blue-50" },
    { name: "getszy-mongo",    port: "27017",role: "MongoDB",               ok: mongo?.ok ?? !!env.MONGO_URL,    icon: Database, color: "text-emerald-600",        bg: "bg-emerald-50" },
    { name: "getszy-caddy",    port: "80/443",role: "Reverse Proxy / HTTPS",ok: true,                            icon: Server,   color: "text-violet-600",         bg: "bg-violet-50" },
  ];

  const aiStack = [
    { name: "Groq LLM",        ok: !!env.GROQ_API_KEY,       desc: "Script generation" },
    { name: "HuggingFace FLUX", ok: !!env.HF_TOKEN,           desc: "FLUX HD images" },
    { name: "OpenRouter",      ok: !!env.OPENROUTER_API_KEY,  desc: "92 free AI models" },
    { name: "Razorpay",        ok: !!env.RAZORPAY_KEY_ID,     desc: "₹ payment gateway" },
    { name: "Edge-TTS",        ok: true,                       desc: "Free Indian voices" },
    { name: "Pollinations",    ok: true,                       desc: "Free image gen" },
  ];

  return (
    <div className="space-y-5" data-testid="admin-servers-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Server className="h-7 w-7 text-[var(--gs-teal)]"/>Server Monitor
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            VPS 31.97.237.222 · 4 containers · Live health check
            {lastRefresh && <span className="ml-2 text-[10px]">Updated {lastRefresh.toLocaleTimeString("en-IN")}</span>}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
        </Button>
      </div>

      {/* Real system stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon={Activity}    label="Backend Status"  value={health ? "Online" : "Checking…"}    color="text-emerald-600" bg="bg-emerald-50" loading={loading}/>
        <StatCard icon={Clock}       label="Uptime"          value={formatUptime(sysStats?.uptime_s)}   color="text-blue-600"   bg="bg-blue-50"    loading={loading}/>
        <StatCard icon={Database}    label="MongoDB"         value={mongo?.ok ? `${mongo.ping_ms}ms` : "Down"} sub={mongo?.ok ? "Ping OK" : "Not reachable"} color="text-violet-600" bg="bg-violet-50" loading={loading}/>
        <StatCard icon={Zap}         label="AI Stack"        value={`${aiStack.filter(a=>a.ok).length}/${aiStack.length}`} color="text-amber-600" bg="bg-amber-50" loading={loading}/>
      </div>

      {/* RAM + Disk + CPU real gauges */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold"><MemoryStick className="h-4 w-4 text-[var(--gs-teal)]"/>RAM</div>
            <span className="text-xs text-[var(--gs-muted)]">{loading ? "…" : ram ? `${ram.used_mb} / ${ram.total_mb} MB` : "No data"}</span>
          </div>
          {ram && <GaugeBar pct={ram.used_pct}/>}
          <div className="text-[10px] text-[var(--gs-muted)]">{loading ? "Loading…" : ram ? `${ram.used_pct}% used · ${ram.avail_mb} MB free` : "N/A on this host"}</div>
        </Card>
        <Card className="p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold"><HardDrive className="h-4 w-4 text-violet-600"/>Disk</div>
            <span className="text-xs text-[var(--gs-muted)]">{loading ? "…" : disk ? `${disk.used_gb} / ${disk.total_gb} GB` : "No data"}</span>
          </div>
          {disk && <GaugeBar pct={disk.used_pct} color="bg-violet-500"/>}
          <div className="text-[10px] text-[var(--gs-muted)]">{loading ? "Loading…" : disk ? `${disk.used_pct}% used · ${disk.free_gb} GB free` : "N/A"}</div>
        </Card>
        <Card className="p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold"><Cpu className="h-4 w-4 text-amber-600"/>CPU Load</div>
            <span className="text-xs text-[var(--gs-muted)]">{loading ? "…" : cpu ? `${cpu["1m"]} avg` : "No data"}</span>
          </div>
          {cpu && <GaugeBar pct={Math.min(cpu["1m"] * 25, 100)} color="bg-amber-500"/>}
          <div className="text-[10px] text-[var(--gs-muted)]">{loading ? "Loading…" : cpu ? `1m: ${cpu["1m"]} · 5m: ${cpu["5m"]} · 15m: ${cpu["15m"]}` : "N/A"}</div>
        </Card>
      </div>

      {/* GPU badge */}
      {!loading && (
        <Card className="p-4 flex items-center gap-3">
          <div className={`h-10 w-10 rounded-xl grid place-items-center flex-shrink-0 ${sysStats?.gpu_available ? "bg-green-50" : "bg-[var(--gs-surface-2)]"}`}>
            <BarChart3 className={`h-5 w-5 ${sysStats?.gpu_available ? "text-green-600" : "text-[var(--gs-muted)]"}`}/>
          </div>
          <div className="flex-1">
            <div className="font-semibold text-sm">GPU</div>
            {sysStats?.gpu_available ? (
              <div className="text-xs text-emerald-600">{gpu?.name} · VRAM {gpu?.vram_total} (free: {gpu?.vram_free})</div>
            ) : (
              <div className="text-xs text-[var(--gs-muted)]">No GPU detected — Avatar HD models need CUDA. Go to Avatar Studio → Setup Guide.</div>
            )}
          </div>
          {sysStats?.gpu_available
            ? <Badge className="bg-emerald-100 text-emerald-700">GPU Ready</Badge>
            : <Badge className="bg-amber-100 text-amber-700">CPU only</Badge>
          }
        </Card>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {/* Docker Containers */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Container className="h-4 w-4 text-[var(--gs-teal)]"/>Docker Containers
            <Badge className="bg-emerald-100 text-emerald-700 text-[10px] ml-auto">
              {containers.filter(c=>c.ok).length}/{containers.length} UP
            </Badge>
          </h3>
          <div className="space-y-3">
            {containers.map(c => (
              <div key={c.name} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--gs-surface-2)]">
                <div className={`h-9 w-9 rounded-xl ${c.bg} grid place-items-center flex-shrink-0`}>
                  <c.icon className={`h-4 w-4 ${c.color}`}/>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold font-mono">{c.name}</div>
                  <div className="text-[10px] text-[var(--gs-muted)]">{c.role} · :{c.port}</div>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <StatusDot ok={c.ok} pulse={c.ok}/>
                  <span className={c.ok ? "text-emerald-600" : "text-rose-600"}>
                    {c.ok ? "Running" : "Down"}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>
            VPS: <span className="font-mono">31.97.237.222</span> ·
            Deploy: <span className="font-mono">cd /opt/getszy && git pull && docker compose up -d --build</span>
          </div>
        </Card>

        {/* AI Stack */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-[var(--gs-teal)]"/>AI Stack
            <Badge className="bg-emerald-100 text-emerald-700 text-[10px] ml-auto">
              {aiStack.filter(a=>a.ok).length}/{aiStack.length} ready
            </Badge>
          </h3>
          <div className="space-y-2">
            {aiStack.map(a => (
              <div key={a.name} className="flex items-center justify-between py-2 border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
                <div>
                  <div className="text-sm font-medium">{a.name}</div>
                  <div className="text-[10px] text-[var(--gs-muted)]">{a.desc}</div>
                </div>
                <div className="flex items-center gap-1.5">
                  <StatusDot ok={loading ? null : a.ok}/>
                  {loading ? (
                    <span className="text-xs text-[var(--gs-muted)]">…</span>
                  ) : a.ok ? (
                    <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">✓ Ready</Badge>
                  ) : (
                    <Badge className="bg-amber-100 text-amber-700 text-[10px]">Key missing</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Quick Terminal Commands */}
      <Card className="p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <Terminal className="h-4 w-4 text-[var(--gs-teal)]"/>Quick VPS Commands
        </h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-2">
          {[
            { label: "Check containers",  cmd: "docker ps --format 'table {{.Names}}\\t{{.Status}}'" },
            { label: "View backend logs", cmd: "docker logs getszy-backend --tail 50" },
            { label: "Restart backend",   cmd: "docker compose restart getszy-backend" },
            { label: "Deploy latest",     cmd: "cd /opt/getszy && git pull && docker compose up -d --build" },
            { label: "DB shell",          cmd: "docker exec -it getszy-mongo mongosh getszy" },
            { label: "Caddy reload",      cmd: "docker exec getszy-caddy caddy reload" },
          ].map(c => (
            <button key={c.label} onClick={() => { navigator.clipboard.writeText(c.cmd); toast.success(`"${c.label}" copied!`); }}
              className="text-left p-3 rounded-xl bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface)] border transition-colors group" style={{ borderColor: "var(--gs-border)" }}>
              <div className="text-xs font-semibold mb-1">{c.label}</div>
              <div className="text-[10px] font-mono text-[var(--gs-muted)] truncate group-hover:text-[var(--gs-teal)] transition-colors">{c.cmd}</div>
            </button>
          ))}
        </div>
        <p className="text-[10px] text-[var(--gs-muted)] mt-2">Click any command to copy to clipboard</p>
      </Card>
    </div>
  );
}
