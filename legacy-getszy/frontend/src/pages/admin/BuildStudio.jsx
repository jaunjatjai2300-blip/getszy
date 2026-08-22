import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import * as Icons from "lucide-react";
import { Wand2, Loader2, Play, Download, Trash2, ExternalLink, Copy, Sparkle, Plus, Laptop, Smartphone, Tablet, RotateCcw, ShieldCheck, CheckCircle2, AlertTriangle, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const PREVIEW_TEMPLATE_FALLBACK = [
  { id: "dance-academy", name: "Dance Academy", industry: "Dance & Performing Arts", source: "Getszy curated" },
  { id: "brand-foundation", name: "Professional Brand Foundation", industry: "General Business", source: "Getszy curated" },
  { id: "saas-app", name: "SaaS App Launch", industry: "Technology & SaaS" },
  { id: "agency-digital", name: "Digital Agency", industry: "Professional Services" },
  { id: "business-startup", name: "Startup Launch", industry: "Business" },
  { id: "ecommerce-tech", name: "Tech Shop", industry: "E-commerce" },
  { id: "education-courses", name: "Online Courses", industry: "Education" },
  { id: "fitness-gym", name: "Fitness Gym", industry: "Wellness & Fitness" },
  { id: "medical-clinic", name: "Health Clinic", industry: "Healthcare" },
  { id: "realestate-luxury", name: "Luxury Properties", industry: "Real Estate" },
  { id: "restaurant-cafe", name: "Cafe & Bistro", industry: "Food & Beverage" },
  { id: "portfolio-creative", name: "Creative Studio", industry: "Portfolio & Agency" },
  { id: "blog-modern", name: "Modern Editorial", industry: "Blog & Editorial" },
  { id: "photography-wedding", name: "Wedding Photography", industry: "Events & Wedding" },
];

async function downloadAuthenticated(path, filename) {
  const apiPath = path.replace(/^\/api(?=\/)/, "");
  try {
    const response = await api.get(apiPath, { responseType: "blob" });
    const blob = response.data instanceof Blob ? response.data : new Blob([response.data]);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    toast.error(error?.response?.status === 401 ? "Please sign in again to download" : "Download failed — please retry");
  }
}

function useHub() {
  const [hub, setHub] = useState({ counts: {}, categories: [] });
  const load = useCallback(async () => { try { const r = await api.get("/builder/hub"); setHub(r.data); } catch (e) { toast.error("Couldn't load Build Studio — refresh to retry"); } }, []);
  useEffect(() => { load(); }, [load]);
  return { hub, reload: load };
}

export default function BuildStudio({ embedded = false }) {
  const { hub, reload: reloadHub } = useHub();
  const [active, setActive] = useState(null); // category id

  return (
    <div className="space-y-6" data-testid="admin-build-studio-page">
      {!embedded && (
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Wand2 className="h-7 w-7 text-[var(--gs-teal)]"/> Build Studio</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">One place to build anything — web apps, faceless channels, custom AI agents, mobile apps, full-stack sites, blogs. Preview, download, deploy.</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="hub-stats">
        {[["webapps","Web Apps"],["channels","Channels"],["agents","Custom Agents"],["starters","Starters"],["videos","Videos"]].map(([k,l]) => (
          <Card key={k} className="p-4">
            <div className="text-[10px] text-[var(--gs-muted)] uppercase">{l}</div>
            <div className="font-display text-3xl mt-1">{hub.counts?.[k] ?? 0}</div>
          </Card>
        ))}
      </div>

      {/* Categories */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="hub-categories">
        {(hub.categories || []).map((c) => {
          const Icon = Icons[c.icon] || Wand2;
          return (
            <button key={c.id} onClick={() => setActive(c)} data-testid={`build-cat-${c.id}`}
              className="gs-card p-5 text-left hover:bg-[var(--gs-surface-2)] transition group">
              <div className="h-12 w-12 rounded-2xl grid place-items-center" style={{ background: `${c.color}22` }}>
                <Icon className="h-6 w-6" style={{ color: c.color }}/>
              </div>
              <div className="mt-3 font-display text-xl">{c.title}</div>
              <div className="text-xs text-[var(--gs-muted)] mt-1">{c.desc}</div>
              <div className="mt-3 text-xs font-semibold flex items-center gap-1" style={{ color: c.color }}>
                Build <Sparkle className="h-3.5 w-3.5"/>
              </div>
            </button>
          );
        })}
      </div>

      {active && <BuilderDialog category={active} onClose={() => { setActive(null); reloadHub(); }}/>}
    </div>
  );
}

// ============================================================
// Category dialog dispatcher
// ============================================================
function BuilderDialog({ category, onClose }) {
  return (
    <Dialog open={true} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid={`build-dialog-${category.id}`}>
        <DialogHeader>
          <DialogTitle className="font-display text-2xl" style={{ color: category.color }}>{category.title}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-[var(--gs-muted)]">{category.desc}</p>
        {category.id === "webapp"    && <WebAppBuilder color={category.color}/>}
        {category.id === "channel"   && <ChannelBuilder color={category.color}/>}
        {category.id === "agent"     && <AgentBuilder color={category.color}/>}
        {category.id === "mobileapp" && <StarterBuilder color={category.color} kind="mobileapp" placeholder="e.g. Indian food delivery app with tracking + address book"/>}
        {category.id === "fullstack" && <StarterBuilder color={category.color} kind="fullstack" placeholder="e.g. Task manager with categories and due dates"/>}
        {category.id === "blog"      && <StarterBuilder color={category.color} kind="blog" placeholder="e.g. Personal finance blog for Indian millennials"/>}
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// 1) Web App Builder
// ============================================================
function recommendedStarterId(value) {
  return /\bdance\b/i.test(String(value || "")) ? "dance-academy" : "brand-foundation";
}

function WebAppBuilder({ color }) {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [projects, setProjects] = useState([]);
  const [previewId, setPreviewId] = useState(null);
  const [previewDevice, setPreviewDevice] = useState("desktop");
  const [previewQuality, setPreviewQuality] = useState(null);
  const [showBrief, setShowBrief] = useState(false);
  const [proofPoints, setProofPoints] = useState("");
  const [brief, setBrief] = useState({ audience: "", primary_goal: "", primary_cta: "", brand_name: "", visual_style: "", offer: "" });
  const [templateId, setTemplateId] = useState("brand-foundation");
  const [templates, setTemplates] = useState(PREVIEW_TEMPLATE_FALLBACK);
  const [templateChosen, setTemplateChosen] = useState(false);
  const [creditInfo, setCreditInfo] = useState({ credits: null, costs: {} });
  const [createdProject, setCreatedProject] = useState(null);
  const isReadOnlyPreview = typeof window !== "undefined" && window.location.hostname.startsWith("preview.");

  const updateBrief = (field, value) => setBrief((current) => ({ ...current, [field]: value }));
  const load = async () => { try { const r = await api.get("/builder/projects"); setProjects(r.data || []); } catch (e) { toast.error("Couldn't load projects — refresh to retry"); } };
  const loadTemplates = async () => { try { const r = await api.get("/builder/templates"); setTemplates(r.data.templates || PREVIEW_TEMPLATE_FALLBACK); } catch { setTemplates(PREVIEW_TEMPLATE_FALLBACK); } };
  const loadCredits = async () => { try { const r = await api.get("/credits/me"); setCreditInfo({ credits: Number(r.data?.credits ?? 0), costs: r.data?.costs || {} }); } catch { setCreditInfo({ credits: null, costs: {} }); } };
  useEffect(() => { load(); loadTemplates(); loadCredits(); }, []);
  useEffect(() => {
    try {
      const draft = JSON.parse(sessionStorage.getItem("getszy_mission_draft") || "null");
      if (draft?.prompt) { setPrompt((current) => current || draft.prompt); setTemplateId(recommendedStarterId(draft.prompt)); }
    } catch { /* An invalid local mission draft must never block a customer build. */ }
  }, []);

  const curatedTemplates = templates.filter((template) => template.source === "Getszy curated");
  const isStarter = true;
  const buildCost = 0;
  const hasEnoughCredits = true;

  const build = async () => {
    if (prompt.trim().length < 4) return toast.error("Prompt too short");
    const confirmation = "Create this curated professional private draft? It does not consume AI generation credits. Any later AI refinement or visual action will show its prepaid cost before you confirm.";
    if (!window.confirm(confirmation)) return;
    setCreatedProject(null);
    setBusy(true); toast.loading("Creating your private project draft…", { id: "wa", duration: 60000 });
    try {
      const normalizedBrief = {
        ...brief,
        proof_points: proofPoints.split("\n").map((item) => item.trim()).filter(Boolean).slice(0, 6),
      };
      const r = await api.post("/builder/projects", { prompt, name, template_id: templateId || null, brief: normalizedBrief });
      toast.success(`Built: ${r.data.name} ✅`, { id: "wa" });
      setPrompt(""); setName(""); setProofPoints(""); setTemplateId("brand-foundation"); setTemplateChosen(false);
      setBrief({ audience: "", primary_goal: "", primary_cta: "", brand_name: "", visual_style: "", offer: "" });
      setPreviewId(r.data.id); setPreviewQuality(r.data.quality_report || null); setCreatedProject(r.data); sessionStorage.setItem("getszy_last_project_id", r.data.id); await Promise.all([load(), loadCredits()]);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "wa" }); }
    finally { setBusy(false); }
  };

  const del = async (pid) => { try { await api.delete(`/builder/projects/${pid}`); load(); toast.success("Deleted"); } catch (e) { toast.error("Delete failed — please retry"); } };

  return (
    <div className="space-y-4 mt-4">
      <div className="rounded-xl border p-3" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
        <div className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--gs-teal)]" /><div><div className="text-sm font-semibold">Start from a curated professional visual system</div><p className="mt-0.5 text-xs text-[var(--gs-muted)]">Getszy no longer sends initial customer projects to a generic open-ended AI page generator. Start from an image-led curated foundation, then add verified business details and paid refinements only when you choose them.</p></div></div>
        <div className="mt-3"><label className="text-xs text-[var(--gs-muted)]">Curated professional starter</label><Select value={templateId} onValueChange={(value) => { setTemplateId(value); setTemplateChosen(true); }}><SelectTrigger data-testid="wa-template"><SelectValue /></SelectTrigger><SelectContent className="max-h-72">{curatedTemplates.map((template) => <SelectItem key={template.id} value={template.id}>{template.name} · {template.industry}</SelectItem>)}</SelectContent></Select></div>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">What should this page achieve? *</label>
        <Textarea rows={3} value={prompt} onChange={(e) => { const value = e.target.value; setPrompt(value); if (!templateChosen) setTemplateId(recommendedStarterId(value)); }} placeholder="Build a premium landing page for a Kathak dance academy in Jaipur…" data-testid="wa-prompt"/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Name (optional)</label>
        <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="wa-name"/>
      </div>
      <div className="rounded-xl border" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>
        <button type="button" onClick={() => setShowBrief((open) => !open)} className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left">
          <span className="flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal className="h-4 w-4 text-[var(--gs-teal)]" />Professional page brief</span>
          <span className="text-xs text-[var(--gs-muted)]">{showBrief ? "Hide" : "Add context"}</span>
        </button>
        {showBrief && (
          <div className="space-y-3 border-t px-3 py-3" style={{ borderColor: "var(--gs-border)" }}>
            <p className="text-xs text-[var(--gs-muted)]">Optional, but this is how Getszy turns a generic request into a clearer, on-brand, conversion-focused page. Only add claims and proof you can verify.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div><label className="text-xs text-[var(--gs-muted)]">Brand name</label><Input value={brief.brand_name} onChange={(e) => updateBrief("brand_name", e.target.value)} placeholder="e.g. Raag Dance Academy" /></div>
              <div><label className="text-xs text-[var(--gs-muted)]">Target audience</label><Input value={brief.audience} onChange={(e) => updateBrief("audience", e.target.value)} placeholder="e.g. Jaipur parents and adult learners" /></div>
              <div><label className="text-xs text-[var(--gs-muted)]">Primary goal</label><Select value={brief.primary_goal} onValueChange={(value) => updateBrief("primary_goal", value)}><SelectTrigger><SelectValue placeholder="Choose one outcome" /></SelectTrigger><SelectContent><SelectItem value="Collect qualified leads">Collect qualified leads</SelectItem><SelectItem value="Book a consultation">Book a consultation</SelectItem><SelectItem value="Sell a product">Sell a product</SelectItem><SelectItem value="Start a free trial">Start a free trial</SelectItem><SelectItem value="Grow an audience">Grow an audience</SelectItem></SelectContent></Select></div>
              <div><label className="text-xs text-[var(--gs-muted)]">Primary CTA</label><Input value={brief.primary_cta} onChange={(e) => updateBrief("primary_cta", e.target.value)} placeholder="e.g. Book a free class" /></div>
              <div><label className="text-xs text-[var(--gs-muted)]">Visual direction</label><Select value={brief.visual_style} onValueChange={(value) => updateBrief("visual_style", value)}><SelectTrigger><SelectValue placeholder="Choose a style" /></SelectTrigger><SelectContent><SelectItem value="Warm and premium">Warm and premium</SelectItem><SelectItem value="Modern and minimal">Modern and minimal</SelectItem><SelectItem value="Bold and energetic">Bold and energetic</SelectItem><SelectItem value="Editorial and refined">Editorial and refined</SelectItem><SelectItem value="Trustworthy and clinical">Trustworthy and clinical</SelectItem></SelectContent></Select></div>
              <div><label className="text-xs text-[var(--gs-muted)]">Core offer</label><Input value={brief.offer} onChange={(e) => updateBrief("offer", e.target.value)} placeholder="e.g. 8-week beginner Kathak course" /></div>
            </div>
            <div><label className="text-xs text-[var(--gs-muted)]">Verified proof points (one per line)</label><Textarea rows={3} value={proofPoints} onChange={(e) => setProofPoints(e.target.value)} placeholder="e.g. Established in 2015&#10;e.g. 120 verified Google reviews" /><p className="mt-1 text-[11px] text-[var(--gs-muted)]">Do not add testimonials, ratings, counts, prices, guarantees, or certifications unless they are true and approved for use.</p></div>
          </div>
        )}
      </div>
      <div className="rounded-xl border px-3 py-3 text-sm" style={{ borderColor: hasEnoughCredits ? "var(--gs-border)" : "#f5b6b6", background: hasEnoughCredits ? "var(--gs-surface-2)" : "#fff4f4" }}>
        <div className="flex flex-wrap items-center justify-between gap-2"><div className="font-semibold">Curated professional starter</div><div className="rounded-full bg-white px-2.5 py-1 text-xs font-bold">0 credits</div></div>
        <p className="mt-1 text-xs text-[var(--gs-muted)]">The first private visual foundation is included. Any later AI refinement or visual-generation action must show its prepaid credit cost before you confirm it.</p>
      </div>
      {isReadOnlyPreview && <div className="rounded-lg border px-3 py-2 text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>Preview mode is read-only: you can inspect the professional brief, cost and starter options, but creation remains disabled until this feature is approved and promoted through the release process.</div>}
      <Button onClick={build} disabled={busy || isReadOnlyPreview || !hasEnoughCredits} className="w-full text-white" style={{ background: color }} data-testid="wa-build-btn">
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Preparing…" : isReadOnlyPreview ? "Preview mode — creation disabled" : "Create Professional Private Draft"}
      </Button>

      <div className="rounded-xl border p-3 text-sm" style={{ borderColor: busy ? "#9dc9ee" : "var(--gs-border)", background: busy ? "#f0f8ff" : "var(--gs-surface-2)" }} aria-live="polite" data-testid="wa-build-status">
        {busy ? <div className="flex items-start gap-2"><Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-sky-700" /><div><strong>Creating your private draft.</strong><p className="mt-1 text-xs leading-5 text-[var(--gs-muted)]">Neo is using your request and brief. This page will show either the real finished project or a clear error; Getszy does not display a made-up progress percentage.</p></div></div> : <div className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--gs-teal)]" /><div><strong>Build status stays visible.</strong><p className="mt-1 text-xs leading-5 text-[var(--gs-muted)]">Every finished website is saved as a project. You can open its project workspace, inspect the private preview, review quality checks, and see the next action.</p></div></div>}
      </div>

      {createdProject && <div className="rounded-xl border border-[#9ed2c3] bg-[#f0f8f5] p-4" data-testid="wa-created-project"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-2 text-sm font-semibold text-[#183c3c]"><CheckCircle2 className="h-4 w-4 text-emerald-700" />Private draft created</div><p className="mt-1 text-xs leading-5 text-[#39685f]">{createdProject.name} is ready for your private review. It has not been published or deployed.</p></div><Button type="button" onClick={() => navigate(`/dashboard/projects/${createdProject.id}`)} className="bg-[#183c3c] text-white hover:bg-[#102f2f]">Review finished project <ExternalLink className="ml-2 h-4 w-4" /></Button></div></div>}

      <div className="grid md:grid-cols-2 gap-2 max-h-80 overflow-y-auto" data-testid="wa-projects">
        {projects.map((p) => (
          <Card key={p.id} className="p-3 flex items-center gap-2" data-testid={`wa-project-${p.id}`}>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{p.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)] truncate">{p.prompt}</div>
            </div>
            <Button variant="outline" size="sm" onClick={() => { setPreviewId(p.id); setPreviewQuality(p.quality_report || null); }}><Play className="h-3.5 w-3.5"/></Button>
            <button type="button" onClick={() => downloadAuthenticated(`/builder/projects/${p.id}/download`, `${p.name || "project"}.zip`)} className="p-2 text-[var(--gs-muted)] hover:text-[var(--gs-teal)]" title="Download zip" aria-label={`Download ${p.name || "project"} zip`} data-testid={`wa-download-${p.id}`}><Download className="h-4 w-4"/></button>
            <button onClick={() => del(p.id)} className="text-rose-500" data-testid={`wa-del-${p.id}`}><Trash2 className="h-4 w-4"/></button>
          </Card>
        ))}
      </div>

      {previewId && (
        <div className="mt-5 overflow-hidden rounded-2xl border" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>
          <div className="flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
            <div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="border-[var(--gs-teal)]/30 bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]">Private preview</Badge>
                <span className="text-xs font-medium text-[var(--gs-ink)]">Not deployed</span>
              </div>
              <p className="mt-1 text-xs text-[var(--gs-muted)]">Review layout and content here before you download or publish this project.</p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {[
                ["desktop", "Desktop", Laptop],
                ["tablet", "Tablet", Tablet],
                ["mobile", "Mobile", Smartphone],
              ].map(([id, label, DeviceIcon]) => (
                <Button key={id} type="button" size="sm" variant={previewDevice === id ? "default" : "outline"} onClick={() => setPreviewDevice(id)} className={previewDevice === id ? "bg-[var(--gs-teal)] text-white hover:bg-[var(--gs-teal)]" : ""}>
                  <DeviceIcon className="mr-1.5 h-3.5 w-3.5" />{label}
                </Button>
              ))}
              <Button type="button" size="icon" variant="outline" onClick={() => setPreviewId(null)} aria-label="Close preview"><RotateCcw className="h-3.5 w-3.5" /></Button>
              <a href={`${BACKEND_URL}/api/builder/projects/${previewId}/preview`} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-md border px-2 text-xs font-medium hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}><ExternalLink className="h-3.5 w-3.5" />Open</a>
            </div>
          </div>
          {previewQuality && (
            <div className="border-b px-4 py-3" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
              <div className="flex flex-wrap items-center gap-2"><Badge variant="outline" className={previewQuality.status === "ready_for_human_review" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700" : "border-amber-500/40 bg-amber-500/10 text-amber-700"}>{previewQuality.score}/100 structural preflight</Badge><span className="text-xs text-[var(--gs-muted)]">{previewQuality.required_checks_passed}/{previewQuality.required_checks_total} required checks passed</span></div>
              {previewQuality.next_actions?.length > 0 ? <div className="mt-2 flex items-start gap-2 text-xs text-[var(--gs-muted)]"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" /><span>{previewQuality.next_actions[0]}</span></div> : <div className="mt-2 flex items-start gap-2 text-xs text-[var(--gs-muted)]"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" /><span>Technical foundation is complete. Review the private preview for brand accuracy, claims, assets, and conversion fit before publishing.</span></div>}
            </div>
          )}
          <div className="overflow-auto p-4">
            <div className={`mx-auto overflow-hidden rounded-xl border bg-white shadow-sm ${previewDevice === "mobile" ? "h-[680px] max-w-[390px]" : previewDevice === "tablet" ? "h-[620px] max-w-[768px]" : "h-[560px] w-full"}`} style={{ borderColor: "var(--gs-border)" }}>
              <iframe src={`${BACKEND_URL}/api/builder/projects/${previewId}/preview`} className="h-full w-full" title="Private project preview" data-testid="wa-preview-iframe"/>
            </div>
          </div>
          <div className="flex items-center gap-2 border-t px-4 py-3 text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}><ShieldCheck className="h-4 w-4 text-emerald-600" />This draft is private. Preview does not publish it to a public domain.</div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 2) Faceless Channel Builder
// ============================================================
function ChannelBuilder({ color }) {
  const [niche, setNiche] = useState("");
  const [style, setStyle] = useState("energetic");
  const [freq, setFreq] = useState(5);
  const [lang, setLang] = useState("hinglish");
  const [orientation, setOrientation] = useState("9:16");
  const [busy, setBusy] = useState(false);
  const [channels, setChannels] = useState([]);
  const [active, setActive] = useState(null);

  const load = async () => { try { const r = await api.get("/builder/channel"); setChannels(r.data.items || []); } catch (e) { toast.error("Couldn't load channels — refresh to retry"); } };
  useEffect(() => { load(); }, []);

  const plan = async () => {
    if (niche.trim().length < 3) return toast.error("Niche too short");
    setBusy(true); toast.loading("Planning your 30-day channel…", { id: "ch", duration: 60000 });
    try {
      const r = await api.post("/builder/channel/plan", { niche, style, posts_per_week: Number(freq), language: lang, orientation });
      toast.success(`Channel "${r.data.plan?.channel_name}" ready ✅`, { id: "ch" });
      setActive(r.data); setNiche(""); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "ch" }); }
    finally { setBusy(false); }
  };

  const execute = async (cid, max) => {
    toast.loading(`Queuing ${max} videos…`, { id: `ex${cid}` });
    try {
      const r = await api.post("/builder/channel/execute", { channel_id: cid, max_videos: max });
      toast.success(`${r.data.count} videos queued → Video Studio ✅`, { id: `ex${cid}` });
      load();
    } catch (e) { toast.error("Execute failed", { id: `ex${cid}` }); }
  };
  const del = async (cid) => { try { await api.delete(`/builder/channel/${cid}`); load(); toast.success("Deleted"); } catch (e) { toast.error("Delete failed — please retry"); } };

  return (
    <div className="space-y-4 mt-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Niche *</label>
        <Input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="e.g. AI tools for Indian students · Personal finance · Indian street food" data-testid="ch-niche"/>
      </div>
      <div className="grid md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Style</label>
          <Select value={style} onValueChange={setStyle}><SelectTrigger data-testid="ch-style"><SelectValue/></SelectTrigger>
            <SelectContent>{["energetic","calm","witty","authoritative","inspirational","story-driven"].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Posts / week</label>
          <Input type="number" value={freq} onChange={(e) => setFreq(e.target.value)} min={1} max={7} data-testid="ch-freq"/>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Language</label>
          <Select value={lang} onValueChange={setLang}><SelectTrigger data-testid="ch-lang"><SelectValue/></SelectTrigger>
            <SelectContent><SelectItem value="hinglish">Hinglish</SelectItem><SelectItem value="hindi">Hindi</SelectItem><SelectItem value="english">English</SelectItem></SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Orientation</label>
          <Select value={orientation} onValueChange={setOrientation}><SelectTrigger data-testid="ch-orient"><SelectValue/></SelectTrigger>
            <SelectContent><SelectItem value="9:16">9:16 Shorts</SelectItem><SelectItem value="16:9">16:9 Long</SelectItem><SelectItem value="1:1">1:1 Post</SelectItem></SelectContent>
          </Select>
        </div>
      </div>
      <Button onClick={plan} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid="ch-plan-btn">
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkle className="h-4 w-4 mr-2"/>}
        {busy ? "Planning…" : "Plan 30-day Channel"}
      </Button>

      <div className="space-y-2 max-h-80 overflow-y-auto" data-testid="ch-list">
        {channels.map((c) => (
          <Card key={c.id} className="p-3" data-testid={`ch-item-${c.id}`}>
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm truncate">{c.plan?.channel_name || c.niche}</div>
                <div className="text-[10px] text-[var(--gs-muted)]">{c.plan?.videos?.length || 0} videos planned · {c.status} · {c.executed_video_ids?.length || 0} executed</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => setActive(c)} data-testid={`ch-view-${c.id}`}>Calendar</Button>
              <Button size="sm" style={{ background: color, color: "white" }} onClick={() => execute(c.id, 5)} data-testid={`ch-exec-${c.id}`}>Execute 5</Button>
              <button onClick={() => del(c.id)} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
            </div>
          </Card>
        ))}
      </div>

      {active && (
        <Card className="p-4 mt-2" data-testid="ch-calendar-panel">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-display text-lg">{active.plan?.channel_name}</h4>
            <button onClick={() => setActive(null)} className="text-[var(--gs-muted)]">✕</button>
          </div>
          <div className="text-xs text-[var(--gs-muted)] mb-3">{active.plan?.channel_bio}</div>
          <div className="grid gap-1 max-h-72 overflow-y-auto">
            {(active.plan?.videos || []).map((v, i) => (
              <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
                <Badge variant="outline" className="text-[9px]">Day {v.day}</Badge>
                <span className="flex-1 truncate">{v.topic}</span>
                <Badge variant="secondary" className="text-[9px]">{v.format || "reel"}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================
// 3) Custom AI Agent Builder
// ============================================================
function AgentBuilder({ color }) {
  const [form, setForm] = useState({ name: "", role: "", system_prompt: "", param_keys_csv: "input", color: color, icon: "Bot" });
  const [busy, setBusy] = useState(false);
  const [agents, setAgents] = useState([]);
  const [active, setActive] = useState(null);
  const [runParams, setRunParams] = useState({});
  const [runOut, setRunOut] = useState(null);
  const [running, setRunning] = useState(false);

  const load = async () => { try { const r = await api.get("/builder/agent"); setAgents(r.data.items || []); } catch (e) { toast.error("Couldn't load agents — refresh to retry"); } };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (form.name.trim().length < 2) return toast.error("Name too short");
    if (form.system_prompt.trim().length < 20) return toast.error("System prompt too short");
    setBusy(true); toast.loading("Saving agent…", { id: "ag" });
    try {
      const param_keys = form.param_keys_csv.split(",").map(s => s.trim()).filter(Boolean);
      await api.post("/builder/agent", { ...form, param_keys });
      toast.success(`${form.name} created ✅`, { id: "ag" });
      setForm({ name: "", role: "", system_prompt: "", param_keys_csv: "input", color, icon: "Bot" });
      await load();
    } catch (e) { toast.error("Create failed", { id: "ag" }); }
    finally { setBusy(false); }
  };

  const openRunner = (a) => { setActive(a); setRunOut(null); const p = {}; (a.param_keys || []).forEach(k => p[k] = ""); setRunParams(p); };
  const run = async () => {
    setRunning(true); toast.loading("Running…", { id: "rn" });
    try {
      const r = await api.post(`/builder/agent/${active.id}/run`, { params: runParams });
      setRunOut(r.data); toast.success("Done ✅", { id: "rn" });
    } catch (e) { toast.error("Run failed", { id: "rn" }); }
    finally { setRunning(false); }
  };

  return (
    <div className="space-y-4 mt-4">
      <Card className="p-4 space-y-3">
        <div className="text-sm font-semibold flex items-center gap-2"><Plus className="h-4 w-4"/>Create custom agent</div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Agent name *</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Blog Writer Bot" data-testid="ag-name"/>
          </div>
          <div>
            <label className="text-xs text-[var(--gs-muted)]">Role description</label>
            <Input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="Writes SEO-optimized Hindi blog posts" data-testid="ag-role"/>
          </div>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">System prompt *</label>
          <Textarea rows={4} value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            placeholder="You are a blog writer for Indian audiences. Given a topic, output JSON: {title, intro, sections:[{h2, body}], conclusion, tags}."
            data-testid="ag-sys"/>
        </div>
        <div>
          <label className="text-xs text-[var(--gs-muted)]">Input parameter names (comma-separated)</label>
          <Input value={form.param_keys_csv} onChange={(e) => setForm({ ...form, param_keys_csv: e.target.value })} placeholder="topic, audience, tone" data-testid="ag-params"/>
        </div>
        <Button onClick={create} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid="ag-create-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Plus className="h-4 w-4 mr-2"/>}
          {busy ? "Saving…" : "Create Agent"}
        </Button>
      </Card>

      <div className="space-y-2">
        <div className="text-sm font-semibold">Your custom agents · {agents.length}</div>
        {agents.length === 0 && <Card className="p-4 text-center text-xs text-[var(--gs-muted)]">No custom agents yet.</Card>}
        <div className="grid md:grid-cols-2 gap-2">
          {agents.map((a) => (
            <Card key={a.id} className="p-3 flex items-center gap-2" data-testid={`ag-card-${a.id}`}>
              <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: `${a.color}22` }}>
                <Icons.Bot className="h-4 w-4" style={{ color: a.color }}/>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{a.name}</div>
                <div className="text-[10px] text-[var(--gs-muted)] truncate">{a.role}</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => openRunner(a)} data-testid={`ag-run-${a.id}`}><Play className="h-3.5 w-3.5"/></Button>
              <button onClick={async () => { await api.delete(`/builder/agent/${a.id}`); load(); }} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
            </Card>
          ))}
        </div>
      </div>

      {active && (
        <Card className="p-4 mt-2" data-testid="ag-runner-panel">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-display text-lg">{active.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)]">{active.role}</div>
            </div>
            <button onClick={() => setActive(null)} className="text-[var(--gs-muted)]">✕</button>
          </div>
          {(active.param_keys || []).map((k) => (
            <div key={k} className="mb-2">
              <label className="text-xs text-[var(--gs-muted)] capitalize">{k}</label>
              <Textarea rows={2} value={runParams[k] ?? ""} onChange={(e) => setRunParams({ ...runParams, [k]: e.target.value })} data-testid={`ag-param-${k}`}/>
            </div>
          ))}
          <Button onClick={run} disabled={running} className="w-full text-white" style={{ background: color }} data-testid="ag-run-btn">
            {running ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Play className="h-4 w-4 mr-2"/>}Run
          </Button>
          {runOut && (
            <pre className="mt-3 text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl max-h-64 overflow-auto" data-testid="ag-output">
              {JSON.stringify(runOut.parsed || runOut, null, 2)}
            </pre>
          )}
        </Card>
      )}
    </div>
  );
}

// ============================================================
// 4-6) Starter Kit builders (mobileapp / fullstack / blog)
// ============================================================
function StarterBuilder({ color, kind, placeholder }) {
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState([]);

  const load = useCallback(async () => { try { const r = await api.get("/builder/starter"); setItems((r.data.items || []).filter(x => x.kind === kind)); } catch (e) { toast.error("Couldn't load starters — refresh to retry"); } }, [kind]);
  useEffect(() => { load(); }, [load]);

  const build = async () => {
    if (prompt.trim().length < 4) return toast.error("Prompt too short");
    setBusy(true); toast.loading("Generating starter kit…", { id: "st", duration: 60000 });
    try {
      const r = await api.post("/builder/starter", { kind, prompt, app_name: name });
      toast.success(`Ready · ${(r.data.size_bytes / 1024).toFixed(1)} KB ✅`, { id: "st" });
      setPrompt(""); setName(""); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed", { id: "st" }); }
    finally { setBusy(false); }
  };

  const del = async (sid) => { try { await api.delete(`/builder/starter/${sid}`); load(); toast.success("Deleted"); } catch (e) { toast.error("Delete failed — please retry"); } };

  return (
    <div className="space-y-4 mt-4">
      <div>
        <label className="text-xs text-[var(--gs-muted)]">Prompt *</label>
        <Textarea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder={placeholder} data-testid={`st-${kind}-prompt`}/>
      </div>
      <div>
        <label className="text-xs text-[var(--gs-muted)]">App name (optional)</label>
        <Input value={name} onChange={(e) => setName(e.target.value)} data-testid={`st-${kind}-name`}/>
      </div>
      <Button onClick={build} disabled={busy} className="w-full text-white" style={{ background: color }} data-testid={`st-${kind}-build`}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Download className="h-4 w-4 mr-2"/>}
        {busy ? "Building starter…" : "Generate Starter Kit"}
      </Button>

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {items.map((it) => (
          <Card key={it.id} className="p-3 flex items-center gap-2" data-testid={`st-${kind}-item-${it.id}`}>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{it.name}</div>
              <div className="text-[10px] text-[var(--gs-muted)] truncate">{it.prompt}</div>
            </div>
            <Badge variant="outline" className="text-[10px]">{(it.size_bytes / 1024).toFixed(1)} KB</Badge>
            <button type="button" onClick={() => downloadAuthenticated(it.download_url, `${it.name || "starter"}-starter.zip`)} className="p-2 text-[var(--gs-muted)] hover:text-[var(--gs-teal)]" title="Download" aria-label={`Download ${it.name || "starter"} starter kit`} data-testid={`st-download-${it.id}`}><Download className="h-4 w-4"/></button>
            <button onClick={() => del(it.id)} className="text-rose-500"><Trash2 className="h-4 w-4"/></button>
          </Card>
        ))}
      </div>

      {kind === "mobileapp" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to run:</strong> Unzip → <code>npm install</code> → <code>npx expo start</code> → scan QR with Expo Go app.
        </div>
      )}
      {kind === "fullstack" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to run:</strong> Unzip → <code>docker compose up --build</code> → Backend at :8001, Frontend at :5173.
        </div>
      )}
      {kind === "blog" && (
        <div className="text-[11px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-xl">
          <strong>How to deploy:</strong> Unzip → drag folder to Netlify/Vercel drop, or open <code>index.html</code> locally.
        </div>
      )}
    </div>
  );
}
