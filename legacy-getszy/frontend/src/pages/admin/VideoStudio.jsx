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
  Youtube, Instagram, Facebook, Twitter, Send, Link, Unlink, AlertCircle,
  Image, Mic, User, Zap, Upload, Wand2, Copy, ExternalLink
} from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const NICHES = [
  {
    id: "finance",
    emoji: "💰",
    label: "Finance / Paise",
    color: "border-emerald-300 bg-emerald-50 hover:bg-emerald-100",
    badge: "bg-emerald-100 text-emerald-800",
    tone: "energetic",
    lang: "hinglish",
    examples: [
      "₹500 rozana bachao toh 10 saal mein kitna banega",
      "Salary aate hi pehle 5 kaam karo",
      "SIP vs FD — konsa better hai 2026 mein",
      "Student loan chukane ke 5 fastest tarike",
      "Tax bachane ke legal tarike jo CA bhi use karte hain",
    ],
  },
  {
    id: "motivational",
    emoji: "🧠",
    label: "Motivation / Self-help",
    color: "border-purple-300 bg-purple-50 hover:bg-purple-100",
    badge: "bg-purple-100 text-purple-800",
    tone: "inspirational",
    lang: "hinglish",
    examples: [
      "Gareeb ghar mein paida hone ke baad bhi success kaise paayein",
      "Ek achi habit jo aapki poori life badal degi",
      "Roz subah 5 baje uthne ka asar 30 din mein",
      "Rejection ke baad wapas kaise uthein",
      "Log kyun talented hote hue bhi fail ho jaate hain",
    ],
  },
  {
    id: "news",
    emoji: "📰",
    label: "News / Current Affairs",
    color: "border-blue-300 bg-blue-50 hover:bg-blue-100",
    badge: "bg-blue-100 text-blue-800",
    tone: "authoritative",
    lang: "hindi",
    examples: [
      "Budget 2026 mein aapko kya mila aur kya nahi",
      "India-China border par kya ho raha hai",
      "AI jobs kha raha hai — India mein kitne jobs khatre mein",
      "Rupee ki giravat aap par kaisa asar dalegi",
      "Petrol price kyun badh rahi hai — asli wajah",
    ],
  },
  {
    id: "recipe",
    emoji: "🍳",
    label: "Recipe / Tutorial",
    color: "border-orange-300 bg-orange-50 hover:bg-orange-100",
    badge: "bg-orange-100 text-orange-800",
    tone: "calm",
    lang: "hindi",
    examples: [
      "10 minute mein restaurant jaisi dal makhani",
      "Bina oven ke eggless cake ghar par",
      "Street style pav bhaji ghar par banao",
      "Protein se bhari nashte ki recipe for gym lovers",
      "Monsoon ke liye garam masala chai 5 tarike",
    ],
  },
  {
    id: "educational",
    emoji: "📚",
    label: "Education / Facts",
    color: "border-yellow-300 bg-yellow-50 hover:bg-yellow-100",
    badge: "bg-yellow-100 text-yellow-800",
    tone: "calm",
    lang: "hinglish",
    examples: [
      "Mughal empire ke 5 raaz jo school mein nahi padhaye",
      "Kya humans ka blood color hamesha se red tha",
      "Black hole ke andar kya hota hai — science ki bhasaa mein",
      "India ne space race kaise jeet li with zero budget",
      "Dinosaur ab bhi maujood hain — kaise",
    ],
  },
];

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
  const [category, setCategory] = useState("");
  const [activeNiche, setActiveNiche] = useState(null);
  const [activeTab, setActiveTab] = useState("single");
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

  // Visual provider
  const [visualProvider, setVisualProvider] = useState("pollinations");
  const [fluxAvailable, setFluxAvailable] = useState(false);

  // Avatar Studio
  const [imgPrompt, setImgPrompt]         = useState("");
  const [imgBusy, setImgBusy]             = useState(false);
  const [imgResult, setImgResult]         = useState(null);
  const [imgOrientation, setImgOrientation] = useState("9:16");
  const [voiceFile, setVoiceFile]         = useState(null);
  const [voiceName, setVoiceName]         = useState("");
  const [voiceBusy, setVoiceBusy]         = useState(false);
  const [voiceResult, setVoiceResult]     = useState(null);
  const [avatarImg, setAvatarImg]         = useState(null);
  const [avatarAudio, setAvatarAudio]     = useState(null);
  const [avatarBusy, setAvatarBusy]       = useState(false);
  const [avatarResult, setAvatarResult]   = useState(null);

  // Social connect
  const [connectPlatform, setConnectPlatform] = useState("");
  const [connectToken, setConnectToken]       = useState("");
  const [connectChannelId, setConnectChannelId] = useState("");
  const [connectChannelName, setConnectChannelName] = useState("");
  const [connectBusy, setConnectBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/video/voices");
      setVoices(r.data);
      if (r.data.flux_hd_available) setFluxAvailable(true);
    } catch (_) {}
    try { const r = await api.get("/video/jobs?limit=30"); setJobs(r.data.items || []); } catch (_) {}
    try { const r = await api.get("/social/accounts"); setPlatforms(r.data.platforms || []); } catch (_) {}
    try { const r = await api.get("/social/scheduled"); setScheduled(r.data.items || []); } catch (_) {}
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 6000); return () => clearInterval(t); }, [load]);

  // ── Generators ──────────────────────────────────────────────────

  const pickNiche = (niche) => {
    setActiveNiche(niche.id);
    setCategory(niche.id);
    setTone(niche.tone);
    setLanguage(niche.lang);
    setTopic(niche.examples[Math.floor(Math.random() * niche.examples.length)]);
    setActiveTab("single");
  };

  const generate = async () => {
    if (topic.trim().length < 4) return toast.error("Topic too short");
    setBusy(true);
    toast.loading("Queuing video job…", { id: "vid" });
    try {
      const r = await api.post("/video/generate", {
        topic, orientation, language, voice_gender: voiceGender,
        target_seconds: Number(seconds), tone, subtitles, category,
        visual_provider: visualProvider,
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

      {/* ── Niche Quick-Start ─────────────────────────────────── */}
      <div>
        <h2 className="font-display text-base mb-3 text-[var(--gs-muted)]">🎯 Quick Start — Apna niche chunno</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {NICHES.map(n => (
            <button key={n.id} onClick={() => pickNiche(n)}
                    className={`p-3 rounded-xl border-2 text-left transition-all cursor-pointer
                      ${activeNiche === n.id ? "ring-2 ring-[var(--gs-teal)] ring-offset-1" : ""}
                      ${n.color}`}>
              <div className="text-2xl mb-1">{n.emoji}</div>
              <div className="font-semibold text-xs leading-tight">{n.label}</div>
              <div className={`text-[9px] mt-1 px-1.5 py-0.5 rounded inline-block ${n.badge}`}>
                {n.examples.length} topics
              </div>
            </button>
          ))}
        </div>
        {activeNiche && (
          <div className="mt-3 p-3 rounded-xl bg-[var(--gs-surface-2)] border">
            <div className="text-[10px] text-[var(--gs-muted)] mb-2 font-semibold uppercase tracking-wide">
              {NICHES.find(n => n.id === activeNiche)?.label} — Example topics (click to use)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {NICHES.find(n => n.id === activeNiche)?.examples.map((ex, i) => (
                <button key={i} onClick={() => { setTopic(ex); setActiveTab("single"); }}
                        className="text-[11px] px-2.5 py-1 rounded-full border border-gray-200 bg-white hover:border-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/5 transition-all text-left">
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="single"><Film className="h-4 w-4 mr-1"/>Single Video</TabsTrigger>
          <TabsTrigger value="batch"><Layers className="h-4 w-4 mr-1"/>Batch</TabsTrigger>
          <TabsTrigger value="story"><BookOpen className="h-4 w-4 mr-1"/>AI Stories</TabsTrigger>
          <TabsTrigger value="avatar"><User className="h-4 w-4 mr-1"/>Avatar Studio</TabsTrigger>
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

            {/* Visual Provider Selector */}
            <div className="p-3 rounded-xl border-2 space-y-2"
              style={{ borderColor: visualProvider === "flux_hd" ? "#7c3aed" : "var(--gs-border)" }}>
              <div className="text-xs font-semibold text-[var(--gs-muted)]">🎨 Visuals Provider</div>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => setVisualProvider("pollinations")}
                  className={`p-2.5 rounded-lg border text-xs text-left transition-all ${visualProvider === "pollinations" ? "border-[var(--gs-teal)] bg-[var(--gs-teal)]/5 font-semibold" : "border-gray-200 hover:border-gray-300"}`}>
                  <div className="font-semibold">🆓 Pollinations</div>
                  <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">Free · Fast · Good quality</div>
                </button>
                <button onClick={() => fluxAvailable ? setVisualProvider("flux_hd") : toast.error("HF_TOKEN not set on server")}
                  className={`p-2.5 rounded-lg border text-xs text-left transition-all relative ${visualProvider === "flux_hd" ? "border-violet-500 bg-violet-50 font-semibold" : fluxAvailable ? "border-gray-200 hover:border-violet-300" : "border-gray-200 opacity-60"}`}>
                  <div className="font-semibold text-violet-700">⚡ FLUX HD</div>
                  <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">HuggingFace · Best quality</div>
                  {!fluxAvailable && <span className="absolute top-1.5 right-1.5 text-[9px] bg-amber-100 text-amber-700 px-1 rounded">No HF key</span>}
                  {fluxAvailable && <span className="absolute top-1.5 right-1.5 text-[9px] bg-emerald-100 text-emerald-700 px-1 rounded">✓ Ready</span>}
                </button>
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

        {/* ── Avatar Studio ─────────────────────────────────────── */}
        <TabsContent value="avatar" className="mt-4 space-y-4">
          <div className="grid md:grid-cols-2 gap-4">

            {/* 1. AI Image Generator */}
            <Card className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-violet-100 grid place-items-center">
                  <Image className="h-4 w-4 text-violet-600"/>
                </div>
                <div>
                  <h3 className="font-semibold text-sm">AI Image Generator</h3>
                  <p className="text-[10px] text-[var(--gs-muted)]">FLUX HD — text se HD image banao</p>
                </div>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Image Prompt *</label>
                <Textarea rows={3} value={imgPrompt} onChange={e => setImgPrompt(e.target.value)}
                  placeholder="e.g. A cinematic shot of a young Indian entrepreneur in a modern Mumbai office, golden hour lighting, 8K…"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Orientation</label>
                <Select value={imgOrientation} onValueChange={setImgOrientation}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="9:16">9:16 Portrait (Reels)</SelectItem>
                    <SelectItem value="16:9">16:9 Landscape (YT)</SelectItem>
                    <SelectItem value="1:1">1:1 Square</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={async () => {
                if (!imgPrompt.trim()) return toast.error("Prompt required");
                setImgBusy(true);
                setImgResult(null);
                try {
                  const r = await api.post("/avatar/generate-image", { prompt: imgPrompt, orientation: imgOrientation });
                  setImgResult(r.data);
                  toast.success("Image generated!");
                } catch (e) {
                  toast.error(e?.response?.data?.detail || "Image generation failed");
                } finally { setImgBusy(false); }
              }} disabled={imgBusy} className="w-full bg-violet-600 hover:bg-violet-700 text-white">
                {imgBusy ? <><Loader2 className="h-4 w-4 animate-spin mr-2"/>Generating…</> : <><Wand2 className="h-4 w-4 mr-2"/>Generate Image</>}
              </Button>
              {imgResult?.image_url && (
                <div className="space-y-2">
                  <img src={`${BACKEND_URL}${imgResult.image_url}`} alt="Generated" className="w-full rounded-xl object-cover max-h-64"/>
                  <a href={`${BACKEND_URL}${imgResult.image_url}`} download className="text-xs text-[var(--gs-teal)] flex items-center gap-1">
                    <Download className="h-3 w-3"/>Download
                  </a>
                </div>
              )}
            </Card>

            {/* 2. Voice Clone */}
            <Card className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-emerald-100 grid place-items-center">
                  <Mic className="h-4 w-4 text-emerald-600"/>
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Voice Clone</h3>
                  <p className="text-[10px] text-[var(--gs-muted)]">Apni awaaz upload karo — clone ready</p>
                </div>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Voice Name *</label>
                <Input value={voiceName} onChange={e => setVoiceName(e.target.value)} placeholder="e.g. my_voice, priya_voice"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Audio Sample * (10-30 sec, WAV/MP3)</label>
                <div className="mt-1 border-2 border-dashed rounded-xl p-4 text-center cursor-pointer hover:border-[var(--gs-teal)] transition-colors"
                  onClick={() => document.getElementById('voice-upload').click()}>
                  <Upload className="h-5 w-5 mx-auto mb-1 text-[var(--gs-muted)]"/>
                  <div className="text-xs text-[var(--gs-muted)]">{voiceFile ? voiceFile.name : "Click to upload audio"}</div>
                  <input id="voice-upload" type="file" accept="audio/*" className="hidden" onChange={e => setVoiceFile(e.target.files[0])}/>
                </div>
              </div>
              <Button onClick={async () => {
                if (!voiceFile || !voiceName.trim()) return toast.error("Voice name + audio required");
                setVoiceBusy(true);
                setVoiceResult(null);
                const fd = new FormData();
                fd.append("file", voiceFile);
                fd.append("voice_name", voiceName);
                try {
                  const r = await api.post("/avatar/clone-voice", fd, { headers: { "Content-Type": "multipart/form-data" } });
                  setVoiceResult(r.data);
                  toast.success(`Voice "${voiceName}" cloned!`);
                } catch (e) {
                  toast.error(e?.response?.data?.detail || "Clone failed");
                } finally { setVoiceBusy(false); }
              }} disabled={voiceBusy} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white">
                {voiceBusy ? <><Loader2 className="h-4 w-4 animate-spin mr-2"/>Cloning…</> : <><Mic className="h-4 w-4 mr-2"/>Clone Voice</>}
              </Button>
              {voiceResult && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs space-y-1">
                  <div className="font-semibold text-emerald-700">✓ Voice cloned!</div>
                  <div className="text-[var(--gs-muted)]">ID: {voiceResult.voice_id || voiceName}</div>
                  {voiceResult.sample_url && (
                    <audio controls src={`${BACKEND_URL}${voiceResult.sample_url}`} className="w-full mt-1"/>
                  )}
                </div>
              )}
            </Card>

            {/* 3. Talking Avatar */}
            <Card className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-pink-100 grid place-items-center">
                  <User className="h-4 w-4 text-pink-600"/>
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Talking Avatar</h3>
                  <p className="text-[10px] text-[var(--gs-muted)]">Photo + Audio → Talking face video (SadTalker)</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-[var(--gs-muted)]">Face Photo *</label>
                  <div className="mt-1 border-2 border-dashed rounded-xl p-3 text-center cursor-pointer hover:border-pink-400 transition-colors"
                    onClick={() => document.getElementById('avatar-img-upload').click()}>
                    {avatarImg ? (
                      <img src={URL.createObjectURL(avatarImg)} alt="" className="w-16 h-16 rounded-full mx-auto object-cover"/>
                    ) : (
                      <><Upload className="h-5 w-5 mx-auto mb-1 text-[var(--gs-muted)]"/><div className="text-[10px] text-[var(--gs-muted)]">Upload photo</div></>
                    )}
                    <input id="avatar-img-upload" type="file" accept="image/*" className="hidden" onChange={e => setAvatarImg(e.target.files[0])}/>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[var(--gs-muted)]">Drive Audio *</label>
                  <div className="mt-1 border-2 border-dashed rounded-xl p-3 text-center cursor-pointer hover:border-pink-400 transition-colors"
                    onClick={() => document.getElementById('avatar-audio-upload').click()}>
                    <Mic className="h-5 w-5 mx-auto mb-1 text-[var(--gs-muted)]"/>
                    <div className="text-[10px] text-[var(--gs-muted)]">{avatarAudio ? avatarAudio.name : "Upload audio"}</div>
                    <input id="avatar-audio-upload" type="file" accept="audio/*" className="hidden" onChange={e => setAvatarAudio(e.target.files[0])}/>
                  </div>
                </div>
              </div>
              <Button onClick={async () => {
                if (!avatarImg || !avatarAudio) return toast.error("Photo + audio dono required");
                setAvatarBusy(true);
                setAvatarResult(null);
                const fd = new FormData();
                fd.append("image", avatarImg);
                fd.append("audio", avatarAudio);
                try {
                  const r = await api.post("/avatar/talking-head", fd, { headers: { "Content-Type": "multipart/form-data" } });
                  setAvatarResult(r.data);
                  toast.success("Talking avatar generated!");
                } catch (e) {
                  toast.error(e?.response?.data?.detail || "Avatar generation failed");
                } finally { setAvatarBusy(false); }
              }} disabled={avatarBusy} className="w-full bg-pink-600 hover:bg-pink-700 text-white">
                {avatarBusy ? <><Loader2 className="h-4 w-4 animate-spin mr-2"/>Generating…</> : <><User className="h-4 w-4 mr-2"/>Generate Talking Avatar</>}
              </Button>
              {avatarResult?.video_url && (
                <video src={`${BACKEND_URL}${avatarResult.video_url}`} controls className="w-full rounded-xl max-h-48"/>
              )}
              {avatarResult?.status === "queued" && (
                <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded-lg">⏳ Job queued — ~2-3 min lagenge. Recent Jobs mein check karo.</div>
              )}
            </Card>

            {/* 4. AI Status */}
            <Card className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-amber-100 grid place-items-center">
                  <Zap className="h-4 w-4 text-amber-600"/>
                </div>
                <div>
                  <h3 className="font-semibold text-sm">AI Stack Status</h3>
                  <p className="text-[10px] text-[var(--gs-muted)]">Available AI providers on server</p>
                </div>
              </div>
              <div className="space-y-2">
                {[
                  { name: "FLUX HD (HF)",   available: fluxAvailable, label: fluxAvailable ? "✓ Ready" : "HF_TOKEN missing", color: fluxAvailable ? "text-emerald-600" : "text-amber-600", bg: fluxAvailable ? "bg-emerald-50" : "bg-amber-50" },
                  { name: "Pollinations",   available: true,          label: "✓ Free, no key", color: "text-emerald-600", bg: "bg-emerald-50" },
                  { name: "edge-tts",       available: true,          label: "✓ Free Indian voices", color: "text-emerald-600", bg: "bg-emerald-50" },
                  { name: "XTTS Voice Clone", available: fluxAvailable, label: fluxAvailable ? "✓ Via HF" : "Needs HF_TOKEN", color: fluxAvailable ? "text-emerald-600" : "text-amber-600", bg: fluxAvailable ? "bg-emerald-50" : "bg-amber-50" },
                  { name: "SadTalker",      available: false,         label: "GPU needed (optional)", color: "text-slate-500", bg: "bg-slate-50" },
                ].map(s => (
                  <div key={s.name} className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs ${s.bg}`}>
                    <span className="font-medium">{s.name}</span>
                    <span className={`font-semibold ${s.color}`}>{s.label}</span>
                  </div>
                ))}
              </div>
              <Button variant="outline" size="sm" className="w-full text-xs" onClick={async () => {
                try {
                  const r = await api.get("/avatar/status");
                  toast.success(`Avatar API: ${JSON.stringify(r.data).slice(0, 80)}`);
                } catch (e) {
                  toast.error("Avatar API unreachable — server check karo");
                }
              }}>
                <Zap className="h-3.5 w-3.5 mr-1"/> Test Avatar API
              </Button>
            </Card>
          </div>
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
