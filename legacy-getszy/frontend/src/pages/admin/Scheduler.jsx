import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  CalendarClock, Youtube, Instagram, Facebook, Twitter, Linkedin,
  RefreshCw, Trash2, Send, Clock, CheckCircle2, XCircle, AlertCircle,
  Loader2, Plus, Link2, ExternalLink, Play, Share2
} from "lucide-react";
import { toast } from "sonner";

const PLATFORMS = {
  youtube:   { icon: Youtube,   color: "text-red-500",   bg: "bg-red-50",   label: "YouTube" },
  instagram: { icon: Instagram, color: "text-pink-500",  bg: "bg-pink-50",  label: "Instagram" },
  facebook:  { icon: Facebook,  color: "text-blue-500",  bg: "bg-blue-50",  label: "Facebook" },
  twitter:   { icon: Twitter,   color: "text-sky-500",   bg: "bg-sky-50",   label: "X/Twitter" },
};

function StatusBadge({ s }) {
  if (s === "published")  return <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-2.5 w-2.5 mr-1"/>Published</Badge>;
  if (s === "scheduled")  return <Badge className="bg-blue-100 text-blue-700 text-[10px]"><Clock className="h-2.5 w-2.5 mr-1"/>Scheduled</Badge>;
  if (s === "publishing") return <Badge className="bg-amber-100 text-amber-700 text-[10px]"><Loader2 className="h-2.5 w-2.5 mr-1 animate-spin"/>Publishing…</Badge>;
  if (s === "failed")     return <Badge className="bg-rose-100 text-rose-700 text-[10px]"><XCircle className="h-2.5 w-2.5 mr-1"/>Failed</Badge>;
  if (s === "partial")    return <Badge className="bg-orange-100 text-orange-700 text-[10px]"><AlertCircle className="h-2.5 w-2.5 mr-1"/>Partial</Badge>;
  return <Badge variant="outline" className="text-[10px]">{s}</Badge>;
}

