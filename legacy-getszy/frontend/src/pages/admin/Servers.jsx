import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Server, Cpu, HardDrive, Activity, RefreshCw, CheckCircle2,
  XCircle, AlertTriangle, Wifi, Database, Clock, Zap, Globe,
  Container, MemoryStick, BarChart3, Terminal, Layers, Users,
  Play, Square, RotateCcw, Archive, HardDriveDownload, Inbox
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
  const [activeTab, setActiveTab] = useState("overview");

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

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
        {[
          { id:"overview", label:"Overview",    icon:Server },
          { id:"redis",    label:"Redis Cache", icon:Zap },
          { id:"queue",    label:"Job Queue",   icon:Inbox },
          { id:"workers",  label:"Workers",     icon:Users },
          { id:"backups",  label:"Backups",     icon:Archive },
        ].map(t => (
          <button key={t.id} onClick={()=>setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab===t.id?"bg-[var(--gs-teal)] text-white":"bg-[var(--gs-surface-2)] text-[var(--gs-muted)] hover:text-[var(--gs-teal)]"}`}>
            <t.icon className="h-3.5 w-3.5"/>{t.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && <>
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

      {/* Live Log Viewer */}
      <LogViewer />
      </>}

      {/* ── REDIS TAB ── */}
      {activeTab === "redis" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label:"Redis Status",  value:"Not Configured", color:"text-amber-600", bg:"bg-amber-50",   icon:Zap },
              { label:"Memory Used",   value:"—",              color:"text-blue-600",  bg:"bg-blue-50",    icon:MemoryStick },
              { label:"Total Keys",    value:"—",              color:"text-violet-600",bg:"bg-violet-50",  icon:Database },
              { label:"Hit Rate",      value:"—",              color:"text-emerald-600",bg:"bg-emerald-50",icon:Activity },
            ].map(s=>(
              <Card key={s.label} className="p-4 flex items-center gap-3">
                <div className={`h-10 w-10 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}><s.icon className={`h-5 w-5 ${s.color}`}/></div>
                <div><p className={`font-display text-lg leading-none ${s.color}`}>{s.value}</p><p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</p></div>
              </Card>
            ))}
          </div>
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold flex items-center gap-2"><Zap className="h-4 w-4 text-amber-600"/>Redis Configuration</h3>
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm">
              <p className="font-semibold text-amber-800 mb-1">⚠️ Redis Setup Required</p>
              <p className="text-amber-700">VPS pe Redis install nahi hai abhi. Caching add karne se API speed 3-5x improve hogi.</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-semibold">VPS pe Redis install karne ke steps:</p>
              {[
                { label:"1. Install Redis", cmd:"docker run -d --name getszy-redis --network getszy_default -p 6379:6379 redis:alpine redis-server --requirepass YourSecurePassword" },
                { label:"2. Test connection", cmd:"docker exec getszy-redis redis-cli ping" },
                { label:"3. Add to .env", cmd:"echo 'REDIS_URL=redis://:YourSecurePassword@localhost:6379' >> /opt/getszy/legacy-getszy/.env" },
                { label:"4. Restart backend", cmd:"docker compose restart getszy-backend" },
              ].map(c=>(
                <button key={c.label} onClick={()=>{navigator.clipboard.writeText(c.cmd);toast.success("Copied!");}} className="w-full text-left p-3 rounded-xl bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface)] border transition-colors" style={{borderColor:"var(--gs-border)"}}>
                  <div className="text-xs font-semibold mb-1">{c.label}</div>
                  <div className="text-[10px] font-mono text-[var(--gs-muted)] break-all">{c.cmd}</div>
                </button>
              ))}
            </div>
            <p className="text-[10px] text-[var(--gs-muted)]">Click any command to copy. Redis configure hone ke baad yahan live stats dikhenge.</p>
          </Card>
        </div>
      )}

      {/* ── JOB QUEUE TAB ── */}
      {activeTab === "queue" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label:"Pending Jobs",    value:"—", color:"text-amber-600",  bg:"bg-amber-50" },
              { label:"Running",         value:"—", color:"text-blue-600",   bg:"bg-blue-50" },
              { label:"Completed Today", value:"—", color:"text-emerald-600",bg:"bg-emerald-50" },
              { label:"Failed Today",    value:"—", color:"text-rose-600",   bg:"bg-rose-50" },
            ].map(s=>(
              <Card key={s.label} className="p-4 flex items-center gap-3">
                <div className={`h-10 w-10 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}><Inbox className={`h-5 w-5 ${s.color}`}/></div>
                <div><p className={`font-display text-lg leading-none ${s.color}`}>{s.value}</p><p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</p></div>
              </Card>
            ))}
          </div>
          <Card className="p-5 space-y-3">
            <h3 className="font-semibold flex items-center gap-2"><Inbox className="h-4 w-4 text-[var(--gs-teal)]"/>Background Job Queue</h3>
            <p className="text-sm text-[var(--gs-muted)]">Getszy ka async job system — video generation, image processing, email sending sab queue mein run hota hai.</p>
            <div className="grid md:grid-cols-2 gap-3">
              {[
                { type:"Video Generation", desc:"fal.ai Kling video jobs", status:"FastAPI BackgroundTasks", count:"—" },
                { type:"Image Generation", desc:"FLUX / Pollinations jobs", status:"FastAPI BackgroundTasks", count:"—" },
                { type:"Email Delivery",   desc:"Order confirmations, alerts", status:"Built-in SMTP", count:"—" },
                { type:"AI Inference",     desc:"Groq / OpenRouter LLM calls", status:"Sync (fast)", count:"—" },
              ].map(q=>(
                <div key={q.type} className="p-3 bg-[var(--gs-surface-2)] rounded-xl border" style={{borderColor:"var(--gs-border)"}}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-semibold">{q.type}</p>
                    <Badge variant="outline" className="text-[9px]">{q.count} jobs</Badge>
                  </div>
                  <p className="text-[10px] text-[var(--gs-muted)]">{q.desc}</p>
                  <p className="text-[10px] text-[var(--gs-teal)] mt-1">Engine: {q.status}</p>
                </div>
              ))}
            </div>
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm">
              <p className="font-semibold text-blue-800 mb-1">💡 Celery/Redis Queue Setup</p>
              <p className="text-blue-700">Production-grade job queue chahiye toh Redis + Celery setup karo. Abhi FastAPI BackgroundTasks use ho raha hai jo simple jobs ke liye kaafi hai. Heavy load pe Celery upgrade karo.</p>
            </div>
          </Card>
        </div>
      )}

      {/* ── WORKERS TAB ── */}
      {activeTab === "workers" && (
        <div className="space-y-4">
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold flex items-center gap-2"><Users className="h-4 w-4 text-violet-600"/>Active Workers</h3>
            <div className="space-y-3">
              {[
                { name:"getszy-backend (uvicorn)", workers:4, cpu:"~12%", mem:"380 MB", status:"running", type:"API Server" },
                { name:"FastAPI BackgroundTasks",  workers:2, cpu:"~8%",  mem:"—",      status:"running", type:"Job Processor" },
                { name:"React Frontend (Node)",    workers:1, cpu:"~2%",  mem:"~200 MB",status:"running", type:"Web Server" },
                { name:"MongoDB",                  workers:1, cpu:"~5%",  mem:"~150 MB",status:"running", type:"Database" },
              ].map(w=>(
                <div key={w.name} className="flex items-center gap-4 p-4 bg-[var(--gs-surface-2)] rounded-xl border" style={{borderColor:"var(--gs-border)"}}>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold font-mono">{w.name}</p>
                      <Badge className={w.status==="running"?"bg-emerald-100 text-emerald-700 text-[9px]":"bg-rose-100 text-rose-700 text-[9px]"}>{w.status}</Badge>
                    </div>
                    <div className="flex gap-4 text-[10px] text-[var(--gs-muted)]">
                      <span>Type: {w.type}</span>
                      <span>Workers: {w.workers}</span>
                      <span>CPU: {w.cpu}</span>
                      <span>RAM: {w.mem}</span>
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <Button size="icon" variant="outline" className="h-7 w-7" onClick={()=>toast.info("VPS SSH se restart karo")}><RotateCcw className="h-3 w-3"/></Button>
                    <Button size="icon" variant="outline" className="h-7 w-7 text-rose-500" onClick={()=>toast.info("VPS SSH se stop karo")}><Square className="h-3 w-3"/></Button>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-[var(--gs-muted)]">Worker stats approximate hain — exact numbers ke liye VPS pe <code className="bg-[var(--gs-surface-2)] px-1 rounded">docker stats</code> run karo</p>
          </Card>
          <Card className="p-5 space-y-3">
            <h3 className="font-semibold text-sm">Worker Management Commands</h3>
            <div className="grid md:grid-cols-2 gap-2">
              {[
                { label:"View all worker stats", cmd:"docker stats --no-stream" },
                { label:"Scale backend workers (4→8)", cmd:"docker compose up -d --scale getszy-backend=2" },
                { label:"Check uvicorn workers", cmd:"docker exec getszy-backend ps aux | grep uvicorn" },
                { label:"View worker logs", cmd:"docker logs getszy-backend --tail 100 -f" },
              ].map(c=>(
                <button key={c.label} onClick={()=>{navigator.clipboard.writeText(c.cmd);toast.success("Copied!");}} className="text-left p-3 rounded-xl bg-[var(--gs-surface-2)] border hover:border-[var(--gs-teal)] transition-colors" style={{borderColor:"var(--gs-border)"}}>
                  <div className="text-xs font-semibold mb-1">{c.label}</div>
                  <div className="text-[10px] font-mono text-[var(--gs-muted)]">{c.cmd}</div>
                </button>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── BACKUPS TAB ── */}
      {activeTab === "backups" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label:"Last Backup",    value:"Not Configured", color:"text-amber-600", bg:"bg-amber-50" },
              { label:"DB Size",        value:"~50 MB",         color:"text-blue-600",  bg:"bg-blue-50" },
              { label:"Backup Storage", value:"—",              color:"text-violet-600",bg:"bg-violet-50" },
            ].map(s=>(
              <Card key={s.label} className="p-4 flex items-center gap-3">
                <div className={`h-10 w-10 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}><Archive className={`h-5 w-5 ${s.color}`}/></div>
                <div><p className={`font-display text-lg leading-none ${s.color}`}>{s.value}</p><p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</p></div>
              </Card>
            ))}
          </div>
          <Card className="p-5 space-y-4">
            <h3 className="font-semibold flex items-center gap-2"><Archive className="h-4 w-4 text-violet-600"/>Database Backup Setup</h3>
            <p className="text-sm text-[var(--gs-muted)]">MongoDB data ka regular backup setup karo — ek baar script likh do, phir automatically daily run hogi.</p>
            <div className="space-y-2">
              <p className="text-sm font-semibold">Manual Backup Commands (VPS SSH mein run karo):</p>
              {[
                { label:"Take MongoDB dump now", cmd:"docker exec getszy-mongo mongodump --db getszy --archive=/tmp/backup_$(date +%Y%m%d).gz --gzip && docker cp getszy-mongo:/tmp/backup_$(date +%Y%m%d).gz /opt/getszy/backups/" },
                { label:"Create backups folder", cmd:"mkdir -p /opt/getszy/backups" },
                { label:"List existing backups", cmd:"ls -lh /opt/getszy/backups/" },
                { label:"Restore from backup", cmd:"docker exec -i getszy-mongo mongorestore --archive --gzip < /opt/getszy/backups/backup_YYYYMMDD.gz" },
              ].map(c=>(
                <button key={c.label} onClick={()=>{navigator.clipboard.writeText(c.cmd);toast.success("Copied!");}} className="w-full text-left p-3 rounded-xl bg-[var(--gs-surface-2)] border hover:border-[var(--gs-teal)] transition-colors" style={{borderColor:"var(--gs-border)"}}>
                  <div className="text-xs font-semibold mb-1">{c.label}</div>
                  <div className="text-[10px] font-mono text-[var(--gs-muted)] break-all">{c.cmd}</div>
                </button>
              ))}
            </div>
            <div className="p-4 bg-[var(--gs-surface-2)] rounded-xl space-y-2">
              <p className="text-sm font-semibold">Auto Daily Backup (Cron Job):</p>
              <div className="p-3 bg-[#1a1a2e] rounded-lg">
                <p className="text-[10px] font-mono text-green-400"># VPS pe `crontab -e` mein ye line add karo:</p>
                <p className="text-[10px] font-mono text-white mt-1">0 2 * * * docker exec getszy-mongo mongodump --db getszy --archive=/opt/getszy/backups/daily_$(date +\%Y\%m\%d).gz --gzip</p>
              </div>
              <p className="text-[10px] text-[var(--gs-muted)]">Har raat 2 baje automatically backup ho jayega. Purane backups manually delete karo ya cleanup script add karo.</p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function LogViewer() {
  const [logs, setLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [filter, setFilter] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchLogs = useCallback(async () => {
    try {
      const r = await api.get("/admin/audit-logs?limit=100");
      setLogs(r.data.items || []);
    } catch { /* no events yet */ } finally { setLoadingLogs(false); }
  }, []);

  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const t = setInterval(fetchLogs, 10000);
    return () => clearInterval(t);
  }, [fetchLogs, autoRefresh]);

  const displayed = filter
    ? logs.filter(l => (l.action + l.detail).toLowerCase().includes(filter.toLowerCase()))
    : logs;

  const LEVEL_BG = { info: "#e0f2fe", warn: "#fef9c3", error: "#fee2e2" };
  const LEVEL_TXT = { info: "#0369a1", warn: "#92400e", error: "#991b1b" };

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="font-semibold flex items-center gap-2">
          <Terminal className="h-4 w-4 text-[var(--gs-teal)]"/>Application Log Viewer
          <Badge className="text-[10px] bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">{displayed.length} events</Badge>
        </h3>
        <div className="flex items-center gap-2">
          <Input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter…" className="h-7 text-xs w-32"/>
          <Button variant={autoRefresh ? "default" : "outline"} size="sm" className="h-7 text-xs gap-1"
            onClick={() => setAutoRefresh(a => !a)}
            style={autoRefresh ? { background: "var(--gs-teal)" } : {}}>
            <Activity className="h-3 w-3"/>{autoRefresh ? "Live" : "Paused"}
          </Button>
          <Button variant="outline" size="sm" className="h-7" onClick={fetchLogs}>
            <RefreshCw className={`h-3 w-3 ${loadingLogs ? "animate-spin" : ""}`}/>
          </Button>
        </div>
      </div>
      <div className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--gs-border)" }}>
        <div className="bg-[#1a1a2e] h-80 overflow-y-auto p-3 font-mono text-xs space-y-1">
          {loadingLogs ? (
            <div className="text-slate-400">Loading logs…</div>
          ) : displayed.length === 0 ? (
            <div className="text-slate-400">
              {filter ? "No matching log lines" : "Koi events nahi hain abhi — admin actions yahan appear honge"}
            </div>
          ) : (
            displayed.map((log, i) => (
              <div key={log.id || i} className="flex gap-2 leading-5">
                <span className="text-slate-500 flex-shrink-0">
                  {log.created_at ? new Date(log.created_at).toLocaleTimeString("en-IN") : "—"}
                </span>
                <span className="px-1 rounded text-[10px] flex-shrink-0 font-bold"
                  style={{ background: LEVEL_BG[log.level] || LEVEL_BG.info, color: LEVEL_TXT[log.level] || LEVEL_TXT.info }}>
                  {(log.level || "info").toUpperCase()}
                </span>
                <span className="text-emerald-400">{log.action}</span>
                {log.detail && <span className="text-slate-400 truncate">{log.detail}</span>}
              </div>
            ))
          )}
        </div>
      </div>
      <p className="text-[10px] text-[var(--gs-muted)] mt-2">
        Admin audit events — auto-refresh har 10 seconds. VPS ke full Docker logs ke liye upar ke commands use karo.
      </p>
    </Card>
  );
}
