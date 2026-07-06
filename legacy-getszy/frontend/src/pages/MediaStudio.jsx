import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Image as ImageIcon, Mic2, Film, RefreshCw, Download, Wand2, Palette, ScanFace, ChevronRight, Lock } from "lucide-react";
import { toast } from "sonner";

const TOOL_ICONS = { image: ImageIcon, logo: Palette, voice: Mic2, video: Film, mirror: ScanFace };

// Convert relative /api/... URLs from backend into absolute URLs for <img> tags
const resolveUrl = (u) => {
  if (!u) return u;
  if (u.startsWith("/api/")) return `${API_BASE.replace(/\/api$/, "")}${u}`;
  return u;
};

const STYLES = [
  { id: "photoreal", label: "Photoreal" },
  { id: "product", label: "Product shot" },
  { id: "cinematic", label: "Cinematic" },
  { id: "illustration", label: "Illustration" },
  { id: "portrait", label: "Portrait" },
  { id: "anime", label: "Anime" },
];

export default function MediaStudio() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [tools, setTools] = useState({ tools: [], credits: null });
  const [active, setActive] = useState("image");
  const [busy, setBusy] = useState(false);
  const [gallery, setGallery] = useState([]);

  // form state per tool
  const [imgPrompt, setImgPrompt] = useState("a Diwali-themed lifestyle photo for an ethnic kurti brand, warm lighting, marigold flowers");
  const [imgStyle, setImgStyle] = useState("photoreal");
  const [imgSize, setImgSize] = useState("1024");
  const [logo, setLogo] = useState({ brand: "Getszy", tagline: "AI-native commerce", style: "minimal", palette: "earthy" });
  const [voice, setVoice] = useState({ text: "Welcome to Getszy AI — your everything store, powered by intelligent agents.", voice: "female-warm" });
  const [video, setVideo] = useState({ prompt: "a dreamy boho jewellery model walking through soft golden light", duration_seconds: 5, aspect: "16:9" });

  const loadTools = async () => { const r = await api.get("/media/tools"); setTools(r.data); };
  const loadHistory = async () => { const r = await api.get("/media/history?limit=12"); setGallery(r.data.items || []); };

  useEffect(() => { if (!loading && !user) navigate("/login"); }, [user, loading, navigate]);
  useEffect(() => { if (user) { loadTools(); loadHistory(); } }, [user]);

  const generate = async () => {
    setBusy(true);
    try {
      let r;
      if (active === "image") {
        const s = parseInt(imgSize, 10) || 1024;
        toast.loading("Generating image... (~10-15s)", { id: "gen", duration: 30000 });
        r = await api.post("/media/image", { prompt: imgPrompt, style: imgStyle, width: s, height: s });
        toast.success("Image ready!", { id: "gen" });
      } else if (active === "logo") {
        toast.loading("Creating 4 logo concepts... (~20s)", { id: "gen", duration: 45000 });
        r = await api.post("/media/logo", { brand_name: logo.brand, tagline: logo.tagline, style: logo.style, palette: logo.palette });
        toast.success("4 logo concepts ready", { id: "gen" });
      } else if (active === "voice") {
        r = await api.post("/media/voice", voice);
        if (r.data.status === "pending_provider") toast.info(r.data.message); else toast.success("Voice queued");
      } else if (active === "video") {
        r = await api.post("/media/video", video);
        if (r.data.status === "pending_provider") toast.info(r.data.message); else toast.success("Video queued");
      }
      await Promise.all([loadHistory(), loadTools()]);
    } catch (e) {
      const msg = e?.response?.data?.detail || "Generation failed";
      toast.error(msg, { id: "gen" });
      if (e?.response?.status === 402) navigate("/pricing");
    } finally { setBusy(false); }
  };

  if (loading || !user) return <div className="p-10 text-center">Loading…</div>;

  const activeTool = tools.tools.find((t) => t.id === active);
  const isPending = activeTool?.status === "pending";
  const credits = tools.credits;

  return (
    <div className="min-h-screen" style={{ background: "#F7F5F2" }} data-testid="media-studio-page">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-end justify-between flex-wrap gap-3 mb-6">
          <div>
            <Badge className="mb-2" style={{ background: "var(--gs-teal-soft)", color: "var(--gs-teal)" }}>Getszy AI Studio</Badge>
            <h1 className="font-display text-4xl">Media Studio</h1>
            <p className="text-sm text-[var(--gs-muted)] mt-1">Generate 4K images, logos, voiceovers, videos & mirror clones</p>
          </div>
          {credits !== null && (
            <button onClick={() => navigate("/pricing")} className="gs-card px-4 py-3 flex items-center gap-2 text-xs hover:bg-[var(--gs-surface-2)]" data-testid="media-studio-credits">
              <span className="text-[var(--gs-muted)]">Balance</span>
              <span className="font-bold text-base" style={{ color: "var(--gs-teal)" }}>{credits}</span>
              <span className="text-[var(--gs-muted)]">credits</span>
              <span className="ml-2 text-[10px] underline text-[var(--gs-teal)]">Top up</span>
            </button>
          )}
        </div>

        <div className="grid lg:grid-cols-[280px_1fr] gap-6">
          <aside className="space-y-2">
            {tools.tools.map((t) => {
              const Icon = TOOL_ICONS[t.id] || Sparkles;
              return (
                <button key={t.id} onClick={() => setActive(t.id)} data-testid={`media-tool-${t.id}`}
                  className={`w-full text-left gs-card p-4 transition-all ${active === t.id ? "ring-2 ring-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`}>
                  <div className="flex items-start gap-3">
                    <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: t.status === "live" ? "var(--gs-teal-soft)" : "var(--gs-surface-2)" }}>
                      <Icon className={`h-5 w-5 ${t.status === "live" ? "text-[var(--gs-teal)]" : "text-[var(--gs-muted)]"}`}/>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{t.name}</span>
                        {t.status === "pending" && <Lock className="h-3 w-3 text-amber-500"/>}
                      </div>
                      <div className="text-[11px] text-[var(--gs-muted)] mt-0.5">{t.tagline}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">{t.cost} cr</Badge>
                        <span className="text-[10px] text-[var(--gs-muted)]">{t.provider}</span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-[var(--gs-muted)] mt-2"/>
                  </div>
                </button>
              );
            })}
          </aside>

          <main className="space-y-6">
            <div className="gs-card p-6">
              {isPending && (
                <div className="mb-4 p-3 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-xs flex items-center gap-2">
                  <Lock className="h-4 w-4"/>This tool is in preview — will activate as soon as your provider key is configured. You can still draft your prompt.
                </div>
              )}

              {active === "image" && (
                <div className="space-y-4">
                  <h2 className="font-display text-2xl">4K Image Studio</h2>
                  <div><label className="text-xs text-[var(--gs-muted)]">Describe the image</label>
                    <Textarea value={imgPrompt} onChange={(e) => setImgPrompt(e.target.value)} rows={4} data-testid="image-prompt"/></div>
                  <div className="flex flex-wrap gap-2">
                    {STYLES.map((s) => (
                      <button key={s.id} onClick={() => setImgStyle(s.id)} className={`px-3 py-1.5 rounded-full text-xs border ${imgStyle === s.id ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)]"}`}>{s.label}</button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-[var(--gs-muted)]">Resolution</label>
                    {["512", "1024", "1536", "2048"].map((s) => (
                      <button key={s} onClick={() => setImgSize(s)} className={`px-3 py-1 rounded-md text-xs border ${imgSize === s ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)]"}`}>{s}px</button>
                    ))}
                  </div>
                </div>
              )}

              {active === "logo" && (
                <div className="space-y-4">
                  <h2 className="font-display text-2xl">Logo & Brand Kit</h2>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div><label className="text-xs text-[var(--gs-muted)]">Brand name</label><Input value={logo.brand} onChange={(e) => setLogo({ ...logo, brand: e.target.value })} data-testid="logo-brand-input"/></div>
                    <div><label className="text-xs text-[var(--gs-muted)]">Tagline (optional)</label><Input value={logo.tagline} onChange={(e) => setLogo({ ...logo, tagline: e.target.value })}/></div>
                    <div><label className="text-xs text-[var(--gs-muted)]">Style</label><Input value={logo.style} onChange={(e) => setLogo({ ...logo, style: e.target.value })} placeholder="minimal, retro, playful…"/></div>
                    <div><label className="text-xs text-[var(--gs-muted)]">Palette</label><Input value={logo.palette} onChange={(e) => setLogo({ ...logo, palette: e.target.value })} placeholder="earthy, monochrome, pastel…"/></div>
                  </div>
                </div>
              )}

              {active === "voice" && (
                <div className="space-y-4">
                  <h2 className="font-display text-2xl">Voice Studio</h2>
                  <div><label className="text-xs text-[var(--gs-muted)]">Script</label><Textarea rows={5} value={voice.text} onChange={(e) => setVoice({ ...voice, text: e.target.value })}/></div>
                  <div className="flex gap-2">
                    {["female-warm", "female-energetic", "male-calm", "male-deep"].map((v) => (
                      <button key={v} onClick={() => setVoice({ ...voice, voice: v })} className={`px-3 py-1.5 rounded-full text-xs border ${voice.voice === v ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)]"}`}>{v}</button>
                    ))}
                  </div>
                </div>
              )}

              {active === "video" && (
                <div className="space-y-4">
                  <h2 className="font-display text-2xl">4K Video Studio</h2>
                  <Textarea rows={4} value={video.prompt} onChange={(e) => setVideo({ ...video, prompt: e.target.value })}/>
                  <div className="flex items-center gap-3 text-xs">
                    <label>Duration <Input type="number" min={3} max={20} value={video.duration_seconds} onChange={(e) => setVideo({ ...video, duration_seconds: Number(e.target.value) })} className="inline-block w-20 ml-2"/></label>
                    {["16:9", "9:16", "1:1"].map((a) => (
                      <button key={a} onClick={() => setVideo({ ...video, aspect: a })} className={`px-3 py-1 rounded-md text-xs border ${video.aspect === a ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)]"}`}>{a}</button>
                    ))}
                  </div>
                </div>
              )}

              {active === "mirror" && (
                <div className="space-y-4">
                  <h2 className="font-display text-2xl">Mirror AI</h2>
                  <p className="text-sm text-[var(--gs-muted)]">Face swap & cloning preview. Upload feature unlocks with your provider key.</p>
                </div>
              )}

              <div className="mt-6 flex items-center gap-3">
                <Button onClick={generate} disabled={busy} className="gap-2" data-testid="media-generate-button">
                  {busy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Wand2 className="h-4 w-4"/>}
                  {busy ? "Generating…" : isPending ? "Try in preview" : "Generate"}
                </Button>
                {activeTool?.cost != null && !isPending && (
                  <span className="text-xs text-[var(--gs-muted)]">Costs <b>{activeTool.cost} credits</b></span>
                )}
              </div>
            </div>

            {/* Gallery */}
            <div>
              <h3 className="font-display text-xl mb-3">Your recent generations</h3>
              {busy && (
                <div className="gs-card p-4 mb-3 flex items-center gap-3 text-sm">
                  <RefreshCw className="h-4 w-4 animate-spin text-[var(--gs-teal)]"/>
                  <span>Generating your {active}… this usually takes 10–20 seconds. The image is cached after, so it loads instantly next time.</span>
                </div>
              )}
              {gallery.length === 0 && !busy ? (
                <div className="gs-card p-8 text-center text-sm text-[var(--gs-muted)]">Nothing yet — generate your first image above.</div>
              ) : (
                <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4" data-testid="media-gallery">
                  {gallery.map((g) => (
                    <article key={g.id} className="gs-card overflow-hidden">
                      {g.kind === "logo" ? (
                        <div className="grid grid-cols-2 gap-1 p-1">
                          {(g.variants || []).slice(0, 4).map((v) => <img key={v.index} src={resolveUrl(v.url)} alt="logo" loading="lazy" className="w-full aspect-square object-cover rounded-md"/>)}
                        </div>
                      ) : g.url ? (
                        <img src={resolveUrl(g.url)} alt={g.prompt} loading="lazy" className="w-full aspect-square object-cover"/>
                      ) : (
                        <div className="aspect-square grid place-items-center bg-[var(--gs-surface-2)] text-xs text-[var(--gs-muted)]">Pending</div>
                      )}
                      <div className="p-3">
                        <div className="text-xs font-semibold capitalize">{g.kind}</div>
                        <div className="text-[11px] text-[var(--gs-muted)] line-clamp-2 mt-1">{g.prompt || g.brand_name}</div>
                        {g.url && <a href={resolveUrl(g.url)} target="_blank" rel="noreferrer" className="text-[11px] text-[var(--gs-teal)] flex items-center gap-1 mt-2"><Download className="h-3 w-3"/>Open / Download</a>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