export default function AdminScheduler() {
  const [accounts,  setAccounts]  = useState([]);
  const [posts,     setPosts]     = useState([]);
  const [videos,    setVideos]    = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [showNew,   setShowNew]   = useState(false);
  const [showConnect, setShowConnect] = useState(false);
  const [connectPlatform, setConnectPlatform] = useState(null);
  const [connectToken, setConnectToken] = useState("");
  const [connectChannelId, setConnectChannelId] = useState("");
  const [connectBusy, setConnectBusy] = useState(false);

  // New post form
  const [videoJobId,   setVideoJobId]   = useState("");
  const [title,        setTitle]        = useState("");
  const [description,  setDescription]  = useState("");
  const [tags,         setTags]         = useState("");
  const [pickedPlatforms, setPickedPlatforms] = useState([]);
  const [scheduleAt,   setScheduleAt]   = useState("");
  const [submitBusy,   setSubmitBusy]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [accts, sched, vids] = await Promise.allSettled([
      api.get("/social/accounts"),
      api.get("/social/scheduled"),
      api.get("/video/jobs?limit=30"),
    ]);
    if (accts.status === "fulfilled")  setAccounts(accts.value.data.platforms || []);
    if (sched.status === "fulfilled")  setPosts(sched.value.data.items || []);
    if (vids.status  === "fulfilled")  setVideos((vids.value.data.items || []).filter(j => j.status === "done"));
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const connectedCount = accounts.filter(a => a.connected).length;

  const togglePlatform = (p) =>
    setPickedPlatforms(cur => cur.includes(p) ? cur.filter(x => x !== p) : [...cur, p]);

  const schedulePost = async () => {
    if (!videoJobId) return toast.error("Pehle ek ready video select karo");
    if (!title.trim()) return toast.error("Title daalo");
    if (!pickedPlatforms.length) return toast.error("Kam se kam ek platform chuno");
    setSubmitBusy(true);
    try {
      await api.post("/social/schedule", {
        video_job_id: videoJobId,
        title,
        description,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
        platforms: pickedPlatforms,
        scheduled_at: scheduleAt || null,
      });
      toast.success("Post scheduled!");
      setShowNew(false);
      setTitle(""); setDescription(""); setTags(""); setPickedPlatforms([]); setVideoJobId(""); setScheduleAt("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Schedule failed");
    } finally { setSubmitBusy(false); }
  };

  const publishNow = async (postId) => {
    try {
      await api.post(`/social/publish/${postId}`);
      toast.success("Publishing…"); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Publish failed"); }
  };

  const deletePost = async (postId) => {
    if (!window.confirm("Cancel this scheduled post?")) return;
    try {
      await api.delete(`/social/scheduled/${postId}`);
      toast.success("Removed"); await load();
    } catch (e) { toast.error("Delete failed"); }
  };

  const connectAccount = async () => {
    if (!connectToken.trim()) return toast.error("Access token daalo");
    setConnectBusy(true);
    try {
      await api.post("/social/accounts/connect", {
        platform: connectPlatform,
        access_token: connectToken,
        channel_id: connectChannelId || undefined,
      });
      toast.success(`${connectPlatform} connected!`);
      setShowConnect(false); setConnectToken(""); setConnectChannelId("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Connect failed");
    } finally { setConnectBusy(false); }
  };

  const disconnectAccount = async (platform) => {
    if (!window.confirm(`Disconnect ${platform}?`)) return;
    try {
      await api.delete(`/social/accounts/${platform}`);
      toast.success("Disconnected"); await load();
    } catch (e) { toast.error("Disconnect failed"); }
  };

  return (
    <div className="space-y-5" data-testid="admin-scheduler-page">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <CalendarClock className="h-7 w-7 text-[var(--gs-teal)]"/>Social Scheduler
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            {connectedCount}/4 platforms connected · {posts.filter(p => p.status === "scheduled").length} posts pending
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
          </Button>
          <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
            onClick={() => setShowNew(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5"/>Schedule Post
          </Button>
        </div>
      </div>

      {/* Platform Connection Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(PLATFORMS).map(([key, meta]) => {
          const acct = accounts.find(a => a.platform === key);
          const connected = acct?.connected;
          return (
            <Card key={key} className="p-4 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className={`h-9 w-9 rounded-xl ${meta.bg} grid place-items-center`}>
                  <meta.icon className={`h-4 w-4 ${meta.color}`}/>
                </div>
                {connected
                  ? <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">✓ Connected</Badge>
                  : <Badge variant="outline" className="text-[10px]">Not connected</Badge>}
              </div>
              <div className="font-semibold text-sm">{meta.label}</div>
              {connected && acct?.info?.channel_name && (
                <div className="text-[10px] text-[var(--gs-muted)] truncate">@{acct.info.channel_name}</div>
              )}
              {connected ? (
                <button onClick={() => disconnectAccount(key)}
                  className="text-[10px] text-rose-500 hover:text-rose-700 text-left mt-auto">Disconnect</button>
              ) : (
                <Button size="sm" variant="outline" className="text-xs h-7 mt-auto"
                  onClick={() => { setConnectPlatform(key); setShowConnect(true); }}>
                  <Link2 className="h-3 w-3 mr-1"/>Connect
                </Button>
              )}
            </Card>
          );
        })}
      </div>

      {/* Scheduled Posts Table */}
      <Card>
        <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold flex items-center gap-2">
            <Share2 className="h-4 w-4 text-[var(--gs-teal)]"/>Scheduled Posts ({posts.length})
          </h3>
        </div>
        {loading ? (
          <div className="p-6 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-[var(--gs-muted)]"/></div>
        ) : posts.length === 0 ? (
          <div className="p-10 text-center">
            <CalendarClock className="h-10 w-10 mx-auto mb-2 text-[var(--gs-muted)] opacity-40"/>
            <p className="text-sm text-[var(--gs-muted)] mb-3">Koi scheduled posts nahi hain</p>
            <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
              onClick={() => setShowNew(true)}>
              <Plus className="h-3.5 w-3.5 mr-1.5"/>Pehla post schedule karo
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="text-xs uppercase tracking-wider text-[var(--gs-muted)] text-left border-b"
                style={{ borderColor: "var(--gs-border)" }}>
                <tr>
                  <th className="p-3">Title</th>
                  <th className="p-3">Platforms</th>
                  <th className="p-3">Scheduled At</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 w-24"/>
                </tr>
              </thead>
              <tbody>
                {posts.map(p => (
                  <tr key={p.id} className="border-b last:border-0 hover:bg-[var(--gs-surface-2)] transition-colors"
                    style={{ borderColor: "var(--gs-border)" }}>
                    <td className="p-3 max-w-[200px]">
                      <div className="font-medium truncate">{p.title || p.topic || "Untitled"}</div>
                      <div className="text-[10px] text-[var(--gs-muted)] truncate">{p.video_url ? "Video attached" : "No video"}</div>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1 flex-wrap">
                        {(p.platforms || []).map(plat => {
                          const m = PLATFORMS[plat];
                          if (!m) return <Badge key={plat} variant="outline" className="text-[10px]">{plat}</Badge>;
                          return (
                            <span key={plat} className={`inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full ${m.bg} ${m.color}`}>
                              <m.icon className="h-2.5 w-2.5"/>{m.label}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td className="p-3 text-xs text-[var(--gs-muted)]">
                      {p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("en-IN", {
                        day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
                      }) : "Immediate"}
                    </td>
                    <td className="p-3"><StatusBadge s={p.status}/></td>
                    <td className="p-3">
                      <div className="flex items-center gap-1">
                        {p.status === "scheduled" && (
                          <Button size="sm" variant="outline" className="h-7 px-2 text-xs"
                            onClick={() => publishNow(p.id)}>
                            <Play className="h-3 w-3 mr-0.5"/>Now
                          </Button>
                        )}
                        {p.results && Object.keys(p.results).length > 0 && (
                          <button onClick={() => toast(JSON.stringify(p.results, null, 2).slice(0, 300))}
                            className="text-[var(--gs-muted)] hover:text-[var(--gs-teal)]">
                            <ExternalLink className="h-3.5 w-3.5"/>
                          </button>
                        )}
                        <button onClick={() => deletePost(p.id)} className="text-rose-400 hover:text-rose-600">
                          <Trash2 className="h-3.5 w-3.5"/>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ── Schedule New Post Dialog ── */}
      <Dialog open={showNew} onOpenChange={o => !o && setShowNew(false)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarClock className="h-5 w-5 text-[var(--gs-teal)]"/>Schedule New Post
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            {/* Video picker */}
            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Video (sirf Done status waale)</label>
              {videos.length === 0 ? (
                <div className="text-xs text-amber-600 p-2 bg-amber-50 rounded-lg">
                  Koi ready video nahi hai — pehle Video Studio mein banao
                </div>
              ) : (
                <select className="w-full border rounded-xl px-3 py-2 text-sm bg-white"
                  style={{ borderColor: "var(--gs-border)" }}
                  value={videoJobId} onChange={e => {
                    setVideoJobId(e.target.value);
                    const v = videos.find(x => x.id === e.target.value);
                    if (v && !title) setTitle(v.topic || "");
                  }}>
                  <option value="">-- Video chuno --</option>
                  {videos.map(v => (
                    <option key={v.id} value={v.id}>{v.topic || v.id?.slice(0,12)}</option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Title *</label>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Post ka title"/>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Description</label>
              <Textarea value={description} onChange={e => setDescription(e.target.value)}
                placeholder="Post description…" rows={3} className="resize-none text-sm"/>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Tags (comma separated)</label>
              <Input value={tags} onChange={e => setTags(e.target.value)} placeholder="india, viral, shorts"/>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Platforms *</label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(PLATFORMS).map(([key, meta]) => {
                  const active = pickedPlatforms.includes(key);
                  return (
                    <button key={key} onClick={() => togglePlatform(key)}
                      className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
                        active ? `${meta.bg} ${meta.color} border-current font-semibold` : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"
                      }`}>
                      <meta.icon className="h-3 w-3"/>{meta.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] block mb-1">Schedule at (khali = abhi publish)</label>
              <Input type="datetime-local" value={scheduleAt} onChange={e => setScheduleAt(e.target.value)}/>
            </div>

            <Button onClick={schedulePost} disabled={submitBusy || !videoJobId || !title || !pickedPlatforms.length}
              className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {submitBusy ? <Loader2 className="h-4 w-4 mr-2 animate-spin"/> : <Send className="h-4 w-4 mr-2"/>}
              {scheduleAt ? "Schedule" : "Publish Now"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── Connect Platform Dialog ── */}
      <Dialog open={showConnect} onOpenChange={o => { if (!o) { setShowConnect(false); setConnectToken(""); setConnectChannelId(""); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 capitalize">
              {connectPlatform && (() => { const m = PLATFORMS[connectPlatform]; return m ? <m.icon className={`h-5 w-5 ${m.color}`}/> : null; })()}
              Connect {connectPlatform}
            </DialogTitle>
          </DialogHeader>
          {connectPlatform && (
            <div className="space-y-3 text-sm">
              <div className="text-xs text-[var(--gs-muted)] p-3 rounded-xl bg-[var(--gs-surface-2)]">
                {accounts.find(a => a.platform === connectPlatform)?.instructions || "Access token paste karo"}
                {accounts.find(a => a.platform === connectPlatform)?.setup_url && (
                  <a href={accounts.find(a => a.platform === connectPlatform)?.setup_url} target="_blank" rel="noreferrer"
                    className="flex items-center gap-1 text-[var(--gs-teal)] mt-1 hover:underline text-[10px]">
                    <ExternalLink className="h-2.5 w-2.5"/>Developer Console
                  </a>
                )}
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)] block mb-1">Access Token *</label>
                <Input value={connectToken} onChange={e => setConnectToken(e.target.value)}
                  placeholder="Paste your access token here" type="password"/>
              </div>
              {(connectPlatform === "youtube" || connectPlatform === "instagram") && (
                <div>
                  <label className="text-xs text-[var(--gs-muted)] block mb-1">Channel / User ID</label>
                  <Input value={connectChannelId} onChange={e => setConnectChannelId(e.target.value)}
                    placeholder="Channel ID ya User ID"/>
                </div>
              )}
              <Button onClick={connectAccount} disabled={connectBusy || !connectToken.trim()}
                className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
                {connectBusy ? <Loader2 className="h-4 w-4 mr-2 animate-spin"/> : <Link2 className="h-4 w-4 mr-2"/>}
                Connect Account
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
