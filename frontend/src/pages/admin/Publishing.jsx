import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Youtube, Instagram, Facebook, Linkedin, Twitter, Share2, Send, Loader2, Trash2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { toast } from "sonner";

const PLATFORM_META = {
  youtube:   { icon: Youtube,   color: "#ef4444", label: "YouTube" },
  instagram: { icon: Instagram, color: "#ec4899", label: "Instagram" },
  facebook:  { icon: Facebook,  color: "#3b82f6", label: "Facebook" },
  x:         { icon: Twitter,   color: "#0ea5e9", label: "X (Twitter)" },
  linkedin:  { icon: Linkedin,  color: "#0a66c2", label: "LinkedIn" },
};

function StatusBadge({ s }) {
  if (s === "live" || s === "live-stub") return <Badge className="bg-emerald-100 text-emerald-800 text-[10px]"><CheckCircle2 className="h-3 w-3 mr-1"/>{s}</Badge>;
  if (s === "dry-run") return <Badge className="bg-amber-100 text-amber-800 text-[10px]"><AlertCircle className="h-3 w-3 mr-1"/>dry-run</Badge>;
  if (s === "scheduled") return <Badge className="bg-blue-100 text-blue-800 text-[10px]"><Clock className="h-3 w-3 mr-1"/>scheduled</Badge>;
  return <Badge variant="outline" className="text-[10px]">{s}</Badge>;
}

export default function Publishing() {
  const [connections, setConnections] = useState({});
  const [queue, setQueue] = useState([]);
  const [videos, setVideos] = useState([]);

  const [topic, setTopic] = useState("");
  const [caption, setCaption] = useState("");
  const [picked, setPicked] = useState([]);
  const [videoJobId, setVideoJobId] = useState("");
  const [scheduleAt, setScheduleAt] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try { const r = await api.get("/publishing/connections"); setConnections(r.data.platforms || {}); } catch (e) {}
    try { const r = await api.get("/publishing/queue?limit=40"); setQueue(r.data.items || []); } catch (e) {}
    try { const r = await api.get("/video/jobs?limit=20"); setVideos((r.data.items || []).filter(j => j.status === "done")); } catch (e) {}
  };
  useEffect(() => { load(); }, []);

  const togglePlatform = (p) => setPicked(cur => cur.includes(p) ? cur.filter(x => x !== p) : [...cur, p]);

  const schedule = async () => {
    if (topic.trim().length < 4) return toast.error("Topic too short");
    if (!picked.length) return toast.error("Pick at least one platform");
    setBusy(true);
    toast.loading("Scheduling…", { id: "sched" });
    try {
      const r = await api.post("/publishing/schedule", {
        platforms: picked, topic, caption, video_job_id: videoJobId || undefined,
        scheduled_at: scheduleAt || undefined, auto_generate_meta: true,
      });
      toast.success(`${r.data.items.length} posts queued ✅`, { id: "sched" });
      setTopic(""); setCaption(""); setPicked([]); setVideoJobId(""); setScheduleAt("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed", { id: "sched" });
    } finally { setBusy(false); }
  };

  const runNow = async (id) => {
    toast.loading("Posting…", { id });
    try {
      const r = await api.post("/publishing/run-now", { queue_id: id });
      toast.success(`Status: ${r.data.status}`, { id });
      await load();
    } catch (e) { toast.error("Post failed", { id }); }
  };
  const cancel = async (id) => { try { await api.delete(`/publishing/queue/${id}`); toast.success("Removed"); load(); } catch (e) {} };

  return (
    <div className="space-y-6" data-testid="admin-publishing-page">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2"><Share2 className="h-7 w-7 text-[var(--gs-teal)]"/> Multi-Platform Publishing</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">Auto-generate platform-specific captions · Schedule across 5 platforms · Dry-run preview if not connected.</p>
      </div>

      {/* Connections */}
      <Card className="p-5">
        <h3 className="font-semibold mb-3">Connections</h3>
        <div className="grid sm:grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(connections).map(([p, info]) => {
            const meta = PLATFORM_META[p]; if (!meta) return null;
            const Icon = meta.icon;
            return (
              <div key={p} className="gs-card p-3 flex items-center gap-3" data-testid={`conn-${p}`}>
                <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: `${meta.color}22` }}>
                  <Icon className="h-5 w-5" style={{ color: meta.color }}/>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold">{meta.label}</div>
                  <div className="text-[10px] text-[var(--gs-muted)]">{info.connected ? "Connected" : "Dry-run mode"}</div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Schedule form */}
      <Card className="p-5 space-y-4" data-testid="schedule-form">
        <h3 className="font-semibold">Schedule a post</h3>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Topic *</label>
          <Input value={topic} onChange={(e) => setTopic(e.target.value)} data-testid="pub-topic"/>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Caption (auto-generated if blank)</label>
          <Textarea value={caption} onChange={(e) => setCaption(e.target.value)} data-testid="pub-caption"/>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Attach a finished video (optional)</label>
            <select className="w-full border rounded-md px-3 py-2 text-sm" value={videoJobId} onChange={(e) => setVideoJobId(e.target.value)} data-testid="pub-video-select">
              <option value="">— none —</option>
              {videos.map(v => <option key={v.id} value={v.id}>{v.topic.slice(0,60)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Schedule at (ISO, optional)</label>
            <Input type="datetime-local" value={scheduleAt} onChange={(e) => setScheduleAt(e.target.value)} data-testid="pub-schedule-at"/>
          </div>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)] mb-2 block">Platforms *</label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(PLATFORM_META).map(([p, meta]) => {
              const Icon = meta.icon; const on = picked.includes(p);
              return (
                <button key={p} onClick={() => togglePlatform(p)} data-testid={`pick-${p}`}
                  className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition ${on ? "text-white border-transparent" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}
                  style={on ? { background: meta.color } : {}}>
                  <Icon className="h-3.5 w-3.5"/>{meta.label}
                </button>
              );
            })}
          </div>
        </div>
        <Button onClick={schedule} disabled={busy} className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="pub-schedule-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Send className="h-4 w-4 mr-2"/>}
          {busy ? "Scheduling…" : `Schedule on ${picked.length || 0} platform(s)`}
        </Button>
      </Card>

      {/* Queue */}
      <div>
        <h3 className="font-display text-xl mb-3">Queue · {queue.length}</h3>
        {queue.length === 0 ? (
          <Card className="p-6 text-center text-sm text-[var(--gs-muted)]">Empty — schedule your first post above.</Card>
        ) : (
          <div className="space-y-2" data-testid="queue-list">
            {queue.map(item => {
              const meta = PLATFORM_META[item.platform]; const Icon = meta?.icon || Share2;
              return (
                <Card key={item.id} className="p-3 flex items-center gap-3" data-testid={`queue-${item.id}`}>
                  <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: `${meta?.color}22` }}>
                    <Icon className="h-4 w-4" style={{ color: meta?.color }}/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate">{item.title || item.topic}</div>
                    <div className="text-[10px] text-[var(--gs-muted)] truncate">{(item.caption || "").slice(0, 80)}</div>
                  </div>
                  <StatusBadge s={item.status}/>
                  {item.status !== "posted" && item.status !== "live" && item.status !== "live-stub" && (
                    <Button size="sm" variant="outline" onClick={() => runNow(item.id)} data-testid={`runnow-${item.id}`}>Run now</Button>
                  )}
                  <button onClick={() => cancel(item.id)} className="text-rose-500" data-testid={`cancel-${item.id}`}><Trash2 className="h-4 w-4"/></button>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
