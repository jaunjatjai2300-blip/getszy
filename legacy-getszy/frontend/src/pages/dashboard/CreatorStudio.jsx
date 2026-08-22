import { useState, useEffect } from "react";
import {
  Sparkles, Clapperboard, Flame, ListOrdered, Film, Languages,
  Scissors, Upload, Send, Bot, Image as ImageIcon, Mic, User, Wand2, Loader2,
  Target, MessageSquare, Layers,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import PageState from "@/components/dashboard/PageState";
import DashboardPageFrame from "@/components/dashboard/DashboardPageFrame";

/* ─── tiny helpers ─────────────────────────────────────────────────────────── */

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const DONE = ["done", "failed", "done_no_lipsync"];

async function pollUntilDone(getUrl, id, onUpdate, max = 80) {
  for (let i = 0; i < max; i++) {
    try {
      const { data } = await api.get(`${getUrl}/${id}`);
      onUpdate(data);
      if (DONE.includes(data.status)) return data;
    } catch {
      /* ignore transient */
    }
    await sleep(3000);
  }
  onUpdate({ status: "timeout" });
  return null;
}

function AuthenticatedMedia({ url, type, alt = "Generated media", className = "", controls = false }) {
  const [objectUrl, setObjectUrl] = useState(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    let localUrl;
    setObjectUrl(null);
    setLoadError(false);
    if (!url) return undefined;
    api.get(url, { responseType: "blob" })
      .then(({ data }) => {
        localUrl = URL.createObjectURL(data);
        if (active) setObjectUrl(localUrl);
      })
      .catch(() => { if (active) setLoadError(true); });
    return () => {
      active = false;
      if (localUrl) URL.revokeObjectURL(localUrl);
    };
  }, [url]);

  if (loadError) return <div className="mt-1 text-xs text-rose-600">Protected media could not be loaded.</div>;
  if (!objectUrl) return <div className="mt-1 text-xs text-[var(--gs-muted)]">Loading protected media…</div>;
  if (type === "image") return <img src={objectUrl} alt={alt} className={className} />;
  if (type === "audio") return <audio src={objectUrl} controls={controls} className={className} />;
  return <video src={objectUrl} controls={controls} className={className} />;
}

async function downloadAuthenticatedMedia(url, filename) {
  const { data } = await api.get(url, { responseType: "blob" });
  const objectUrl = URL.createObjectURL(data);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename || "getszy-media";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function Section({ icon: Icon, title, badge, children }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="h-5 w-5 text-[var(--gs-teal)]" />
        <h2 className="font-display text-xl">{title}</h2>
        {badge ? <Badge className="bg-[var(--gs-teal)]/15 text-[var(--gs-teal)] ml-auto">{badge}</Badge> : null}
      </div>
      {children}
    </Card>
  );
}

function FileField({ label, accept, onChange, file }) {
  return (
    <div>
      <label className="text-xs font-medium">{label}</label>
      <input type="file" accept={accept} onChange={(e) => onChange(e.target.files?.[0] || null)}
        className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--gs-teal)] file:px-3 file:py-1 file:text-white" />
      {file ? <p className="text-xs text-[var(--gs-muted)] mt-1">{file.name}</p> : null}
    </div>
  );
}

function ResultView({ data, kind }) {
  if (!data) return null;
  const failed = data.status === "failed";
  if (failed) return <PageState compact kind="error" title="Failed" message={data.error || "Generation failed"} />;
  if (data.status === "timeout") return <PageState compact kind="error" title="Still processing" message="Taking longer than expected — refresh shortly." />;

  if (kind === "storyboard" && data.storyboard) {
    return (
      <div className="space-y-2 mt-2">
        {data.storyboard.map((s) => (
          <div key={s.scene} className="rounded-lg border p-2">
            <div className="text-xs font-semibold text-[var(--gs-teal)]">Scene {s.scene}</div>
            <div className="text-sm">{s.visual}</div>
            <div className="text-xs text-[var(--gs-muted)]">“{s.caption}” — {s.narration}</div>
            {s.image_url ? <AuthenticatedMedia url={s.image_url} type="image" alt={`Storyboard scene ${s.scene}`} className="mt-1 rounded w-32" /> : null}
            {s.clip_url ? <AuthenticatedMedia url={s.clip_url} type="video" controls className="mt-1 w-40 rounded" /> : null}
          </div>
        ))}
      </div>
    );
  }
  if (kind === "shorts" && data.shorts) {
    return (
      <div className="space-y-2 mt-2">
        {data.shorts.map((m, i) => (
          <div key={i} className="rounded-lg border p-2 text-sm">
            <span className="font-semibold text-rose-500">{m.start}–{m.end}s</span> · {m.hook}
            <div className="text-xs text-[var(--gs-muted)]">“{m.caption}”</div>
          </div>
        ))}
      </div>
    );
  }
  if (kind === "video" && data.url) {
    return <AuthenticatedMedia url={data.url} type="video" controls className="mt-2 w-full rounded-lg" />;
  }
  if (kind === "translate" && data.translated_text) {
    return (
      <div className="mt-2 space-y-1 text-sm">
        <div><span className="font-semibold">Translated:</span> {data.translated_text}</div>
        {data.dubbed_audio_url ? <AuthenticatedMedia url={data.dubbed_audio_url} type="audio" controls className="w-full" /> : null}
        {data.synced_video_url ? <AuthenticatedMedia url={data.synced_video_url} type="video" controls className="w-full rounded" /> : null}
        {data.note ? <div className="text-xs text-amber-600">{data.note}</div> : null}
      </div>
    );
  }
  if (kind === "reply" && data.reply) {
    return <div className="mt-2 rounded-lg border bg-[var(--gs-surface-2)] p-2 text-sm">{data.reply}</div>;
  }
  if (kind === "social") {
    return <div className="mt-2 text-sm text-[var(--gs-muted)]">{data.message || "Queued."}</div>;
  }
  return <PageState compact kind="loading" title="Processing…" />;
}

