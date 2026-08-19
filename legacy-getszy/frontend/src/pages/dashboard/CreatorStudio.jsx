import { useState, useEffect } from "react";
import {
  Sparkles, Clapperboard, Flame, ListOrdered, Film, Languages,
  Scissors, Upload, Send, Bot, Image as ImageIcon, Mic, User, Wand2, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import PageState from "@/components/dashboard/PageState";

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
            {s.image_url ? <img src={s.image_url} alt="" className="mt-1 rounded w-32" /> : null}
            {s.clip_url ? <video src={s.clip_url} controls className="mt-1 w-40 rounded" /> : null}
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
    return <video src={data.url} controls className="mt-2 w-full rounded-lg" />;
  }
  if (kind === "translate" && data.translated_text) {
    return (
      <div className="mt-2 space-y-1 text-sm">
        <div><span className="font-semibold">Translated:</span> {data.translated_text}</div>
        {data.dubbed_audio_url ? <audio src={data.dubbed_audio_url} controls className="w-full" /> : null}
        {data.synced_video_url ? <video src={data.synced_video_url} controls className="w-full rounded" /> : null}
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
              {s.image_url ? <img src={s.image_url} alt="" className="h-16 w-full object-cover rounded" /> : <div className="h-16 bg-[var(--gs-surface-2)] rounded" />}
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
              <input type="checkbox" checked={blend} onChange={(e) => setBlend(e.target.checked)} /> Blend live trends
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
  const [busy, setBusy] = useState(false);

  const photoToAvatar = async () => {
    if (!portrait || !voice || script.trim().length < 2) return toast.error("Need photo, voice sample & script");
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
          <Button onClick={photoToAvatar} disabled={busy} className="w-full" data-testid="photo-to-avatar">
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
          <Textarea value={twinScript} onChange={(e) => setTwinScript(e.target.value)} rows={2} placeholder="Your cloned voice will say this." />
          <Button onClick={digitalTwin} disabled={busy} className="w-full" data-testid="digital-twin">
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
              <video src={ttv.final_video_url} controls className="mt-1 w-full rounded-lg" />
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

/* ─── Page shell ───────────────────────────────────────────────────────────── */

const TABS = [
  { id: "hooks", label: "Hooks & Memes" },
  { id: "avatars", label: "Avatars" },
  { id: "video", label: "Video Tools" },
  { id: "social", label: "Social & Agents" },
];

export default function CreatorStudio() {
  const [tab, setTab] = useState("hooks");
  return (
    <div className="space-y-6" data-testid="creator-studio-page">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2">
          <Clapperboard className="h-7 w-7 text-[var(--gs-teal)]" /> Creator Studio
        </h1>
        <p className="mt-1 text-sm text-[var(--gs-muted)]">
          The Viral Engine for YouTubers, Reel creators & faceless channels — cheap, fast, Hinglish-native.
        </p>
      </div>

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
    </div>
  );
}
