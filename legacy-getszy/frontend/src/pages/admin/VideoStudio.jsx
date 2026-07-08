import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Film, Play, Loader2, Download, Trash2, RefreshCw, Layers, Sparkles,
  FileText, BookOpen, Calendar, Share2, CheckCircle, XCircle, Clock,
  Youtube, Instagram, Facebook, Twitter, Send, Link, Unlink, AlertCircle
} from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const ORIENTATIONS = [
  { id: "9:16", label: "9:16 Shorts / Reels" },
  { id: "16:9", label: "16:9 YT Long-form" },
  { id: "1:1",  label: "1:1 Insta Square" },
];

const PLATFORM_META = {
  youtube:   { label: "YouTube",   icon: Youtube,   color: "text-red-600",   bg: "bg-red-50 border-red-200" },
  instagram: { label: "Instagram", icon: Instagram,  color: "text-pink-600",  bg: "bg-pink-50 border-pink-200" },
  facebook:  { label: "Facebook",  icon: Facebook,   color: "text-blue-600",  bg: "bg-blue-50 border-blue-200" },
  twitter:   { label: "Twitter/X", icon: Twitter,    color: "text-sky-600",   bg: "bg-sky-50 border-sky-200" },
};

const STATUS_LABEL = {
  queued: "Queued", writing_script: "Writing script", planning_shots: "Planning shots",
  generating_visuals: "Generating visuals", synthesizing_voice: "Synthesizing voice",
  composing_video: "Composing video", done: "Done", failed: "Failed",
};

function StatusPill({ s }) {
  const cls = s === "done" ? "bg-emerald-100 text-emerald-800" :
              s === "failed" ? "bg-rose-100 text-rose-800" :
              "bg-amber-100 text-amber-800";
  return <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${cls}`}>{STATUS_LABEL[s] || s}</span>;
}

function JobCard({ j, onView, onDelete }) {
  return (
    <Card className="p-4" data-testid={`video-job-${j.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-semibold text-sm truncate">{j.topic}</div>
          <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{j.orientation} · {j.language}</div>
        </div>
        <StatusPill s={j.status}/>
      </div>
      {j.percent !== undefined && j.status !== "done" && j.status !== "failed" && (
        <div className="mt-2 h-1.5 rounded-full bg-[var(--gs-surface-2)] overflow-hidden">
          <div className="h-full bg-[var(--gs-teal)] transition-all" style={{ width: `${j.percent}%` }}/>
        </div>
      )}
      {j.status === "done" && j.video_url && (
        <video className="w-full mt-2 rounded-xl bg-black max-h-48 object-contain"
               src={`${BACKEND_URL}${j.video_url}`} controls preload="metadata"/>
      )}
      {j.status === "failed" && <div className="text-[11px] text-rose-600 mt-2">{j.error}</div>}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        <Button size="sm" variant="outline" onClick={() => onView(j.id)} data-testid={`view-job-${j.id}`}>View</Button>
        {j.status === "done" && (
          <>
            <a href={`${BACKEND_URL}${j.video_url}`} download className="text-xs underline" data-testid={`download-${j.id}`}>
              <Download className="h-3.5 w-3.5 inline"/> MP4
            </a>
            <a href={`${BACKEND_URL}${j.srt_url}`} download className="text-xs underline">
              <FileText className="h-3.5 w-3.5 inline"/> SRT
            </a>
          </>
        )}
        <button onClick={() => onDelete(j.id)} className="ml-auto text-rose-500" data-testid={`delete-${j.id}`}>
          <Trash2 className="h-3.5 w-3.5"/>
        </button>
      </div>
    </Card>
  );
}

