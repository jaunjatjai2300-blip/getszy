import { useState, useEffect, useCallback } from "react";
import {
  Wand2, Sparkles, Scissors, Layers, Image as ImageIcon, Download, Loader2,
  RefreshCw, Upload, Film, AlertTriangle, CheckCircle2, Palette, Type,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import PageState from "@/components/dashboard/PageState";

/* Pull an authenticated blob (image/video) and expose it via an object URL.
   Mirrors the existing AuthenticatedMedia pattern used elsewhere in the app so
   private media never leaks through an unauthenticated URL. */
function AuthMedia({ url, type, className = "" }) {
  const [src, setSrc] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    let obj;
    setSrc(null);
    setError(false);
    if (!url) return undefined;
    api.get(url, { responseType: "blob" })
      .then(({ data }) => { obj = URL.createObjectURL(data); if (active) setSrc(obj); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; if (obj) URL.revokeObjectURL(obj); };
  }, [url]);
  if (error) return <div className="text-xs text-rose-600">Protected media could not be loaded.</div>;
  if (!src) return <div className="text-xs text-[var(--gs-muted)]">Loading secure preview…</div>;
  if (type === "image") return <img src={src} alt="Design preview" className={className} />;
  return <video src={src} controls className={className} />;
}

function downloadDataUrl(url, name) {
  const a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
}