function StoryboardTimeline({ scenes }) {
  const [order, setOrder] = useState(() => scenes.map((_, i) => i));
  const [locked, setLocked] = useState({});
  useEffect(() => { setOrder(scenes.map((_, i) => i)); setLocked({}); }, [scenes]);
  const move = (from, to) => {
    if (locked[from] || locked[to] || to < 0 || to >= order.length) return;
    setOrder((o) => { const n = [...o]; [n[from], n[to]] = [n[to], n[from]]; return n; });
  };
  const toggleLock = (i) => setLocked((l) => ({ ...l, [i]: !l[i] }));
  return (
    <div className="mt-3">
      <div className="text-xs font-semibold text-[var(--gs-muted)] mb-1">Timeline (drag order · lock to protect)</div>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {order.map((idx, pos) => {
          const s = scenes[idx];
          return (
            <div key={idx} className={`relative shrink-0 w-36 rounded-lg border ${locked[idx] ? "border-amber-400" : "border-[var(--gs-border)]"} p-2`}>
              <div className="text-[10px] text-[var(--gs-muted)]">#{pos + 1}</div>
              {s.image_url ? <AuthenticatedMedia url={s.image_url} type="image" alt={`Storyboard scene ${pos + 1}`} className="h-16 w-full object-cover rounded" /> : <div className="h-16 bg-[var(--gs-surface-2)] rounded" />}
              <div className="text-[11px] mt-1 line-clamp-2">{s.caption || s.visual}</div>
              <div className="mt-1 flex items-center justify-between">
                <div className="flex gap-1">
                  <button onClick={() => move(pos, pos - 1)} className="text-xs px-1 rounded bg-[var(--gs-surface-2)]">◀</button>
                  <button onClick={() => move(pos, pos + 1)} className="text-xs px-1 rounded bg-[var(--gs-surface-2)]">▶</button>
                </div>
                <button onClick={() => toggleLock(idx)} className={`text-[10px] px-1 rounded ${locked[idx] ? "bg-amber-400 text-black" : "bg-[var(--gs-surface-2)]"}`}>
                  {locked[idx] ? "Locked" : "Lock"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Hooks & Memes (existing) ─────────────────────────────────────────────── */

function HooksMemes() {
  const [niche, setNiche] = useState("");
  const [count, setCount] = useState(5);
  const [blend, setBlend] = useState(false);
  const [hooks, setHooks] = useState(null);
  const [source, setSource] = useState("");
  const [style, setStyle] = useState("story");
  const [scenes, setScenes] = useState(6);
  const [story, setStory] = useState(null);
  const [busy, setBusy] = useState(false);

  const genHooks = async () => {
    if (niche.trim().length < 2) return toast.error("Enter a niche");
    setBusy(true); setHooks(null);
    try {
      const { data } = await api.post("/creator/viral-hooks", { niche: niche.trim(), count, language: "hinglish", blend_trends: blend });
      setHooks(data.hooks || []);
    } catch { toast.error("Hook generation failed"); }
    finally { setBusy(false); }
  };
  const genStory = async () => {
    if (source.trim().length < 10) return toast.error("Paste at least 10 characters");
    setBusy(true); setStory(null);
    try {
      const { data } = await api.post("/creator/meme-mode", { source_text: source.trim(), style, scenes, language: "hinglish" });
      setStory(data.storyboard || []);
    } catch { toast.error("Storyboard failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section icon={Flame} title="Viral Hook Generator" badge="Hook">
        <div className="space-y-3">
          <label className="text-xs font-medium">Niche / topic</label>
          <Input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="history facts, finance tips…" data-testid="hook-niche" />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium">Hooks</label>
            <Input type="number" min={1} max={10} value={count} onChange={(e) => setCount(Number(e.target.value) || 5)} className="w-20" />
            <label className="flex items-center gap-1.5 text-xs ml-auto cursor-pointer">
              <input type="checkbox" checked={blend} onChange={(e) => setBlend(e.target.checked)} /> Blend trend-inspired patterns
            </label>
          </div>
          <Button onClick={genHooks} disabled={busy} className="w-full bg-rose-600 hover:bg-rose-700" data-testid="hook-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />} Generate Hooks
          </Button>
          {hooks ? (
            hooks.length === 0 ? <PageState compact kind="empty" title="No hooks" message="Try another niche." /> :
            <ol className="space-y-2">{hooks.map((h, i) => <li key={i} className="flex gap-2 items-start rounded-lg border bg-[var(--gs-surface-2)] p-2 text-sm"><span className="font-semibold text-rose-500">{i + 1}.</span><span>{h}</span></li>)}</ol>
          ) : null}
        </div>
      </Section>

      <Section icon={ListOrdered} title="Meme & Story Mode" badge="Faceless">
        <div className="space-y-3">
          <label className="text-xs font-medium">Source text</label>
          <Textarea value={source} onChange={(e) => setSource(e.target.value)} rows={4} placeholder="Paste a story, fact, or post…" data-testid="story-source" />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium">Style</label>
            <select value={style} onChange={(e) => setStyle(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm" data-testid="story-style">
              {["story", "meme", "documentary"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <label className="text-xs font-medium ml-auto">Scenes</label>
            <Input type="number" min={2} max={12} value={scenes} onChange={(e) => setScenes(Number(e.target.value) || 6)} className="w-20" />
          </div>
          <Button onClick={genStory} disabled={busy} className="w-full" data-testid="story-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Clapperboard className="mr-2 h-4 w-4" />} Build Storyboard
          </Button>
          {story ? (
            story.length === 0 ? <PageState compact kind="empty" title="No scenes" message="Paste source and build." /> :
            <div className="space-y-2">{story.map((s, i) => <div key={i} className="rounded-lg border p-2"><div className="text-xs font-semibold text-[var(--gs-teal)]">Scene {s.scene ?? i + 1}</div><div className="text-sm">{s.visual}</div>{s.caption ? <div className="text-xs text-[var(--gs-muted)]">“{s.caption}”</div> : null}</div>)}</div>
          ) : null}
        </div>
      </Section>
    </div>
  );
}

/* ─── Avatars ──────────────────────────────────────────────────────────────── */

function Avatars() {
  const [portrait, setPortrait] = useState(null);
  const [script, setScript] = useState("");
  const [voice, setVoice] = useState(null);
  const [expr, setExpr] = useState("neutral");
  const [twinVideo, setTwinVideo] = useState(null);
  const [twinPortrait, setTwinPortrait] = useState(null);
  const [twinScript, setTwinScript] = useState("");
  const [photoRes, setPhotoRes] = useState(null);
  const [twinRes, setTwinRes] = useState(null);
  const [avatarConsent, setAvatarConsent] = useState(false);
  const [twinConsent, setTwinConsent] = useState(false);
  const [busy, setBusy] = useState(false);

  const photoToAvatar = async () => {
    if (!portrait || !voice || script.trim().length < 2) return toast.error("Need photo, voice sample & script");
    if (!avatarConsent) return toast.error("Confirm that you have permission to use this person’s portrait and voice");
    setBusy(true); setPhotoRes({ status: "queued" });
    try {
      const fd = new FormData();
      fd.append("portrait", portrait); fd.append("reference_audio", voice); fd.append("script", script); fd.append("expression", expr);
      const { data } = await api.post("/avatar/photo-to-avatar", fd);
      await pollUntilDone("/avatar/job", data.job_id, setPhotoRes);
    } catch (e) { toast.error(e?.response?.data?.detail || "Photo-to-Avatar failed"); }
    finally { setBusy(false); }
  };
  const digitalTwin = async () => {
    if (!twinVideo || !twinPortrait || twinScript.trim().length < 2) return toast.error("Need video, portrait & script");
    if (!twinConsent) return toast.error("Confirm that you have permission to create this digital twin");
    setBusy(true); setTwinRes({ status: "queued" });
    try {
      const fd = new FormData();
      fd.append("video", twinVideo); fd.append("portrait", twinPortrait); fd.append("script", twinScript);
      const { data } = await api.post("/avatar/digital-twin", fd);
      await pollUntilDone("/avatar/job", data.job_id, setTwinRes);
    } catch (e) { toast.error(e?.response?.data?.detail || "Digital Twin failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section icon={User} title="Photo-to-Avatar" badge="Text+Photo">
        <div className="space-y-3">
          <FileField label="Portrait photo" accept="image/*" onChange={setPortrait} file={portrait} />
          <FileField label="Voice sample (10s+)" accept="audio/*" onChange={setVoice} file={voice} />
          <label className="text-xs font-medium">Script</label>
          <Textarea value={script} onChange={(e) => setScript(e.target.value)} rows={2} placeholder="What should your avatar say?" />
          <label className="text-xs font-medium">Expression</label>
          <select value={expr} onChange={(e) => setExpr(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
            {["neutral", "happy", "excited", "urgent", "calm"].map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
          <label className="flex items-start gap-2 rounded-lg border p-2 text-xs" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}><input type="checkbox" checked={avatarConsent} onChange={(e) => setAvatarConsent(e.target.checked)} className="mt-0.5" /><span>I confirm that I have permission to use this person’s portrait and voice for this output. I will review the final video, claims, disclosures, and platform rules before publishing.</span></label>
          <Button onClick={photoToAvatar} disabled={busy || !avatarConsent} className="w-full" data-testid="photo-to-avatar">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />} Create Talking Avatar
          </Button>
          <ResultView data={photoRes} kind="video" />
        </div>
      </Section>

      <Section icon={Clapperboard} title="Digital Twin" badge="Video→Clone">
        <div className="space-y-3">
          <FileField label="Short video of you speaking" accept="video/*" onChange={setTwinVideo} file={twinVideo} />
          <FileField label="Clear portrait photo" accept="image/*" onChange={setTwinPortrait} file={twinPortrait} />
          <label className="text-xs font-medium">Script</label>
          <Textarea value={twinScript} onChange={(e) => setTwinScript(e.target.value)} rows={2} placeholder="What should the presenter say? Include only approved claims and product facts." />
          <label className="flex items-start gap-2 rounded-lg border p-2 text-xs" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}><input type="checkbox" checked={twinConsent} onChange={(e) => setTwinConsent(e.target.checked)} className="mt-0.5" /><span>I confirm I have explicit permission from the person depicted to create and use this digital twin. I will not use it to mislead viewers or impersonate someone without consent.</span></label>
          <Button onClick={digitalTwin} disabled={busy || !twinConsent} className="w-full" data-testid="digital-twin">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Mic className="mr-2 h-4 w-4" />} Build Digital Twin
          </Button>
          <ResultView data={twinRes} kind="video" />
        </div>
      </Section>
    </div>
  );
}

/* ─── Video Tools ──────────────────────────────────────────────────────────── */

function VideoTools() {
  const [topic, setTopic] = useState("");
  const [vstyle, setVstyle] = useState("story");
  const [vscenes, setVscenes] = useState(6);
  const [ttv, setTtv] = useState(null);

  const [img, setImg] = useState(null);
  const [imgPrompt, setImgPrompt] = useState("");
  const [imgDur, setImgDur] = useState(5);
  const [iv, setIv] = useState(null);

  const [vid, setVid] = useState(null);
  const [tlang, setTlang] = useState("hindi");
  const [transcript, setTranscript] = useState("");
  const [refA, setRefA] = useState(null);
  const [vt, setVt] = useState(null);

  const [source, setSource] = useState("upload");
  const [ytUrl, setYtUrl] = useState("");
  const [repTranscript, setRepTranscript] = useState("");
  const [repCount, setRepCount] = useState(5);
  const [rep, setRep] = useState(null);

  const [busy, setBusy] = useState(false);

  const textToVideo = async () => {
    if (topic.trim().length < 3) return toast.error("Enter a topic");
    setBusy(true); setTtv({ status: "scripting" });
    try {
      const { data } = await api.post("/video-tools/text-to-video", { topic: topic.trim(), style: vstyle, scenes: vscenes, language: "hinglish" });
      await pollUntilDone("/video-tools/project", data.project_id, setTtv);
    } catch (e) { toast.error(e?.response?.data?.detail || "Text-to-Video failed"); }
    finally { setBusy(false); }
  };
  const imageToVideo = async () => {
    if (!img || imgPrompt.trim().length < 3) return toast.error("Need image & prompt");
    setBusy(true); setIv({ status: "queued" });
    try {
      const fd = new FormData(); fd.append("image", img); fd.append("prompt", imgPrompt); fd.append("duration", String(imgDur));
      const { data } = await api.post("/video-tools/image-to-video", fd);
      await pollUntilDone("/video-tools/job", data.job_id, setIv);
    } catch (e) { toast.error(e?.response?.data?.detail || "Image-to-Video failed"); }
    finally { setBusy(false); }
  };
  const videoTranslate = async () => {
    if (!vid) return toast.error("Upload a video");
    setBusy(true); setVt({ status: "queued" });
    try {
      const fd = new FormData(); fd.append("video", vid); fd.append("target_lang", tlang); fd.append("transcript", transcript);
      if (refA) fd.append("reference_audio", refA);
      const { data } = await api.post("/video-tools/video-translate", fd);
      await pollUntilDone("/video-tools/job", data.job_id, setVt);
    } catch (e) { toast.error(e?.response?.data?.detail || "Video translate failed"); }
    finally { setBusy(false); }
  };
  const repurpose = async () => {
    if (source === "youtube" && !ytUrl.trim()) return toast.error("Enter a YouTube URL");
    if (source === "upload" && repTranscript.trim().length < 10) return toast.error("Paste a transcript");
    setBusy(true); setRep({ status: "analyzing" });
    try {
      const { data } = await api.post("/video-tools/one-tap-repurposing", { source, url: ytUrl || null, transcript: repTranscript, count: repCount });
      await pollUntilDone("/video-tools/project", data.project_id, setRep);
    } catch (e) { toast.error(e?.response?.data?.detail || "Repurposing failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <Section icon={Film} title="Text-to-Video" badge="AI Scenes">
        <div className="space-y-3">
          <label className="text-xs font-medium">Topic</label>
          <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="5 tips for weight loss" data-testid="ttv-topic" />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium">Style</label>
            <select value={vstyle} onChange={(e) => setVstyle(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
              {["story", "meme", "documentary", "ad"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <label className="text-xs font-medium ml-auto">Scenes</label>
            <Input type="number" min={2} max={12} value={vscenes} onChange={(e) => setVscenes(Number(e.target.value) || 6)} className="w-20" />
          </div>
          <Button onClick={textToVideo} disabled={busy} className="w-full" data-testid="ttv-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />} Generate Video
          </Button>
          <ResultView data={ttv} kind="storyboard" />
          {ttv?.storyboard ? <StoryboardTimeline scenes={ttv.storyboard} /> : null}
          {ttv?.final_video_url ? (
            <div className="mt-2">
              <div className="text-xs font-semibold text-[var(--gs-teal)]">Captioned final video</div>
              <AuthenticatedMedia url={ttv.final_video_url} type="video" controls className="mt-1 w-full rounded-lg" />
            </div>
          ) : null}
        </div>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section icon={ImageIcon} title="Image-to-Video" badge="Photo→Clip">
          <div className="space-y-3">
            <FileField label="Photo" accept="image/*" onChange={setImg} file={img} />
            <label className="text-xs font-medium">Motion prompt</label>
            <Input value={imgPrompt} onChange={(e) => setImgPrompt(e.target.value)} placeholder="a person walking on beach" />
            <label className="text-xs font-medium">Duration (s)</label>
            <Input type="number" min={2} max={12} value={imgDur} onChange={(e) => setImgDur(Number(e.target.value) || 5)} className="w-20" />
            <Button onClick={imageToVideo} disabled={busy} className="w-full" data-testid="iv-generate">
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />} Animate
            </Button>
            <ResultView data={iv} kind="video" />
          </div>
        </Section>

        <Section icon={Languages} title="Video Translation + Lip-Sync" badge="Dub">
          <div className="space-y-3">
            <FileField label="Video" accept="video/*" onChange={setVid} file={vid} />
            <FileField label="Voice sample (optional, for dub)" accept="audio/*" onChange={setRefA} file={refA} />
            <label className="text-xs font-medium">Target language</label>
            <select value={tlang} onChange={(e) => setTlang(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
              {["hindi", "tamil", "telugu", "english", "hinglish"].map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
            <label className="text-xs font-medium">Transcript (required)</label>
            <Textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={3} placeholder="Original speech text…" />
            <Button onClick={videoTranslate} disabled={busy} className="w-full" data-testid="vt-generate">
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Languages className="mr-2 h-4 w-4" />} Translate & Dub
            </Button>
            <ResultView data={vt} kind="translate" />
          </div>
        </Section>
      </div>

      <Section icon={Scissors} title="One-Tap Repurposing (Long → Shorts)" badge="USP">
        <div className="space-y-3">
          <label className="text-xs font-medium">Source</label>
          <select value={source} onChange={(e) => setSource(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
            {["upload", "youtube"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          {source === "youtube" ? (
            <Input value={ytUrl} onChange={(e) => setYtUrl(e.target.value)} placeholder="https://youtube.com/watch?v=…" />
          ) : (
            <Textarea value={repTranscript} onChange={(e) => setRepTranscript(e.target.value)} rows={4} placeholder="Paste the long video transcript…" />
          )}
          <label className="text-xs font-medium">Shorts count</label>
          <Input type="number" min={1} max={10} value={repCount} onChange={(e) => setRepCount(Number(e.target.value) || 5)} className="w-20" />
          <Button onClick={repurpose} disabled={busy} className="w-full" data-testid="rep-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Scissors className="mr-2 h-4 w-4" />} Find Best Moments
          </Button>
          <ResultView data={rep} kind="shorts" />
        </div>
      </Section>
    </div>
  );
}

/* ─── Social & Agents ──────────────────────────────────────────────────────── */

function SocialAgents() {
  const [platform, setPlatform] = useState("youtube");
  const [videoUrl, setVideoUrl] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [social, setSocial] = useState(null);
  const [busy, setBusy] = useState(false);

  const [comment, setComment] = useState("");
  const [ctx, setCtx] = useState("");
  const [reply, setReply] = useState(null);

  const publish = async () => {
    if (!videoUrl.trim()) return toast.error("Video URL required");
    setBusy(true); setSocial(null);
    try {
      const { data } = await api.post("/video-tools/social-publish", { platform, video_url: videoUrl, title, description: desc, tags: [] });
      setSocial(data);
      if (!data.configured) toast.warning(data.message);
      else toast.success("Queued for publishing");
    } catch (e) { toast.error(e?.response?.data?.detail || "Publish failed"); }
    finally { setBusy(false); }
  };
  const replyGen = async () => {
    if (comment.trim().length < 2) return toast.error("Enter a comment");
    setBusy(true); setReply(null);
    try {
      const { data } = await api.post("/video-tools/influencer-reply", { platform, comment_text: comment, context: ctx });
      setReply(data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Reply failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Section icon={Upload} title="One-Click Social Distribution" badge="Publish">
        <div className="space-y-3">
          <label className="text-xs font-medium">Platform</label>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
            {["youtube", "instagram", "facebook"].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <label className="text-xs font-medium">Video URL</label>
          <Input value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder="https://…/video.mp4" data-testid="social-url" />
          <label className="text-xs font-medium">Title</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          <label className="text-xs font-medium">Description</label>
          <Textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={2} />
          <Button onClick={publish} disabled={busy} className="w-full" data-testid="social-publish">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />} Publish
          </Button>
          <ResultView data={social} kind="social" />
        </div>
      </Section>

      <Section icon={Bot} title="AI Influencer Agent" badge="Auto-Reply">
        <div className="space-y-3">
          <label className="text-xs font-medium">Comment</label>
          <Textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={3} placeholder="A follower's comment…" data-testid="reply-comment" />
          <label className="text-xs font-medium">Context (optional)</label>
          <Input value={ctx} onChange={(e) => setCtx(e.target.value)} placeholder="video topic, brand tone…" />
          <Button onClick={replyGen} disabled={busy} className="w-full" data-testid="reply-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />} Generate Reply
          </Button>
          <ResultView data={reply} kind="reply" />
        </div>
      </Section>
    </div>
  );
}

/* ─── Growth tools (Phase 3) ──────────────────────────────────────────────── */

function GrowthTools() {
  const [busy, setBusy] = useState(false);

  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [thumbs, setThumbs] = useState(null);

  const [script, setScript] = useState("");
  const [brand, setBrand] = useState("");
  const [product, setProduct] = useState("");
  const [sponsor, setSponsor] = useState(null);

  const [dubText, setDubText] = useState("");
  const [dubLangs, setDubLangs] = useState("tamil, telugu, marathi, bengali");
  const [dubs, setDubs] = useState(null);

  const [comments, setComments] = useState("");
  const [cTopic, setCTopic] = useState("");
  const [idea, setIdea] = useState(null);

  const [fTopic, setFTopic] = useState("");
  const [funnel, setFunnel] = useState(null);

  const [mGoal, setMGoal] = useState("");
  const [mNiche, setMNiche] = useState("");
  const [mentor, setMentor] = useState(null);

  const [iTopic, setITopic] = useState("");
  const [iGenre, setIGenre] = useState("thriller");
  const [interactive, setInteractive] = useState(null);

  const [twinSamples, setTwinSamples] = useState("");
  const [twinTopic, setTwinTopic] = useState("");
  const [twin, setTwin] = useState(null);

  const [calNiche, setCalNiche] = useState("");
  const [calGoal, setCalGoal] = useState("grow audience");
  const [calFreq, setCalFreq] = useState(3);
  const [calDays, setCalDays] = useState(30);
  const [calendar, setCalendar] = useState(null);

  const genThumbs = async () => {
    if (topic.trim().length < 4) return toast.error("Enter a topic");
    setBusy(true); setThumbs(null);
    try {
      const { data } = await api.post("/creator/thumbnail", { topic: topic.trim(), count });
      setThumbs(data);
      toast.success(`Generated ${data.variants.length} thumbnails`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Thumbnail generation failed"); }
    finally { setBusy(false); }
  };
  const genSponsor = async () => {
    if (script.trim().length < 20) return toast.error("Paste the script (min 20 chars)");
    setBusy(true); setSponsor(null);
    try {
      const { data } = await api.post("/creator/sponsorship", { script: script.trim(), brand: brand.trim() || undefined, product: product.trim() || undefined });
      setSponsor(data.data);
      toast.success("Placement plan ready");
    } catch (e) { toast.error(e?.response?.data?.detail || "Sponsorship finder failed"); }
    finally { setBusy(false); }
  };
  const genDub = async () => {
    if (dubText.trim().length < 10) return toast.error("Enter the text to dub");
    setBusy(true); setDubs(null);
    try {
      const langs = dubLangs.split(",").map((s) => s.trim()).filter(Boolean);
      const { data } = await api.post("/creator/dub", { text: dubText.trim(), languages: langs });
      setDubs(data.tracks);
      toast.success(`Dubbed into ${data.tracks.length} languages`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Dubbing failed"); }
    finally { setBusy(false); }
  };
  const genIdea = async () => {
    if (comments.trim().length < 5) return toast.error("Paste a few comments");
    setBusy(true); setIdea(null);
    try {
      const { data } = await api.post("/creator/comment-ideas", { comments: comments.trim(), topic: cTopic.trim() || undefined });
      setIdea(data.data);
      toast.success("Content idea ready");
    } catch (e) { toast.error(e?.response?.data?.detail || "Idea generation failed"); }
    finally { setBusy(false); }
  };
  const genFunnel = async () => {
    if (fTopic.trim().length < 4) return toast.error("Enter a topic");
    setBusy(true); setFunnel(null);
    try {
      const { data } = await api.post("/creator/funnel", { topic: fTopic.trim() });
      setFunnel(data.data);
      toast.success("Funnel mapped");
    } catch (e) { toast.error(e?.response?.data?.detail || "Funnel generation failed"); }
    finally { setBusy(false); }
  };
  const genMentor = async () => {
    if (mGoal.trim().length < 4) return toast.error("Enter your goal");
    setBusy(true); setMentor(null);
    try {
      const { data } = await api.post("/creator/mentor", { goal: mGoal.trim(), niche: mNiche.trim() });
      setMentor(data.data);
      toast.success("Mentor plan ready");
    } catch (e) { toast.error(e?.response?.data?.detail || "Mentor failed"); }
    finally { setBusy(false); }
  };
  const genInteractive = async () => {
    if (iTopic.trim().length < 4) return toast.error("Enter a topic");
    setBusy(true); setInteractive(null);
    try {
      const { data } = await api.post("/creator/interactive", { topic: iTopic.trim(), genre: iGenre });
      setInteractive(data.data);
      toast.success("Story built");
    } catch (e) { toast.error(e?.response?.data?.detail || "Story generation failed"); }
    finally { setBusy(false); }
  };
  const genTwin = async () => {
    const samples = twinSamples.split("\n").map((s) => s.trim()).filter((s) => s.length > 20);
    if (samples.length < 1) return toast.error("Paste at least one past script (min 20 chars each)");
    if (twinTopic.trim().length < 4) return toast.error("Enter a new topic");
    setBusy(true); setTwin(null);
    try {
      const { data } = await api.post("/creator/digital-twin", { samples, topic: twinTopic.trim() });
      setTwin(data.data);
      toast.success("Twin trained");
    } catch (e) { toast.error(e?.response?.data?.detail || "Digital twin failed"); }
    finally { setBusy(false); }
  };
  const genCalendar = async () => {
    if (calNiche.trim().length < 3) return toast.error("Enter a niche");
    setBusy(true); setCalendar(null);
    try {
      const { data } = await api.post("/creator/calendar", { niche: calNiche.trim(), goal: calGoal.trim(), frequency: calFreq, days: calDays });
      setCalendar(data.data);
      toast.success("Calendar ready");
    } catch (e) { toast.error(e?.response?.data?.detail || "Calendar generation failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <Section icon={ImageIcon} title="Thumbnail Generator + CTR Predictor" badge="Clicks">
        <div className="space-y-3">
          <label className="text-xs font-medium">Video topic / title</label>
          <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="10-minute workout you can do at home" data-testid="thumb-topic" />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium">Variants</label>
            <Input type="number" min={2} max={8} value={count} onChange={(e) => setCount(Number(e.target.value) || 5)} className="w-20" />
          </div>
          <Button onClick={genThumbs} disabled={busy} className="w-full" data-testid="thumb-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImageIcon className="mr-2 h-4 w-4" />} Generate Thumbnails
          </Button>
          {thumbs?.variants?.length ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {thumbs.variants.map((v, i) => (
                <Card key={i} className="overflow-hidden">
                  {v.image_url ? (
                    <AuthenticatedMedia url={v.image_url} type="image" alt={v.headline} className="w-full h-32 object-cover" />
                  ) : (
                    <div className="h-32 bg-[var(--gs-surface-2)] grid place-items-center text-center px-2 text-sm font-semibold">{v.headline}</div>
                  )}
                  <div className="p-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--gs-teal)]">CTR {v.ctr_score}%</span>
                      {v.image_url ? <button type="button" onClick={() => downloadAuthenticatedMedia(v.image_url, `getszy-thumbnail-${i + 1}.png`).catch(() => toast.error("Download failed"))} className="text-xs underline">Download</button> : null}
                    </div>
                    <p className="text-xs text-[var(--gs-muted)]">{v.reason}</p>
                  </div>
                </Card>
              ))}
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={Target} title="Sponsorship Placement" badge="Deals">
        <div className="space-y-3">
          <label className="text-xs font-medium">Your script / transcript</label>
          <Textarea value={script} onChange={(e) => setScript(e.target.value)} rows={4} placeholder="Paste the full video script…" data-testid="sponsor-script" />
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="text-xs font-medium">Brand (optional)</label><Input value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Nike" /></div>
            <div><label className="text-xs font-medium">Product (optional)</label><Input value={product} onChange={(e) => setProduct(e.target.value)} placeholder="running shoes" /></div>
          </div>
          <Button onClick={genSponsor} disabled={busy} className="w-full" data-testid="sponsor-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Target className="mr-2 h-4 w-4" />} Find Placement
          </Button>
          {sponsor ? (
            <div className="space-y-2 rounded-lg border p-3">
              <div className="text-xs font-semibold text-[var(--gs-teal)]">Insert at: {sponsor.insertion_point}</div>
              <div className="text-sm whitespace-pre-wrap">{sponsor.integrated_script}</div>
              <div className="text-xs font-semibold">CTA: {sponsor.cta}</div>
              <div className="text-xs text-[var(--gs-muted)]">{sponsor.rationale}</div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={Languages} title="Multi-language Dubbing" badge="Reach">
        <div className="space-y-3">
          <label className="text-xs font-medium">Text to dub</label>
          <Textarea value={dubText} onChange={(e) => setDubText(e.target.value)} rows={3} placeholder="Your Hindi/English lines…" data-testid="dub-text" />
          <label className="text-xs font-medium">Languages (comma-separated)</label>
          <Input value={dubLangs} onChange={(e) => setDubLangs(e.target.value)} placeholder="tamil, telugu, marathi, bengali" />
          <Button onClick={genDub} disabled={busy} className="w-full" data-testid="dub-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Languages className="mr-2 h-4 w-4" />} Dub Now
          </Button>
          {dubs?.length ? (
            <div className="space-y-3">
              {dubs.map((t, i) => (
                <div key={i} className="rounded-lg border p-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--gs-teal)] capitalize">{t.language}</span>
                    <span className="text-xs text-[var(--gs-muted)]">voice: {t.voice}</span>
                  </div>
                  {t.audio_url ? (
                    <AuthenticatedMedia url={t.audio_url} type="audio" controls className="w-full" />
                  ) : <div className="text-xs text-[var(--gs-muted)]">{t.note || "audio unavailable"}</div>}
                  <div className="text-sm whitespace-pre-wrap">{t.text}</div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={MessageSquare} title="Comment → Content Idea" badge="Never dry">
        <div className="space-y-3">
          <label className="text-xs font-medium">Audience comments</label>
          <Textarea value={comments} onChange={(e) => setComments(e.target.value)} rows={4} placeholder="Paste follower comments…" data-testid="idea-comments" />
          <label className="text-xs font-medium">Channel topic (optional)</label>
          <Input value={cTopic} onChange={(e) => setCTopic(e.target.value)} placeholder="fitness" />
          <Button onClick={genIdea} disabled={busy} className="w-full" data-testid="idea-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <MessageSquare className="mr-2 h-4 w-4" />} Get Next Video Idea
          </Button>
          {idea ? (
            <div className="space-y-2 rounded-lg border p-3">
              <div className="text-sm">{idea.idea}</div>
              <div className="text-xs font-semibold text-[var(--gs-teal)]">{idea.title}</div>
              <div className="text-xs">Angle: {idea.angle}</div>
              <div className="text-xs text-[var(--gs-muted)] whitespace-pre-wrap">{idea.script_outline}</div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={Layers} title="Content Funnel (Topic → Omnipresence)" badge="Reach">
        <div className="space-y-3">
          <label className="text-xs font-medium">Topic</label>
          <Input value={fTopic} onChange={(e) => setFTopic(e.target.value)} placeholder="budget travel India" data-testid="funnel-topic" />
          <Button onClick={genFunnel} disabled={busy} className="w-full" data-testid="funnel-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Layers className="mr-2 h-4 w-4" />} Map Funnel
          </Button>
          {funnel ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border p-3 space-y-1">
                <div className="text-xs font-semibold text-[var(--gs-teal)]">YouTube</div>
                <div className="text-sm whitespace-pre-wrap">{funnel.youtube}</div>
              </div>
              <div className="rounded-lg border p-3 space-y-1">
                <div className="text-xs font-semibold text-[var(--gs-teal)]">Reels / Shorts</div>
                <ul className="list-disc pl-4 text-sm space-y-1">{funnel.reels?.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
              <div className="rounded-lg border p-3 space-y-1">
                <div className="text-xs font-semibold text-[var(--gs-teal)]">X / Thread</div>
                <ol className="list-decimal pl-4 text-sm space-y-1">{funnel.thread?.map((t, i) => <li key={i}>{t}</li>)}</ol>
              </div>
              <div className="rounded-lg border p-3 space-y-1">
                <div className="text-xs font-semibold text-[var(--gs-teal)]">LinkedIn</div>
                <div className="text-sm whitespace-pre-wrap">{funnel.linkedin}</div>
              </div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={Bot} title="AI Growth Mentor" badge="Coach">
        <div className="space-y-3">
          <label className="text-xs font-medium">Your goal</label>
          <Input value={mGoal} onChange={(e) => setMGoal(e.target.value)} placeholder="Reach 100k subs in 6 months" data-testid="mentor-goal" />
          <label className="text-xs font-medium">Niche (optional)</label>
          <Input value={mNiche} onChange={(e) => setMNiche(e.target.value)} placeholder="tech reviews" />
          <Button onClick={genMentor} disabled={busy} className="w-full" data-testid="mentor-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />} Get My Plan
          </Button>
          {mentor ? (
            <div className="space-y-3 rounded-lg border p-3">
              <div className="text-sm whitespace-pre-wrap">{mentor.audit}</div>
              <div>
                <div className="text-xs font-semibold text-[var(--gs-teal)]">Top 3 mistakes</div>
                <ul className="list-disc pl-4 text-sm">{mentor.top3_mistakes?.map((m, i) => <li key={i}>{m}</li>)}</ul>
              </div>
              <div>
                <div className="text-xs font-semibold text-[var(--gs-teal)]">30-day plan</div>
                <ol className="list-decimal pl-4 text-sm space-y-1">{mentor.plan_30d?.map((p, i) => <li key={i}>{p}</li>)}</ol>
              </div>
              <div>
                <div className="text-xs font-semibold text-[var(--gs-teal)]">First 3 videos</div>
                <ul className="list-disc pl-4 text-sm space-y-1">{mentor.first_3_videos?.map((v, i) => <li key={i}><span className="font-medium">{v.title}</span> — {v.why_it_wins}</li>)}</ul>
              </div>
              <div className="text-xs whitespace-pre-wrap">💰 {mentor.monetization}</div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={Sparkles} title="Interactive Storytelling" badge="Choose-your-path">
        <div className="space-y-3">
          <label className="text-xs font-medium">Story topic</label>
          <Input value={iTopic} onChange={(e) => setITopic(e.target.value)} placeholder="A detective in a haunted Mumbai metro" data-testid="interactive-topic" />
          <div className="flex items-center gap-3">
            <label className="text-xs font-medium">Genre</label>
            <select value={iGenre} onChange={(e) => setIGenre(e.target.value)} className="rounded-lg border bg-white px-2 py-1 text-sm">
              {["thriller", "romance", "sci-fi", "horror", "comedy", "mystery"].map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <Button onClick={genInteractive} disabled={busy} className="w-full" data-testid="interactive-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />} Build Story
          </Button>
          {interactive ? (
            <div className="space-y-3 rounded-lg border p-3">
              <div className="text-sm whitespace-pre-wrap">{interactive.premise}</div>
              <div className="text-xs font-semibold text-[var(--gs-teal)]">Episodes</div>
              <div className="text-sm">{interactive.episode_plan?.join(" → ")}</div>
              <div className="rounded-lg bg-[var(--gs-surface-2)] p-2">
                <div className="text-xs font-semibold">Scene 1</div>
                <div className="text-sm whitespace-pre-wrap">{interactive.scene_1?.narrative}</div>
                <div className="mt-2 space-y-1">
                  {interactive.scene_1?.choices?.map((c, i) => (
                    <div key={i} className="text-sm"><span className="font-medium">{c.label}</span>: {c.outcome} <span className="text-[var(--gs-muted)]">({c.next})</span></div>
                  ))}
                </div>
              </div>
              <div className="text-xs whitespace-pre-wrap">{interactive.scene_2?.narrative_outline || interactive.scene_2?.narrative}</div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={User} title="Digital Twin (Clone Your Style)" badge="AI You">
        <div className="space-y-3">
          <label className="text-xs font-medium">Your past scripts (one per line, min 1)</label>
          <Textarea value={twinSamples} onChange={(e) => setTwinSamples(e.target.value)} rows={5} placeholder={"Paste a previous video script…\nanother transcript…"} data-testid="twin-samples" />
          <label className="text-xs font-medium">New topic to write in your voice</label>
          <Input value={twinTopic} onChange={(e) => setTwinTopic(e.target.value)} placeholder="best budget smartphones 2026" data-testid="twin-topic" />
          <Button onClick={genTwin} disabled={busy} className="w-full" data-testid="twin-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <User className="mr-2 h-4 w-4" />} Train & Generate
          </Button>
          {twin ? (
            <div className="space-y-3 rounded-lg border p-3">
              <div>
                <div className="text-xs font-semibold text-[var(--gs-teal)]">Style DNA</div>
                <div className="text-sm">Voice: {twin.style_profile?.voice}</div>
                <div className="text-xs">Pacing: {twin.style_profile?.pacing}</div>
                <div className="text-xs">Vocabulary: {twin.style_profile?.vocabulary}</div>
                <div className="text-xs">Structure: {twin.style_profile?.structure}</div>
                <div className="text-xs">Rules: {twin.style_profile?.do_and_dont}</div>
                <div className="text-xs">Hooks: {(twin.style_profile?.hooks || []).join(" | ")}</div>
              </div>
              <div className="rounded-lg bg-[var(--gs-surface-2)] p-2">
                <div className="text-sm font-medium">{twin.generated?.title}</div>
                <div className="text-xs text-[var(--gs-teal)]">Hook: {twin.generated?.hook}</div>
                <div className="mt-1 text-sm whitespace-pre-wrap">{twin.generated?.script}</div>
                <div className="text-xs mt-1">CTA: {twin.generated?.cta}</div>
              </div>
            </div>
          ) : null}
        </div>
      </Section>

      <Section icon={ListOrdered} title="Content Calendar" badge="Plan">
        <div className="space-y-3">
          <label className="text-xs font-medium">Niche</label>
          <Input value={calNiche} onChange={(e) => setCalNiche(e.target.value)} placeholder="personal finance" data-testid="cal-niche" />
          <label className="text-xs font-medium">Goal</label>
          <Input value={calGoal} onChange={(e) => setCalGoal(e.target.value)} placeholder="grow audience" />
          <div className="flex items-center gap-3">
            <div><label className="text-xs font-medium">Posts/week</label><Input type="number" min={1} max={14} value={calFreq} onChange={(e) => setCalFreq(Number(e.target.value) || 3)} className="w-20" /></div>
            <div><label className="text-xs font-medium">Days</label><Input type="number" min={7} max={90} value={calDays} onChange={(e) => setCalDays(Number(e.target.value) || 30)} className="w-20" /></div>
          </div>
          <Button onClick={genCalendar} disabled={busy} className="w-full" data-testid="cal-generate">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ListOrdered className="mr-2 h-4 w-4" />} Build Calendar
          </Button>
          {calendar ? (
            <div className="space-y-2 rounded-lg border p-3">
              <div className="text-xs font-semibold text-[var(--gs-teal)]">Theme: {calendar.theme}</div>
              <div className="space-y-2 max-h-80 overflow-auto">
                {calendar.entries?.map((e, i) => (
                  <div key={i} className="rounded-lg border p-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold">{e.date} · {e.platform}</span>
                      <span className="text-[var(--gs-muted)]">{e.best_time}</span>
                    </div>
                    <div className="text-sm font-medium">{e.title}</div>
                    <div className="text-xs">{e.format} — {e.hook}</div>
                    <div className="text-xs text-[var(--gs-teal)]">CTR tip: {e.ctr_tip}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </Section>
    </div>
  );
}

/* ─── Page shell ───────────────────────────────────────────────────────────── */

const TABS = [
  { id: "hooks", label: "Hooks & Memes" },
  { id: "avatars", label: "Avatars" },
  { id: "video", label: "Video Tools" },
  { id: "social", label: "Social & Agents" },
  { id: "growth", label: "Growth" },
];

export default function CreatorStudio() {
  const [tab, setTab] = useState("hooks");
  return (
    <DashboardPageFrame
      className="space-y-6"
      eyebrow="Creator OS"
      title="Create the next piece of content with a clear outcome"
      description="Plan hooks, generate creator assets, turn audience signals into ideas, and grow your channel with Hinglish-native workflows."
      icon={Clapperboard}
      metrics={[{ label: "creator workflows", value: TABS.length }, { label: "active workspace", value: TABS.find((item) => item.id === tab)?.label }]}
      hint="Choose the stage of your content workflow first, then complete one focused creation task at a time."
    >

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium border ${tab === t.id ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "border-[var(--gs-border)] text-[var(--gs-muted)]"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "hooks" && <HooksMemes />}
      {tab === "avatars" && <Avatars />}
      {tab === "video" && <VideoTools />}
      {tab === "social" && <SocialAgents />}
      {tab === "growth" && <GrowthTools />}
    </DashboardPageFrame>
  );
}