export default function VideoStudio() {
  const [voices, setVoices]     = useState({ voices: [], providers: {} });
  const [jobs, setJobs]         = useState([]);
  const [active, setActive]     = useState(null);
  const [platforms, setPlatforms] = useState([]);
  const [scheduled, setScheduled] = useState([]);

  // Single video
  const [topic, setTopic]       = useState("");
  const [orientation, setOrientation] = useState("9:16");
  const [language, setLanguage] = useState("hinglish");
  const [voiceGender, setVoiceGender] = useState("female");
  const [subtitles, setSubtitles] = useState(true);
  const [seconds, setSeconds]   = useState(45);
  const [tone, setTone]         = useState("energetic");
  const [busy, setBusy]         = useState(false);

  // Batch
  const [batchTopics, setBatchTopics] = useState("");
  const [batchBusy, setBatchBusy]     = useState(false);

  // AI Story
  const [storyTheme, setStoryTheme]   = useState("");
  const [storyGenre, setStoryGenre]   = useState("motivational");
  const [storyLang, setStoryLang]     = useState("hinglish");
  const [storyBusy, setStoryBusy]     = useState(false);

  // Schedule
  const [schedJobId, setSchedJobId]   = useState("");
  const [schedTitle, setSchedTitle]   = useState("");
  const [schedDesc, setSchedDesc]     = useState("");
  const [schedPlatforms, setSchedPlatforms] = useState([]);
  const [schedAt, setSchedAt]         = useState("");
  const [schedBusy, setSchedBusy]     = useState(false);

  // Social connect
  const [connectPlatform, setConnectPlatform] = useState("");
  const [connectToken, setConnectToken]       = useState("");
  const [connectChannelId, setConnectChannelId] = useState("");
  const [connectChannelName, setConnectChannelName] = useState("");
  const [connectBusy, setConnectBusy] = useState(false);

  const load = useCallback(async () => {
    try { const r = await api.get("/video/voices"); setVoices(r.data); } catch (_) {}
    try { const r = await api.get("/video/jobs?limit=30"); setJobs(r.data.items || []); } catch (_) {}
    try { const r = await api.get("/social/accounts"); setPlatforms(r.data.platforms || []); } catch (_) {}
    try { const r = await api.get("/social/scheduled"); setScheduled(r.data.items || []); } catch (_) {}
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 6000); return () => clearInterval(t); }, [load]);

  // ── Generators ──────────────────────────────────────────────────

  const generate = async () => {
    if (topic.trim().length < 4) return toast.error("Topic too short");
    setBusy(true);
    toast.loading("Queuing video job…", { id: "vid" });
    try {
      const r = await api.post("/video/generate", {
        topic, orientation, language, voice_gender: voiceGender,
        target_seconds: Number(seconds), tone, subtitles,
      });
      toast.success(`Job queued ✅ (${r.data.id.slice(0, 8)})`, { id: "vid" });
      setTopic("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed", { id: "vid" });
    } finally { setBusy(false); }
  };

  const runBatch = async () => {
    const topics = batchTopics.split("\n").map(t => t.trim()).filter(Boolean);
    if (!topics.length) return toast.error("Add at least one topic");
    if (topics.length > 10) return toast.error("Max 10 topics");
    setBatchBusy(true);
    toast.loading(`Queuing ${topics.length} videos…`, { id: "batch" });
    try {
      const r = await api.post("/video/batch", {
        topics, orientation, language, voice_gender: voiceGender, target_seconds: Number(seconds)
      });
      toast.success(`${r.data.count} jobs queued ✅`, { id: "batch" });
      setBatchTopics("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed", { id: "batch" });
    } finally { setBatchBusy(false); }
  };

  const generateStory = async () => {
    if (storyTheme.trim().length < 4) return toast.error("Story theme too short");
    setStoryBusy(true);
    toast.loading("Creating AI story video…", { id: "story" });
    try {
      const r = await api.post("/video/generate", {
        topic: storyTheme,
        orientation: "9:16",
        language: storyLang,
        voice_gender: voiceGender,
        target_seconds: 75,
        tone: storyGenre === "horror" ? "dramatic" : storyGenre === "comedy" ? "witty" : "inspirational",
        subtitles: true,
        format: "ai_story",
      });
      toast.success(`Story video queued ✅ (${r.data.id.slice(0, 8)})`, { id: "story" });
      setStoryTheme("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed", { id: "story" });
    } finally { setStoryBusy(false); }
  };

  // ── Schedule ────────────────────────────────────────────────────

  const schedulePost = async () => {
    if (!schedJobId) return toast.error("Select a completed video first");
    if (!schedTitle.trim()) return toast.error("Add a title");
    if (!schedPlatforms.length) return toast.error("Select at least one platform");
    setSchedBusy(true);
    try {
      await api.post("/social/schedule", {
        video_job_id: schedJobId,
        platforms: schedPlatforms,
        title: schedTitle,
        description: schedDesc,
        tags: schedTitle.split(" ").filter(w => w.length > 3).slice(0, 5).map(w => `#${w}`),
        scheduled_at: schedAt || null,
      });
      toast.success("Post scheduled ✅");
      setSchedJobId(""); setSchedTitle(""); setSchedDesc(""); setSchedPlatforms([]); setSchedAt("");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Schedule failed");
    } finally { setSchedBusy(false); }
  };

  const publishNow = async (postId) => {
    try {
      await api.post(`/social/publish/${postId}`);
      toast.success("Publishing started!");
      await load();
    } catch (e) {
      toast.error("Publish failed");
    }
  };

  const deleteScheduled = async (postId) => {
    try {
      await api.delete(`/social/scheduled/${postId}`);
      toast.success("Removed");
      await load();
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  // ── Social connect ───────────────────────────────────────────────

  const connectAccount = async () => {
    if (!connectPlatform || !connectToken.trim()) return toast.error("Platform and access token required");
    setConnectBusy(true);
    try {
      await api.post("/social/accounts/connect", {
        platform: connectPlatform,
        access_token: connectToken,
        channel_id: connectChannelId || undefined,
        channel_name: connectChannelName || undefined,
      });
      toast.success(`${connectPlatform} connected ✅`);
      setConnectToken(""); setConnectChannelId(""); setConnectChannelName("");
      await load();
    } catch (e) {
      toast.error("Connect failed");
    } finally { setConnectBusy(false); }
  };

  const disconnectAccount = async (platform) => {
    try {
      await api.delete(`/social/accounts/${platform}`);
      toast.success(`${platform} disconnected`);
      await load();
    } catch (e) {
      toast.error("Disconnect failed");
    }
  };

  const openJob = async (id) => {
    try { const r = await api.get(`/video/jobs/${id}`); setActive(r.data); } catch (_) { toast.error("Failed to load"); }
  };
  const delJob = async (id) => {
    try { await api.delete(`/video/jobs/${id}`); toast.success("Deleted"); load(); } catch (_) { toast.error("Delete failed"); }
  };

  const toggleSchedPlatform = (p) =>
    setSchedPlatforms(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);

  const doneJobs = jobs.filter(j => j.status === "done");

  // ── Render ───────────────────────────────────────────────────────

  return (
    <div className="space-y-6" data-testid="admin-video-studio-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Film className="h-7 w-7 text-[var(--gs-teal)]"/> Video Studio
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            Faceless videos · AI Stories · Schedule · Auto-post to all platforms
          </p>
        </div>
        {voices.providers && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(voices.providers).map(([k, v]) => (
              <Badge key={k} variant="outline" className="text-[10px]">{k}: <span className="ml-1 font-semibold">{v}</span></Badge>
            ))}
          </div>
        )}
      </div>

      <Tabs defaultValue="single">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="single"><Film className="h-4 w-4 mr-1"/>Single Video</TabsTrigger>
          <TabsTrigger value="batch"><Layers className="h-4 w-4 mr-1"/>Batch</TabsTrigger>
          <TabsTrigger value="story"><BookOpen className="h-4 w-4 mr-1"/>AI Stories</TabsTrigger>
          <TabsTrigger value="schedule"><Calendar className="h-4 w-4 mr-1"/>Schedule</TabsTrigger>
          <TabsTrigger value="social"><Share2 className="h-4 w-4 mr-1"/>Social Media</TabsTrigger>
        </TabsList>

        {/* ── Single Video ──────────────────────────────────────── */}
        <TabsContent value="single" className="mt-4">
          <Card className="p-5 space-y-4">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Topic *</label>
              <Input value={topic} onChange={e => setTopic(e.target.value)}
                     placeholder="e.g. Top 5 AI side hustles for Indian students"
                     data-testid="video-topic-input"/>
            </div>
            <div className="grid md:grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Orientation</label>
                <Select value={orientation} onValueChange={setOrientation}>
                  <SelectTrigger data-testid="video-orientation"><SelectValue/></SelectTrigger>
                  <SelectContent>{ORIENTATIONS.map(o => <SelectItem key={o.id} value={o.id}>{o.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Language</label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger data-testid="video-language"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hinglish">Hinglish</SelectItem>
                    <SelectItem value="hindi">Hindi</SelectItem>
                    <SelectItem value="english">Indian English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Voice gender</label>
                <Select value={voiceGender} onValueChange={setVoiceGender}>
                  <SelectTrigger data-testid="video-voice-gender"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="female">Female</SelectItem>
                    <SelectItem value="male">Male</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Length (sec)</label>
                <Input type="number" value={seconds} onChange={e => setSeconds(e.target.value)} data-testid="video-seconds"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Tone</label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger data-testid="video-tone"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    {["energetic","calm","witty","authoritative","inspirational","story-driven"].map(t => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end gap-3">
                <Switch checked={subtitles} onCheckedChange={setSubtitles} data-testid="video-subtitles"/>
                <span className="text-xs">Burn-in subtitles</span>
              </div>
            </div>
            <Button onClick={generate} disabled={busy} className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="video-generate-btn">
              {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Play className="h-4 w-4 mr-2"/>}
              {busy ? "Queuing…" : "Generate Faceless Video (1080p HD)"}
            </Button>
            <p className="text-[11px] text-[var(--gs-muted)]">
              1080p HD · 5 scenes minimum · 60–120s render time · Captions included
            </p>
          </Card>
        </TabsContent>

        {/* ── Batch ─────────────────────────────────────────────── */}
        <TabsContent value="batch" className="mt-4">
          <Card className="p-5 space-y-4">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Topics (one per line, max 10)</label>
              <Textarea rows={6} value={batchTopics} onChange={e => setBatchTopics(e.target.value)}
                        placeholder="5 AI tools for Indian students&#10;How to start a YouTube channel in 2026&#10;…"
                        data-testid="batch-topics-input"/>
            </div>
            <Button onClick={runBatch} disabled={batchBusy} className="w-full bg-[#7c3aed] hover:bg-[#7c3aed]/90" data-testid="batch-run-btn">
              {batchBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Layers className="h-4 w-4 mr-2"/>}
              {batchBusy ? "Queuing batch…" : "Queue Batch (up to 10 videos)"}
            </Button>
          </Card>
        </TabsContent>

        {/* ── AI Stories ────────────────────────────────────────── */}
        <TabsContent value="story" className="mt-4">
          <Card className="p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <BookOpen className="h-5 w-5 text-[var(--gs-teal)]"/>
              <h3 className="font-display text-lg">AI Short Story Video</h3>
            </div>
            <p className="text-xs text-[var(--gs-muted)]">
              AI likhega ek complete story — opening, conflict, climax, moral — aur cinematic video banayega. Best for Reels.
            </p>
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Story theme / idea *</label>
              <Input value={storyTheme} onChange={e => setStoryTheme(e.target.value)}
                     placeholder="e.g. Ek garib ladka jisne coding seekh ke apni life badal li"/>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Genre</label>
                <Select value={storyGenre} onValueChange={setStoryGenre}>
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="motivational">Motivational</SelectItem>
                    <SelectItem value="drama">Drama</SelectItem>
                    <SelectItem value="comedy">Comedy</SelectItem>
                    <SelectItem value="horror">Horror</SelectItem>
                    <SelectItem value="love">Love Story</SelectItem>
                    <SelectItem value="thriller">Thriller</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Language</label>
                <Select value={storyLang} onValueChange={setStoryLang}>
                  <SelectTrigger><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hinglish">Hinglish</SelectItem>
                    <SelectItem value="hindi">Hindi</SelectItem>
                    <SelectItem value="english">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={generateStory} disabled={storyBusy}
                    className="w-full bg-gradient-to-r from-[var(--gs-teal)] to-[#7c3aed] hover:opacity-90">
              {storyBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
              {storyBusy ? "Creating story…" : "Generate AI Story Video"}
            </Button>
            <p className="text-[11px] text-[var(--gs-muted)]">
              AI likhega: Opening → Rising action → Climax → Resolution → Moral. 5-scene 9:16 Reel, ~75s.
            </p>
          </Card>
        </TabsContent>

        {/* ── Schedule ──────────────────────────────────────────── */}
        <TabsContent value="schedule" className="mt-4 space-y-5">
          <Card className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-[var(--gs-teal)]"/>
              <h3 className="font-display text-lg">Schedule a Post</h3>
            </div>
            <p className="text-xs text-[var(--gs-muted)]">Kisi completed video ko select karo aur platform + time set karo.</p>

            <div>
              <label className="text-xs text-[var(--gs-muted)]">Select completed video *</label>
              <Select value={schedJobId} onValueChange={id => {
                setSchedJobId(id);
                const j = doneJobs.find(j => j.id === id);
                if (j) setSchedTitle(j.topic);
              }}>
                <SelectTrigger>
                  <SelectValue placeholder={doneJobs.length ? "Choose a video…" : "No completed videos yet"}/>
                </SelectTrigger>
                <SelectContent>
                  {doneJobs.map(j => (
                    <SelectItem key={j.id} value={j.id}>{j.topic.slice(0, 50)} ({j.orientation})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)]">Post title</label>
              <Input value={schedTitle} onChange={e => setSchedTitle(e.target.value)} placeholder="Video ka title"/>
            </div>
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Description (optional)</label>
              <Textarea rows={2} value={schedDesc} onChange={e => setSchedDesc(e.target.value)} placeholder="Caption ya description…"/>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)] mb-2 block">Platforms *</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(PLATFORM_META).map(([key, meta]) => {
                  const Icon = meta.icon;
                  const sel = schedPlatforms.includes(key);
                  const acct = platforms.find(p => p.platform === key);
                  return (
                    <button key={key} onClick={() => toggleSchedPlatform(key)}
                            className={`flex items-center gap-2 p-2.5 rounded-lg border text-sm transition-all
                              ${sel ? "border-[var(--gs-teal)] bg-[var(--gs-teal)]/10" : "border-gray-200 hover:border-gray-300"}`}>
                      <Icon className={`h-4 w-4 ${meta.color}`}/>
                      <span className="font-medium">{meta.label}</span>
                      {acct?.connected ? (
                        <CheckCircle className="h-3 w-3 text-emerald-500 ml-auto"/>
                      ) : (
                        <AlertCircle className="h-3 w-3 text-amber-400 ml-auto" title="Not connected"/>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="text-xs text-[var(--gs-muted)]">Schedule date & time (optional — blank = publish now)</label>
              <Input type="datetime-local" value={schedAt} onChange={e => setSchedAt(e.target.value)}/>
            </div>

            <Button onClick={schedulePost} disabled={schedBusy} className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {schedBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Calendar className="h-4 w-4 mr-2"/>}
              {schedBusy ? "Scheduling…" : schedAt ? "Schedule Post" : "Publish Now to Selected Platforms"}
            </Button>
          </Card>

          {/* Scheduled posts list */}
          <div>
            <h4 className="font-display text-base mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4"/> Scheduled Posts ({scheduled.length})
            </h4>
            {scheduled.length === 0 ? (
              <Card className="p-4 text-center text-sm text-[var(--gs-muted)]">Koi scheduled post nahi hai abhi.</Card>
            ) : (
              <div className="space-y-2">
                {scheduled.map(p => (
                  <Card key={p.id} className="p-3 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-sm truncate">{p.title}</div>
                      <div className="text-[10px] text-[var(--gs-muted)]">
                        {p.platforms?.join(", ")} · {p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("en-IN") : "Now"}
                      </div>
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {(p.results ? Object.entries(p.results) : []).map(([plat, res]) => (
                          <span key={plat} className={`text-[9px] px-1.5 py-0.5 rounded ${res.ok ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                            {plat}: {res.ok ? "✓" : res.error?.slice(0, 30)}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge variant="outline" className="text-[9px]">{p.status}</Badge>
                      {p.status === "scheduled" && (
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => publishNow(p.id)}>
                          <Send className="h-3 w-3 mr-1"/> Publish
                        </Button>
                      )}
                      <button onClick={() => deleteScheduled(p.id)} className="text-rose-400"><Trash2 className="h-3.5 w-3.5"/></button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* ── Social Media ──────────────────────────────────────── */}
        <TabsContent value="social" className="mt-4 space-y-5">
          {/* Platform status */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
            {(platforms.length ? platforms : Object.keys(PLATFORM_META).map(p => ({ platform: p, connected: false }))).map(acct => {
              const meta = PLATFORM_META[acct.platform] || {};
              const Icon = meta.icon || Share2;
              return (
                <Card key={acct.platform} className={`p-4 border ${acct.connected ? "border-emerald-200 bg-emerald-50" : "border-gray-200"}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className={`h-5 w-5 ${meta.color}`}/>
                    <span className="font-semibold text-sm capitalize">{meta.label || acct.platform}</span>
                    {acct.connected ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500 ml-auto"/>
                    ) : (
                      <XCircle className="h-4 w-4 text-gray-300 ml-auto"/>
                    )}
                  </div>
                  {acct.connected ? (
                    <>
                      <div className="text-[10px] text-[var(--gs-muted)] mb-2">
                        {acct.info?.channel_name || "Connected"} · {acct.info?.connected_at ? new Date(acct.info.connected_at).toLocaleDateString("en-IN") : ""}
                      </div>
                      <Button size="sm" variant="ghost" className="w-full text-rose-500 h-7" onClick={() => disconnectAccount(acct.platform)}>
                        <Unlink className="h-3 w-3 mr-1"/> Disconnect
                      </Button>
                    </>
                  ) : (
                    <Button size="sm" variant="outline" className="w-full h-7"
                            onClick={() => setConnectPlatform(acct.platform)}>
                      <Link className="h-3 w-3 mr-1"/> Connect
                    </Button>
                  )}
                </Card>
              );
            })}
          </div>

          {/* Connect form */}
          <Card className="p-5 space-y-4">
            <h3 className="font-display text-lg flex items-center gap-2">
              <Link className="h-5 w-5 text-[var(--gs-teal)]"/> Connect a Platform
            </h3>
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Platform</label>
              <Select value={connectPlatform} onValueChange={setConnectPlatform}>
                <SelectTrigger><SelectValue placeholder="Choose platform…"/></SelectTrigger>
                <SelectContent>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                  <SelectItem value="facebook">Facebook</SelectItem>
                  <SelectItem value="twitter">Twitter / X</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {connectPlatform && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800">
                <div className="font-semibold mb-1">Token kaise milega ({connectPlatform}):</div>
                <div>{platforms.find(p => p.platform === connectPlatform)?.instructions ||
                  {
                    youtube: "Google Cloud Console → OAuth 2.0 → Enable YouTube Data API v3 → Get access token via OAuth playground",
                    instagram: "Meta for Developers → Instagram Basic Display API → Get long-lived access token (60 days)",
                    facebook: "Meta for Developers → Facebook Login → Get Page access token from Graph Explorer",
                    twitter: "Twitter Developer Portal → Create App → OAuth 2.0 → Generate Bearer token",
                  }[connectPlatform]
                }</div>
              </div>
            )}

            <div>
              <label className="text-xs text-[var(--gs-muted)]">Access Token *</label>
              <Input value={connectToken} onChange={e => setConnectToken(e.target.value)}
                     type="password" placeholder="Paste your access token here…"/>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Channel / Account ID (optional)</label>
                <Input value={connectChannelId} onChange={e => setConnectChannelId(e.target.value)}
                       placeholder="e.g. UCxxxxxx or 17841..."/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Channel name (optional)</label>
                <Input value={connectChannelName} onChange={e => setConnectChannelName(e.target.value)}
                       placeholder="e.g. My YouTube Channel"/>
              </div>
            </div>
            <Button onClick={connectAccount} disabled={connectBusy || !connectPlatform || !connectToken}
                    className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {connectBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Link className="h-4 w-4 mr-2"/>}
              {connectBusy ? "Connecting…" : "Connect Account"}
            </Button>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Jobs list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-display text-xl">Recent video jobs</h3>
          <Button variant="ghost" size="sm" onClick={load} data-testid="reload-jobs">
            <RefreshCw className="h-4 w-4 mr-1"/> Refresh
          </Button>
        </div>
        {jobs.length === 0 ? (
          <Card className="p-6 text-center text-sm text-[var(--gs-muted)]">Koi jobs nahi hain abhi — upar se video generate karo.</Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="video-jobs-grid">
            {jobs.map(j => <JobCard key={j.id} j={j} onView={openJob} onDelete={delJob}/>)}
          </div>
        )}
      </div>

      {/* Job detail panel */}
      {active && (
        <Card className="p-5 fixed inset-x-4 bottom-4 md:inset-x-auto md:right-4 md:bottom-4 md:w-[480px] shadow-2xl z-40"
              data-testid="video-job-detail">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h4 className="font-display text-lg">{active.topic}</h4>
              <div className="text-[10px] text-[var(--gs-muted)]">{active.id}</div>
            </div>
            <button onClick={() => setActive(null)} className="text-[var(--gs-muted)] text-lg">✕</button>
          </div>
          {active.script && (
            <div className="mt-3 max-h-64 overflow-y-auto text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl">
              <div className="font-semibold">Script: {active.script.title}</div>
              {active.script.hook && <div className="mt-1 italic">Hook: {active.script.hook}</div>}
              {(active.script.hashtags || []).slice(0, 6).map((h, i) => (
                <Badge key={i} variant="outline" className="text-[9px] mr-1 mt-1">{h}</Badge>
              ))}
            </div>
          )}
          {active.scenes && (
            <div className="mt-2 text-[11px]">
              <div className="text-[var(--gs-muted)] mb-1">{active.scenes.length} scenes</div>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {active.scenes.slice(0, 10).map((s, i) => (
                  <div key={i} className="flex gap-2 items-start">
                    <Badge variant="outline" className="text-[9px]">{s.seconds}s</Badge>
                    <span className="flex-1">{s.narration_chunk}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
