import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Layout, Loader2, Copy, RefreshCw, Sparkle } from "lucide-react";
import { toast } from "sonner";
import { useBuilderWebsiteOperation } from "@/hooks/useBuilderWebsiteOperation";
import { useBuilderPreviewToken } from "@/hooks/useBuilderPreviewToken";
import { OperationStatusCard } from "@/components/operation/OperationStatusCard";

const TEMPLATES = [
  { id:"saas", label:"SaaS Product", icon:"☁️", desc:"Hero + Features + Pricing + CTA" },
  { id:"startup", label:"Startup Landing", icon:"🚀", desc:"Bold hero + social proof + waitlist" },
  { id:"product", label:"Product Launch", icon:"📦", desc:"Launch page with countdown + features" },
  { id:"agency", label:"Digital Agency", icon:"🎨", desc:"Portfolio + services + contact" },
  { id:"course", label:"Online Course", icon:"🎓", desc:"Course landing with curriculum + enroll" },
  { id:"restaurant", label:"Restaurant", icon:"🍽️", desc:"Menu + gallery + reservation form" },
  { id:"doctor", label:"Doctor/Clinic", icon:"🏥", desc:"Services + team + appointment booking" },
  { id:"ecommerce", label:"Product Store", icon:"🛍️", desc:"Featured products + trust badges + cart" },
];

const STYLES = ["Modern Minimal","Bold & Colorful","Corporate Professional","Dark & Futuristic","Warm & Friendly","Indian Traditional"];
const COLORS = ["#00c2b2 (Teal)","#6366f1 (Indigo)","#0ea5e9 (Sky)","#10b981 (Emerald)","#f59e0b (Amber)","#ef4444 (Red)","#8b5cf6 (Violet)"];