/* ─────────────────────────────── Design ─────────────────────────────── */
function DesignPanel() {
  const [formats, setFormats] = useState([]);
  const [models, setModels] = useState([]);
  const [fmt, setFmt] = useState("ig_post");
  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [cta, setCta] = useState("");
  const [primary, setPrimary] = useState("");
  const [bgFile, setBgFile] = useState(null);
  const [logoFile, setLogoFile] = useState(null);
  const [modelId, setModelId] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/media-suite/design/formats").then((r) => setFormats(r.data.formats || [])).catch(() => {});
    api.get("/media-suite/models").then((r) => {
      const imgs = (r.data.models?.image || []).filter((m) => m.free);
      setModels(imgs);
    }).catch(() => {});
  }, []);

  const generate = async () => {
    if (!bgFile && prompt.trim().length < 3) {
      toast.error("Background image chahiye ya generation prompt (min 3 chars)");
      return;
    }
    setBusy(true); setError(null); setResult(null);
    try {
      const fd = new FormData();
      fd.append("fmt", fmt);
      fd.append("title", title);
      fd.append("subtitle", subtitle);
      fd.append("cta", cta);
      fd.append("prompt", prompt);
      fd.append("model_id", modelId || "");
      fd.append("primary_color", primary);
      if (bgFile) fd.append("background", bgFile);
      if (logoFile) fd.append("logo", logoFile);
      const { data } = await api.post("/media-suite/design/compose", fd);
      setResult(data);
      toast.success("Design ready");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Design generation failed. Try a different background or prompt.";
      setError(msg);
      toast.error("Generation failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Palette className="h-5 w-5 text-[var(--gs-teal)]" />
          <h3 className="font-display text-lg">Design Agent</h3>
          <Badge className="ml-auto bg-[var(--gs-teal)]/15 text-[var(--gs-teal)]">Free-only</Badge>
        </div>
        <div className="space-y-3">
          <label className="text-xs font-medium">Platform format</label>
          <div className="flex flex-wrap gap-1.5">
            {formats.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setFmt(f.id)}
                className={`text-xs px-2.5 py-1 rounded-full border ${fmt === f.id ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white"}`}
                style={{ borderColor: fmt === f.id ? "var(--gs-teal)" : "var(--gs-border)" }}
                data-testid={`ms-fmt-${f.id}`}
              >
                {f.label} · {f.width}×{f.height}
              </button>
            ))}
          </div>

          <label className="text-xs font-medium">Background prompt (optional if you upload a background)</label>
          <Input value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="a calm gradient with soft light" data-testid="ms-design-prompt" />

          <label className="text-xs font-medium">Free model (optional)</label>
          <select value={modelId} onChange={(e) => setModelId(e.target.value)} className="rounded-lg border bg-white px-2 py-1.5 text-sm" data-testid="ms-design-model">
            <option value="">Auto (free)</option>
            {models.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium">Title</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Launch Day" data-testid="ms-design-title" />
            </div>
            <div>
              <label className="text-xs font-medium">Subtitle</label>
              <Input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} placeholder="Join the movement" data-testid="ms-design-subtitle" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium">CTA</label>
              <Input value={cta} onChange={(e) => setCta(e.target.value)} placeholder="Get Started" data-testid="ms-design-cta" />
            </div>
            <div>
              <label className="text-xs font-medium">Brand color (optional)</label>
              <Input value={primary} onChange={(e) => setPrimary(e.target.value)} placeholder="#0DC8B3" data-testid="ms-design-color" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-xs font-medium">Background image (optional)</label>
              <input type="file" accept="image/*" onChange={(e) => setBgFile(e.target.files?.[0] || null)} className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--gs-teal)] file:px-3 file:py-1 file:text-white" data-testid="ms-design-bg" />
            </div>
            <div>
              <label className="text-xs font-medium">Logo (optional)</label>
              <input type="file" accept="image/*" onChange={(e) => setLogoFile(e.target.files?.[0] || null)} className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--gs-teal)] file:px-3 file:py-1 file:text-white" data-testid="ms-design-logo" />
            </div>
          </div>

          <Button onClick={generate} disabled={busy} className="w-full bg-[var(--gs-teal)] gap-2" data-testid="ms-design-generate">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} Compose Design
          </Button>
          {error && <div className="rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 p-3" data-testid="ms-design-error">{error}</div>}
        </div>
      </Card>

      <Card className="p-5">
        <div className="text-sm font-semibold mb-3">Preview</div>
        {busy && <PageState compact kind="loading" title="Composing your design…" />}
        {!busy && !result && !error && (
          <PageState compact kind="empty" title="No design yet" message="Pick a format, add your copy, and compose. Your graphic appears here." />
        )}
        {result && (
          <div className="space-y-3" data-testid="ms-design-result">
            <div className="rounded-lg overflow-hidden border bg-black/5" style={{ borderColor: "var(--gs-border)" }}>
              <img src={result.image} alt="Generated design" className="w-full" />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="text-xs">{result.format}</Badge>
              <Badge variant="outline" className="text-xs">{result.width}×{result.height}</Badge>
              <Badge variant="outline" className="text-xs">provider: {result.provider}</Badge>
              <Button size="sm" className="ml-auto gap-1 bg-[var(--gs-teal)]" onClick={() => downloadDataUrl(result.image, `getszy-${result.format}.png`)} data-testid="ms-design-download">
                <Download className="h-3.5 w-3.5" /> Download PNG
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ─────────────────────────────── Shorts ────────────────────────────── */
function ShortsPanel() {
  const [source, setSource] = useState("upload");
  const [file, setFile] = useState(null);
  const [yt, setYt] = useState("");
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState("sentence");
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const backend = process.env.REACT_APP_BACKEND_URL || "";

  const poll = useCallback(async (id) => {
    try {
      const { data } = await api.get(`/media-suite/shorts/${id}`);
      setStatus(data.status);
      setResult(data.result || null);
      if (["completed", "failed"].includes(data.status)) {
        if (data.status === "failed" && data.result?.error) setError(data.result.error);
        return true;
      }
    } catch {
      /* transient */
    }
    return false;
  }, []);

  useEffect(() => {
    if (!jobId) return undefined;
    let active = true;
    const iv = setInterval(async () => {
      const done = await poll(jobId);
      if (done && active) clearInterval(iv);
    }, 3000);
    return () => { active = false; clearInterval(iv); };
  }, [jobId, poll]);

  const generate = async () => {
    if (source === "youtube" && !yt.trim()) { toast.error("Enter a YouTube URL"); return; }
    if (source === "upload" && !file) { toast.error("Upload a video/audio file"); return; }
    setBusy(true); setError(null); setResult(null); setJobId(null); setStatus("queued");
    try {
      const fd = new FormData();
      if (source === "youtube") fd.append("youtube_url", yt.trim());
      else fd.append("file", file);
      fd.append("orientation", "9:16");
      const { data } = await api.post("/media-suite/shorts", fd);
      setJobId(data.job_id);
      toast.success("Shorts engine started — transcribing & captioning…");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Couldn't start shorts generation.";
      setError(msg); toast.error("Start failed");
    } finally { setBusy(false); }
  };

  const retry = () => { setJobId(null); setResult(null); setStatus(null); setError(null); generate(); };

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Scissors className="h-5 w-5 text-[var(--gs-teal)]" />
          <h3 className="font-display text-lg">Shorts / Reel Generator</h3>
          <Badge className="ml-auto bg-[var(--gs-teal)]/15 text-[var(--gs-teal)]">9:16 · captions</Badge>
        </div>
        <div className="space-y-3">
          <label className="text-xs font-medium">Source</label>
          <div className="flex gap-2">
            {[["upload", "Upload file"], ["youtube", "YouTube URL"]].map(([v, l]) => (
              <button key={v} type="button" onClick={() => setSource(v)}
                className={`text-xs px-3 py-1.5 rounded-full border ${source === v ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white"}`}
                style={{ borderColor: source === v ? "var(--gs-teal)" : "var(--gs-border)" }}
                data-testid={`ms-short-src-${v}`}>{l}</button>
            ))}
          </div>

          {source === "upload" ? (
            <div>
              <label className="text-xs font-medium">Video / audio file</label>
              <input type="file" accept="video/*,audio/*" onChange={(e) => setFile(e.target.files?.[0] || null)} className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--gs-teal)] file:px-3 file:py-1 file:text-white" data-testid="ms-short-file" />
            </div>
          ) : (
            <div>
              <label className="text-xs font-medium">YouTube URL</label>
              <Input value={yt} onChange={(e) => setYt(e.target.value)} placeholder="https://youtube.com/watch?v=…" data-testid="ms-short-yt" />
            </div>
          )}

          <div>
            <label className="text-xs font-medium">Topic / context (optional)</label>
            <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="travel vlog highlights" data-testid="ms-short-topic" />
          </div>

          <label className="text-xs font-medium">Caption style</label>
          <select value={style} onChange={(e) => setStyle(e.target.value)} className="rounded-lg border bg-white px-2 py-1.5 text-sm" data-testid="ms-short-style">
            <option value="sentence">Sentence-level (free Whisper)</option>
            <option value="highlight">Highlight words</option>
          </select>

          <Button onClick={generate} disabled={busy || (source === "youtube" ? !yt.trim() : !file)} className="w-full bg-[var(--gs-teal)] gap-2" data-testid="ms-short-generate">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Film className="h-4 w-4" />} Generate Shorts
          </Button>

          {(status === "queued" || status === "processing" || status === "transcribing") && (
            <div className="rounded-lg bg-[var(--gs-teal)]/8 border border-[var(--gs-teal)]/20 p-3 text-sm" data-testid="ms-short-progress">
              <Loader2 className="h-4 w-4 animate-spin inline mr-2" /> Processing… {status}
            </div>
          )}
          {error && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 p-3 flex items-start gap-2" data-testid="ms-short-error">
              <AlertTriangle className="h-4 w-4 mt-0.5" /> {error}
            </div>
          )}
        </div>
      </Card>

      <Card className="p-5">
        <div className="text-sm font-semibold mb-3">Result</div>
        {!jobId && !error && <PageState compact kind="empty" title="No short yet" message="Upload or paste a link, then generate a captioned 9:16 short." />}
        {jobId && result?.output && (
          <div className="space-y-3" data-testid="ms-short-result">
            <AuthMedia url={`/media-suite/shorts/${jobId}/file`} type="video" className="w-full rounded-lg bg-black" />
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="text-xs">{result.orientation || "9:16"}</Badge>
              <Badge variant="outline" className="text-xs">{result.captions?.length || 0} captions</Badge>
              <a href={`${backend}/api/media-suite/shorts/${jobId}/file`} className="text-xs px-3 py-1.5 rounded-lg bg-[var(--gs-teal)] text-white ml-auto flex items-center gap-1" data-testid="ms-short-download">
                <Download className="h-3.5 w-3.5" /> Download MP4
              </a>
              <Button size="sm" variant="outline" onClick={retry} className="gap-1" data-testid="ms-short-retry">
                <RefreshCw className="h-3.5 w-3.5" /> Retry
              </Button>
            </div>
          </div>
        )}
        {jobId && status === "failed" && !result?.output && (
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={retry} className="gap-1" data-testid="ms-short-retry-failed"><RefreshCw className="h-3.5 w-3.5" /> Retry</Button>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ────────────────────────────── Workflow ───────────────────────────── */
const EXAMPLE_DAG = JSON.stringify(
  {
    nodes: [
      { id: "art", type: "image", params: { prompt: "a neon city skyline", model: "FLUX.1-schnell" } },
      { id: "voice", type: "tts", params: { text: "Welcome to the future", voice: "en-US-AriaNeural" } },
    ],
    edges: [{ from: "art", to: "voice", as: "image" }],
  },
  null,
  2,
);

function WorkflowPanel() {
  const [name, setName] = useState("My first workflow");
  const [json, setJson] = useState(EXAMPLE_DAG);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [outputs, setOutputs] = useState(null);
  const [error, setError] = useState(null);

  const poll = useCallback(async (id) => {
    try {
      const { data } = await api.get(`/media-suite/workflow/${id}`);
      setStatus(data.status);
      setOutputs(data.outputs || null);
      if (["completed", "failed"].includes(data.status)) {
        if (data.status === "failed") setError(data.error || "Workflow failed");
        return true;
      }
    } catch { /* transient */ }
    return false;
  }, []);

  useEffect(() => {
    if (!jobId) return undefined;
    let active = true;
    const iv = setInterval(async () => {
      const done = await poll(jobId);
      if (done && active) clearInterval(iv);
    }, 2500);
    return () => { active = false; clearInterval(iv); };
  }, [jobId, poll]);

  const run = async () => {
    let graph;
    try { graph = JSON.parse(json); }
    catch { toast.error("Invalid JSON graph"); return; }
    if (!graph.nodes || !Array.isArray(graph.nodes)) { toast.error("Graph needs a 'nodes' array"); return; }
    try {
      setBusy(true); setError(null); setOutputs(null);
      const { data } = await api.post("/media-suite/workflow/run", { graph });
      setJobId(data.job_id);
      toast.success("Workflow queued");
    } catch (e) {
      const msg = e?.response?.data?.detail || "Failed to start workflow.";
      setError(msg); toast.error("Start failed");
    } finally { setBusy(false); }
  };

  const retry = () => { setJobId(null); setStatus(null); setOutputs(null); setError(null); run(); };

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Layers className="h-5 w-5 text-[var(--gs-teal)]" />
          <h3 className="font-display text-lg">Vibe Workflow</h3>
          <Badge className="ml-auto bg-[var(--gs-teal)]/15 text-[var(--gs-teal)]">JSON DAG</Badge>
        </div>
        <div className="space-y-3">
          <label className="text-xs font-medium">Workflow name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="ms-wf-name" />
          <label className="text-xs font-medium">Graph (nodes + edges)</label>
          <Textarea value={json} onChange={(e) => setJson(e.target.value)} rows={12} className="text-xs font-mono" data-testid="ms-wf-json" />
          <p className="text-[11px] text-[var(--gs-muted)]">Node types: image · tts · text · delay · shorts. Connect nodes with edges (from → to, optional "as" name).</p>
          <Button onClick={run} disabled={busy} className="w-full bg-[var(--gs-teal)] gap-2" data-testid="ms-wf-run">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayIcon />} Run Workflow
          </Button>
          {error && (
            <div className="rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 p-3 flex items-start gap-2" data-testid="ms-wf-error">
              <AlertTriangle className="h-4 w-4 mt-0.5" /> {error}
            </div>
          )}
        </div>
      </Card>

      <Card className="p-5">
        <div className="text-sm font-semibold mb-3">Execution</div>
        {!jobId && !error && <PageState compact kind="empty" title="No run yet" message="Define a graph and run it. Status and outputs appear here." />}
        {jobId && (
          <div className="space-y-3" data-testid="ms-wf-result">
            <div className="flex items-center gap-2">
              <Badge className={status === "completed" ? "bg-emerald-500" : status === "failed" ? "bg-rose-500" : "bg-amber-500"}>
                {status === "completed" ? <CheckCircle2 className="h-3 w-3 mr-1" /> : status === "failed" ? <AlertTriangle className="h-3 w-3 mr-1" /> : <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                {status || "queued"}
              </Badge>
              <Button size="sm" variant="outline" onClick={retry} className="ml-auto gap-1" data-testid="ms-wf-retry"><RefreshCw className="h-3.5 w-3.5" /> Retry</Button>
            </div>
            {outputs && (
              <div className="space-y-2 max-h-[360px] overflow-auto">
                {Object.entries(outputs).map(([nid, out]) => (
                  <div key={nid} className="rounded-lg border p-2" style={{ borderColor: "var(--gs-border)" }}>
                    <div className="text-xs font-semibold text-[var(--gs-teal)] mb-1">#{nid}</div>
                    {out?.image ? (
                      <img
                        src={out.image.startsWith("http") ? out.image : `data:image/png;base64,${out.image}`}
                        alt={`output ${nid}`}
                        className="w-full rounded"
                      />
                    ) : (
                      <pre className="text-[11px] whitespace-pre-wrap text-[var(--gs-muted)]">{JSON.stringify(out, null, 1).slice(0, 600)}</pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
  );
}

/* ─────────────────────────── Media Suite shell ──────────────────────────── */
export default function MediaSuite() {
  const [tab, setTab] = useState("design");
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[var(--gs-teal)]" />
        <h2 className="font-display text-xl">Media Suite</h2>
        <Badge className="bg-[var(--gs-teal)]/15 text-[var(--gs-teal)]">SamurAIGPT · Open-Generative-AI</Badge>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="justify-start bg-[var(--gs-surface-2)] p-0.5 h-auto flex-wrap">
          {[
            { v: "design", label: "Design", Icon: ImageIcon },
            { v: "shorts", label: "Shorts / Reels", Icon: Scissors },
            { v: "workflow", label: "Workflow", Icon: Layers },
          ].map((t) => (
            <TabsTrigger key={t.v} value={t.v} className="text-xs gap-1 data-[state=active]:bg-[var(--gs-teal)] data-[state=active]:text-white" data-testid={`ms-tab-${t.v}`}>
              <t.Icon className="h-3 w-3" />{t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="mt-4">
          <TabsContent value="design" className="m-0" data-testid="ms-panel-design"><DesignPanel /></TabsContent>
          <TabsContent value="shorts" className="m-0" data-testid="ms-panel-shorts"><ShortsPanel /></TabsContent>
          <TabsContent value="workflow" className="m-0" data-testid="ms-panel-workflow"><WorkflowPanel /></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
