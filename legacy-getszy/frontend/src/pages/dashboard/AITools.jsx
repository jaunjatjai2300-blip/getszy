import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import {
  Wand2, Sparkle, Image, FileText, Search, Palette, Layout,
  Scissors, Flame, ArrowUpCircle, Lightbulb, Loader2, Copy,
  Download, RefreshCw, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";

const TOOLS = [
  { id: "logo", name: "Design a Logo", icon: Palette, color: "#7c3aed", category: "design",
    desc: "Describe your brand, get a logo concept you can iterate on until it's right" },
  { id: "copy", name: "Write Website Copy", icon: FileText, color: "#1e8e8e", category: "content",
    desc: "Describe your page and goal, get compelling headlines, body text, and CTAs" },
  { id: "landing", name: "Write a Landing Page", icon: Layout, color: "#c97a87", category: "content",
    desc: "Get a hero headline, benefits section, social proof, and CTA that converts" },
  { id: "image", name: "Image Generator", icon: Image, color: "#e0a458", category: "media",
    desc: "Describe what you want to see, get a generated image you can refine" },
  { id: "seo", name: "SEO Audit", icon: Search, color: "#5d8f8e", category: "marketing",
    desc: "Share your URL, get a review of on-page, technical, and content SEO" },
  { id: "content", name: "Content Generator", icon: FileText, color: "#10b981", category: "content",
    desc: "Share your topic and audience, get long-form written content" },
  { id: "bg-remove", name: "Background Remover", icon: Scissors, color: "#ef4444", category: "media",
    desc: "Upload an image, get a clean version with the background removed" },
  { id: "heatmap", name: "AI Heatmap", icon: Flame, color: "#f59e0b", category: "marketing",
    desc: "Upload a screenshot, get a predicted-attention heatmap overlay" },
  { id: "upscaler", name: "Image Upscaler", icon: ArrowUpCircle, color: "#3b82f6", category: "media",
    desc: "Upload an image, get a sharper, higher-resolution version" },
  { id: "validate", name: "Validate My Business Idea", icon: Lightbulb, color: "#8b5cf6", category: "strategy",
    desc: "Describe your idea, get honest feedback on viability, risks, and next steps" },
];

const CATEGORIES = [
  { id: "all", label: "All Tools" },
  { id: "design", label: "Design" },
  { id: "content", label: "Content" },
  { id: "media", label: "Media" },
  { id: "marketing", label: "Marketing" },
  { id: "strategy", label: "Strategy" },
];

export default function AITools() {
  const [active, setActive] = useState(null);
  const [cat, setCat] = useState("all");

  const filtered = cat === "all" ? TOOLS : TOOLS.filter(t => t.category === cat);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2">
          <Wand2 className="h-7 w-7 text-[var(--gs-teal)]"/> AI Tools
        </h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">
          10 AI-powered tools to design, write, generate, and validate — all in one place.
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {CATEGORIES.map(c => (
          <button key={c.id} onClick={() => setCat(c.id)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-all ${
              cat === c.id ? "bg-[var(--gs-teal)] text-white" : "bg-white border hover:bg-[var(--gs-surface-2)]"
            }`}>
            {c.label}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(tool => {
          const Icon = tool.icon;
          return (
            <button key={tool.id} onClick={() => setActive(tool)}
              className="gs-card p-5 text-left hover:bg-[var(--gs-surface-2)] transition group">
              <div className="h-12 w-12 rounded-2xl grid place-items-center" style={{ background: `${tool.color}22` }}>
                <Icon className="h-6 w-6" style={{ color: tool.color }}/>
              </div>
              <div className="mt-3 font-display text-lg">{tool.name}</div>
              <div className="text-xs text-[var(--gs-muted)] mt-1">{tool.desc}</div>
              <div className="mt-3 text-xs font-semibold flex items-center gap-1" style={{ color: tool.color }}>
                Try it <Sparkle className="h-3.5 w-3.5"/>
              </div>
            </button>
          );
        })}
      </div>

      {active && <ToolDialog tool={active} onClose={() => setActive(null)}/>}
    </div>
  );
}

function ToolDialog({ tool, onClose }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: `${tool.color}22` }}>
              <tool.icon className="h-5 w-5" style={{ color: tool.color }}/>
            </div>
            <div>
              <h2 className="font-display text-xl">{tool.name}</h2>
              <p className="text-xs text-[var(--gs-muted)]">{tool.desc}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-[var(--gs-muted)] hover:text-[var(--gs-ink)] text-xl">✕</button>
        </div>
        {tool.id === "logo" && <LogoTool color={tool.color}/>}
        {tool.id === "copy" && <CopyTool color={tool.color}/>}
        {tool.id === "landing" && <LandingTool color={tool.color}/>}
        {tool.id === "image" && <ImageGenTool color={tool.color}/>}
        {tool.id === "seo" && <SEOTool color={tool.color}/>}
        {tool.id === "content" && <ContentTool color={tool.color}/>}
        {tool.id === "bg-remove" && <BGRemoveTool color={tool.color}/>}
        {tool.id === "heatmap" && <HeatmapTool color={tool.color}/>}
        {tool.id === "upscaler" && <UpscalerTool color={tool.color}/>}
        {tool.id === "validate" && <ValidateTool color={tool.color}/>}
      </div>
    </div>
  );
}

// ── 1. Logo Generator ──
function LogoTool({ color }) {
  const [brand, setBrand] = useState("");
  const [style, setStyle] = useState("minimal");
  const [busy, setBusy] = useState(false);
  const [logos, setLogos] = useState([]);

  const generate = async () => {
    if (!brand.trim()) return toast.error("Brand name required");
    setBusy(true); toast.loading("Generating logos…", { id: "logo" });
    try {
      const r = await api.post("/media/logo", { brand_name: brand, style, palette: "teal" });
      setLogos(r.data.variants?.map(v => v.url) || []);
      toast.success("4 logo concepts ready ✅", { id: "logo" });
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "logo" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Brand name *</label>
        <Input value={brand} onChange={e => setBrand(e.target.value)} placeholder="e.g. Getszy, PixelCraft, NovaBite"/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Style</label>
        <Select value={style} onValueChange={setStyle}>
          <SelectTrigger><SelectValue/></SelectTrigger>
          <SelectContent>
            {["minimal", "bold", "playful", "elegant", "tech", "organic"].map(s =>
              <SelectItem key={s} value={s}>{s}</SelectItem>
            )}
          </SelectContent>
        </Select>
      </div>
      <Button onClick={generate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Generating…" : "Generate 4 Logo Concepts"}
      </Button>
      {logos.length > 0 ? (
        <div className="grid grid-cols-2 gap-3">
          {logos.map((url, i) => (
            <div key={i} className="rounded-xl overflow-hidden border bg-white">
              <img src={url} alt={`Logo ${i+1}`} className="w-full aspect-square object-contain"/>
              <a href={url} download className="block text-center text-xs py-2 bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface)]">
                <Download className="h-3 w-3 inline mr-1"/>Download
              </a>
            </div>
          ))}
        </div>
      ) : !busy && (
        <p className="text-xs text-[var(--gs-muted)]">Your generated logo concepts will appear here.</p>
      )}
    </div>
  );
}

// ── 2. Website Copy ──
function CopyTool({ color }) {
  const [desc, setDesc] = useState("");
  const [goal, setGoal] = useState("sales");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  const generate = async () => {
    if (!desc.trim()) return toast.error("Describe your page");
    setBusy(true); toast.loading("Writing copy…", { id: "copy" });
    try {
      const r = await api.post("/ai-tools/chat/completions", {
        messages: [
          { role: "system", content: "You are a world-class, conversion-focused website copywriter. Produce brand-grade, specific, benefit-driven copy — never generic filler or 'lorem ipsum'. Structure the response with clear markdown headings and bulleted sections. Match the requested goal and tone." },
          { role: "user", content: `Write high-converting website copy for: ${desc}\nPrimary goal: ${goal}\n\nDeliver exactly:\n## Headline Options\n- 3 distinct, punchy hero headlines\n## Subheadline\n- One compelling subheadline that reinforces the value prop\n## Body Copy\n- 2-3 short, benefit-led paragraphs\n## Social Proof Angle\n- One credibility statement (stats, testimonial style, or trust signal)\n## CTA Buttons\n- 2 CTA button texts (action-oriented, < 5 words)` }
        ]
      });
      setResult(r.data.choices?.[0]?.message?.content || "No result");
      toast.success("Copy ready ✅", { id: "copy" });
    } catch (e) { toast.error("Failed", { id: "copy" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Describe your page *</label>
        <Textarea rows={3} value={desc} onChange={e => setDesc(e.target.value)} placeholder="e.g. Landing page for an AI-powered resume builder for Indian students"/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Goal</label>
        <Select value={goal} onValueChange={setGoal}>
          <SelectTrigger><SelectValue/></SelectTrigger>
          <SelectContent>
            <SelectItem value="sales">Sales</SelectItem>
            <SelectItem value="leads">Lead Generation</SelectItem>
            <SelectItem value="signup">Signups</SelectItem>
            <SelectItem value="brand">Brand Awareness</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button onClick={generate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Writing…" : "Generate Copy"}
      </Button>
      {result && <ResultCard text={result}/>}
    </div>
  );
}

// ── 3. Landing Page ──
function LandingTool({ color }) {
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  const generate = async () => {
    if (!desc.trim()) return toast.error("Describe your landing page");
    setBusy(true); toast.loading("Building landing page…", { id: "land" });
    try {
      const r = await api.post("/ai-tools/chat/completions", {
        messages: [
          { role: "system", content: "You are a senior conversion-rate-optimization specialist and landing page copywriter. Write a complete, ready-to-build landing page copy deck that is specific, persuasive, and structured. Use clear markdown headings. Never use generic placeholders — invent plausible, compelling specifics." },
          { role: "user", content: `Create a high-converting landing page copy deck for: ${desc}\n\nInclude:\n## Hero\n- Headline + subheadline + primary CTA text\n## Value Proposition\n- 3 benefit-driven bullet points\n## Features / Benefits\n- 4 items (name + one-line benefit each)\n## Social Proof\n- 2 short testimonial-style quotes + 1 trust stat\n## FAQ\n- 4 common objections with reassuring answers\n## Final CTA Section\n- Headline + button text + supporting microcopy\n## SEO Meta\n- Title tag (<=60 chars) + meta description (<=155 chars)` }
        ]
      });
      setResult(r.data.choices?.[0]?.message?.content || "No result");
      toast.success("Landing page ready ✅", { id: "land" });
    } catch (e) { toast.error("Failed", { id: "land" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Describe your product/service *</label>
        <Textarea rows={3} value={desc} onChange={e => setDesc(e.target.value)} placeholder="e.g. AI-powered fitness coach app for women, ₹299/month, tracks workouts + nutrition"/>
      </div>
      <Button onClick={generate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Building…" : "Generate Landing Page"}
      </Button>
      {result && <ResultCard text={result}/>}
    </div>
  );
}

// ── 4. Image Generator ──
function ImageGenTool({ color }) {
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [image, setImage] = useState("");

  const generate = async () => {
    if (!prompt.trim()) return toast.error("Describe the image");
    setBusy(true); toast.loading("Generating image…", { id: "img" });
    try {
      const r = await api.post("/media/image", { prompt, width: 1024, height: 1024 });
      setImage(r.data.url || "");
      toast.success("Image ready ✅", { id: "img" });
    } catch (e) { toast.error("Failed", { id: "img" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Describe what you want to see *</label>
        <Textarea rows={3} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="e.g. A serene Japanese garden with cherry blossoms, soft morning light, watercolor style"/>
      </div>
      <Button onClick={generate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Image className="h-4 w-4 mr-2"/>}
        {busy ? "Generating…" : "Generate Image"}
      </Button>
      {image && (
        <div className="rounded-xl overflow-hidden border">
          <img src={image} alt="Generated" className="w-full"/>
          <a href={image} download className="block text-center text-xs py-2 bg-[var(--gs-surface-2)]">
            <Download className="h-3 w-3 inline mr-1"/>Download
          </a>
        </div>
      )}
    </div>
  );
}

// ── 5. SEO Audit ──
function SEOTool({ color }) {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  const analyze = async () => {
    if (!url.trim()) return toast.error("Enter a URL");
    setBusy(true); toast.loading("Analyzing SEO…", { id: "seo" });
    try {
      const r = await api.post("/ai-tools/chat/completions", {
        messages: [
          { role: "system", content: "You are an SEO expert. Analyze the given URL and provide: 1) Title & meta review, 2) Heading structure, 3) Content quality, 4) Technical issues, 5) Recommendations. Be specific and actionable. Format as clean markdown." },
          { role: "user", content: `Perform SEO audit for: ${url}` }
        ]
      });
      setResult(r.data.choices?.[0]?.message?.content || "No result");
      toast.success("SEO audit ready ✅", { id: "seo" });
    } catch (e) { toast.error("Failed", { id: "seo" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Website URL *</label>
        <Input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://yourwebsite.com"/>
      </div>
      <Button onClick={analyze} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Search className="h-4 w-4 mr-2"/>}
        {busy ? "Analyzing…" : "Run SEO Audit"}
      </Button>
      {result && <ResultCard text={result}/>}
    </div>
  );
}

// ── 6. Content Generator ──
function ContentTool({ color }) {
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  const generate = async () => {
    if (!topic.trim()) return toast.error("Enter a topic");
    setBusy(true); toast.loading("Writing content…", { id: "content" });
    try {
      const r = await api.post("/ai-tools/chat/completions", {
        messages: [
          { role: "system", content: "You are a content writer. Write engaging, well-structured long-form content with introduction, main sections with H2/H3 headings, bullet points, and a conclusion. Format as clean markdown." },
          { role: "user", content: `Write about: ${topic}\nTarget audience: ${audience || 'general'}\nLength: 800-1200 words` }
        ]
      });
      setResult(r.data.choices?.[0]?.message?.content || "No result");
      toast.success("Content ready ✅", { id: "content" });
    } catch (e) { toast.error("Failed", { id: "content" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Topic *</label>
        <Input value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. How AI is changing Indian small businesses"/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Target audience</label>
        <Input value={audience} onChange={e => setAudience(e.target.value)} placeholder="e.g. Small business owners in India"/>
      </div>
      <Button onClick={generate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Writing…" : "Generate Content"}
      </Button>
      {result && <ResultCard text={result}/>}
    </div>
  );
}

// ── 7. Background Remover ──
function BGRemoveTool({ color }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const fileRef = useRef(null);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); toast.loading("Removing background…", { id: "bg" });
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/ai-tools/bg-remove", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data.url || "");
      toast.success("Background removed ✅", { id: "bg" });
    } catch (e) { toast.error(e?.response?.data?.detail || "Upload an image first", { id: "bg" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={upload}/>
        <Button onClick={() => fileRef.current?.click()} disabled={busy} className="w-full text-white" style={{ background: color }}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Scissors className="h-4 w-4 mr-2"/>}
          {busy ? "Processing…" : "Upload Image"}
        </Button>
      </div>
      {result && (
        <div className="rounded-xl overflow-hidden border">
          <img src={result} alt="Result" className="w-full"/>
          <a href={result} download className="block text-center text-xs py-2 bg-[var(--gs-surface-2)]">
            <Download className="h-3 w-3 inline mr-1"/>Download
          </a>
        </div>
      )}
    </div>
  );
}

// ── 8. AI Heatmap ──
function HeatmapTool({ color }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const fileRef = useRef(null);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); toast.loading("Generating heatmap…", { id: "heat" });
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/ai-tools/heatmap", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data.url || "");
      toast.success("Heatmap ready ✅", { id: "heat" });
    } catch (e) { toast.error(e?.response?.data?.detail || "Upload a screenshot first", { id: "heat" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={upload}/>
        <Button onClick={() => fileRef.current?.click()} disabled={busy} className="w-full text-white" style={{ background: color }}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Flame className="h-4 w-4 mr-2"/>}
          {busy ? "Analyzing…" : "Upload Screenshot"}
        </Button>
      </div>
      {result && (
        <div className="rounded-xl overflow-hidden border">
          <img src={result} alt="Heatmap" className="w-full"/>
          <a href={result} download className="block text-center text-xs py-2 bg-[var(--gs-surface-2)]">
            <Download className="h-3 w-3 inline mr-1"/>Download
          </a>
        </div>
      )}
    </div>
  );
}

// ── 9. Image Upscaler ──
function UpscalerTool({ color }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const fileRef = useRef(null);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); toast.loading("Upscaling…", { id: "up" });
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/ai-tools/upscale", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data.url || "");
      toast.success("Upscaled ✅", { id: "up" });
    } catch (e) { toast.error(e?.response?.data?.detail || "Upload an image first", { id: "up" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={upload}/>
        <Button onClick={() => fileRef.current?.click()} disabled={busy} className="w-full text-white" style={{ background: color }}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <ArrowUpCircle className="h-4 w-4 mr-2"/>}
          {busy ? "Upscaling…" : "Upload Image"}
        </Button>
      </div>
      {result && (
        <div className="rounded-xl overflow-hidden border">
          <img src={result} alt="Upscaled" className="w-full"/>
          <a href={result} download className="block text-center text-xs py-2 bg-[var(--gs-surface-2)]">
            <Download className="h-3 w-3 inline mr-1"/>Download
          </a>
        </div>
      )}
    </div>
  );
}

// ── 10. Validate Business Idea ──
function ValidateTool({ color }) {
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");

  const validate = async () => {
    if (!idea.trim()) return toast.error("Describe your idea");
    setBusy(true); toast.loading("Analyzing idea…", { id: "val" });
    try {
      const r = await api.post("/ai-tools/chat/completions", {
        messages: [
          { role: "system", content: "You are a brutal-honest startup advisor. Evaluate the business idea and provide: 1) One-line verdict (Go/Iterate/Stop), 2) Market size estimate, 3) Top 3 risks, 4) Competitive landscape, 5) Suggested next steps (3 actionable items). Be direct and honest. Format as clean markdown." },
          { role: "user", content: `Validate this business idea: ${idea}` }
        ]
      });
      setResult(r.data.choices?.[0]?.message?.content || "No result");
      toast.success("Analysis ready ✅", { id: "val" });
    } catch (e) { toast.error("Failed", { id: "val" }); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Describe your business idea *</label>
        <Textarea rows={3} value={idea} onChange={e => setIdea(e.target.value)} placeholder="e.g. AI-powered WhatsApp bot that sends daily outfit recommendations based on weather + user style preferences, monetized via affiliate links"/>
      </div>
      <Button onClick={validate} disabled={busy} className="w-full text-white" style={{ background: color }}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Lightbulb className="h-4 w-4 mr-2"/>}
        {busy ? "Analyzing…" : "Validate Idea"}
      </Button>
      {result && <ResultCard text={result}/>}
    </div>
  );
}

// ── Shared result card ──
function ResultCard({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <div className="rounded-xl border bg-[var(--gs-surface-2)] p-4">
      <div className="flex items-center justify-between mb-2">
        <Badge variant="outline" className="text-[10px]">Result</Badge>
        <button onClick={copy} className="text-xs text-[var(--gs-muted)] hover:text-[var(--gs-teal)]">
          {copied ? <CheckCircle2 className="h-3.5 w-3.5 inline mr-1"/> : <Copy className="h-3.5 w-3.5 inline mr-1"/>}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="text-sm whitespace-pre-wrap leading-relaxed">{text}</div>
    </div>
  );
}