export default function LandingPageBuilder() {
  const [form, setForm] = useState({ business_name:"", description:"", template:"saas", style:"Modern Minimal", primary_color:"#00c2b2 (Teal)", language:"Hindi/English mix", cta_text:"Abhi Start Karo", features:"" });
  const [result, setResult] = useState(null);
  const [tab, setTab] = useState("preview");

  const { operation, busy, start, recover, reset } = useBuilderWebsiteOperation({
    storageKey: "getszy_builder_landing_operation",
    noun: "landing page",
    onSucceeded: (project) => setResult(project),
  });
  useEffect(() => { recover(); }, []);

  const { previewUrl } = useBuilderPreviewToken(result?.id);

  const generate = async () => {
    if (!form.business_name || !form.description) return toast.error("Business name aur description chahiye");
    const prompt = `Create a complete, stunning landing page HTML for "${form.business_name}". Template: ${form.template}. Style: ${form.style}. Primary color: ${form.primary_color}. Language: ${form.language}.

Business description: ${form.description}

Key features: ${form.features || "AI-powered, Fast, Easy to use"}

CTA Button text: "${form.cta_text}"

Requirements:
- Full HTML5 page with embedded CSS (no external deps except Google Fonts)
- Responsive design (mobile + desktop)
- Sections: Hero, Features/Benefits, Social Proof, CTA, Footer
- Modern animations (CSS only)
- Include placeholder for logo, use emoji as icons
- WhatsApp/Contact button for Indian users
- Indian rupee pricing format if pricing section
- ${form.language === "Hindi/English mix" ? "Use Hinglish tone" : "Use professional English"}

Return ONLY the complete HTML code, nothing else.`;

    const brief = {
      brand_name: form.business_name,
      audience: form.language,
      primary_goal: form.cta_text,
      primary_cta: form.cta_text,
      offer: form.description,
      visual_style: form.style,
      proof_points: (form.features || "").split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 6),
    };
    const name = `${form.business_name} Landing Page`;
    try {
      await start({ prompt, name, brief });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Generation failed — try again");
    }
  };

  const regenerate = () => { reset(); setResult(null); };
  const copy = () => { navigator.clipboard?.writeText(result?.html_content || ""); toast.success("HTML copied!"); };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Layout className="h-7 w-7 text-[var(--gs-teal)]"/>Landing Page Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">AI se complete landing page — seconds mein</p>
        </div>
        {result && (
          <div className="flex gap-2">
            <div className="flex bg-[var(--gs-surface-2)] rounded-lg p-1 gap-1">
              {[["preview","👁 Preview"],["code","</> Code"]].map(([t,l]) => (
                <button key={t} onClick={() => setTab(t)} className={`text-xs px-3 py-1.5 rounded-md ${tab === t ? "bg-white shadow text-[var(--gs-teal)] font-medium" : "text-[var(--gs-muted)]"}`}>{l}</button>
              ))}
            </div>
            <Button variant="outline" size="sm" onClick={regenerate}><RefreshCw className="h-3.5 w-3.5 mr-1"/>Regenerate</Button>
            <Button size="sm" onClick={copy}><Copy className="h-3.5 w-3.5 mr-1"/>Copy HTML</Button>
          </div>
        )}
      </div>

      {result ? (
        <>
          {tab === "preview" && (
            <div className="border border-[var(--gs-border)] rounded-xl overflow-hidden" style={{ height: "600px" }}>
              {previewUrl ? (
                <iframe src={previewUrl} className="w-full h-full" title="Landing Page Preview" sandbox="allow-scripts allow-same-origin" />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-[var(--gs-muted)]">Preview loading…</div>
              )}
            </div>
          )}
          {tab === "code" && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-[var(--gs-muted)]">{(result.html_content || "").length} characters · Full HTML</p>
                <div className="flex gap-2">
                  <button onClick={copy} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy</button>
                </div>
              </div>
              <pre className="bg-[#0a0a0a] text-green-400 text-xs p-4 rounded-xl overflow-auto font-mono max-h-[500px] whitespace-pre-wrap">{result.html_content}</pre>
            </div>
          )}
        </>
      ) : operation ? (
        <div className="rounded-xl border p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
          <OperationStatusCard operation={operation} noun="landing page" />
          {busy && (
            <div className="mt-4 flex flex-col items-center justify-center gap-3">
              <div className="relative">
                <div className="h-16 w-16 rounded-full border-4 border-[var(--gs-teal)]/20 border-t-[var(--gs-teal)] animate-spin" />
                <Layout className="h-6 w-6 text-[var(--gs-teal)] absolute inset-0 m-auto" />
              </div>
              <p className="text-sm text-[var(--gs-muted)]">Landing page ban raha hai…</p>
            </div>
          )}
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6 max-w-4xl">
          <div className="space-y-4">
            <div><label className="text-xs font-medium mb-1.5 block">Business / Product Name *</label>
              <Input className="h-10 text-sm" placeholder="e.g. Doctorzap, FoodKart, LearnAI" value={form.business_name} onChange={e => setForm(p => ({ ...p, business_name: e.target.value }))} /></div>
            <div><label className="text-xs font-medium mb-1.5 block">What does it do? (2-3 lines) *</label>
              <Textarea rows={3} className="text-sm" placeholder="AI-powered hospital management system jo doctors aur patients ko connect karta hai. Appointment booking, billing, aur EMR sab ek jagah." value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} /></div>
            <div><label className="text-xs font-medium mb-1.5 block">Key Features / Benefits (one per line)</label>
              <Textarea rows={3} className="text-sm" placeholder={"24/7 AI support\nInstant booking\n₹99 se shuru"} value={form.features} onChange={e => setForm(p => ({ ...p, features: e.target.value }))} /></div>
            <div><label className="text-xs font-medium mb-1.5 block">CTA Button Text</label>
              <Input className="h-9 text-sm" placeholder="Abhi Start Karo" value={form.cta_text} onChange={e => setForm(p => ({ ...p, cta_text: e.target.value }))} /></div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium mb-1.5 block">Template</label>
              <div className="grid grid-cols-2 gap-2">
                {TEMPLATES.map(t => (
                  <button key={t.id} onClick={() => setForm(p => ({ ...p, template: t.id }))}
                    className={`p-3 rounded-xl text-left border transition-all ${form.template === t.id ? "border-[var(--gs-teal)] bg-[var(--gs-teal-soft)]" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}>
                    <div className="text-xl mb-1">{t.icon}</div>
                    <p className="text-xs font-semibold">{t.label}</p>
                    <p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>
            <div><label className="text-xs font-medium mb-1.5 block">Design Style</label>
              <div className="flex flex-wrap gap-2">{STYLES.map(s => <button key={s} onClick={() => setForm(p => ({ ...p, style: s }))} className={`text-xs px-3 py-1.5 rounded-full border transition-all ${form.style === s ? "border-[var(--gs-teal)] bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]" : "border-[var(--gs-border)]"}`}>{s}</button>)}</div>
            </div>
            <div><label className="text-xs font-medium mb-1.5 block">Language</label>
              <Select value={form.language} onValueChange={v => setForm(p => ({ ...p, language: v }))}>
                <SelectTrigger className="h-9 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>{["Hindi/English mix (Hinglish)","English only","Hindi only"].map(l => <SelectItem key={l} value={l} className="text-xs">{l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <Button className="w-full h-11 bg-[var(--gs-teal)] text-base font-semibold" onClick={generate}>
              <Sparkle className="h-5 w-5 mr-2"/>AI se Generate Karo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
