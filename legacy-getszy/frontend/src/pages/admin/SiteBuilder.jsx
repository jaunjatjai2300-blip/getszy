import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Globe, Plus, Trash2, Eye, Code2, Copy, Loader2, Sparkles, GripVertical, Image, Type, Layout } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

let _id = () => Math.random().toString(36).slice(2,8);

const SECTION_TYPES = [
  { value:"hero",       label:"Hero Banner",     icon:"🦸", desc:"Big headline + CTA button" },
  { value:"features",   label:"Features Grid",   icon:"⚡", desc:"3-6 feature cards" },
  { value:"pricing",    label:"Pricing Table",   icon:"💰", desc:"Plans + prices" },
  { value:"testimonial",label:"Testimonials",    icon:"💬", desc:"Customer reviews" },
  { value:"faq",        label:"FAQ Accordion",   icon:"❓", desc:"Questions & answers" },
  { value:"cta",        label:"Call to Action",  icon:"🎯", desc:"Button section" },
  { value:"about",      label:"About Section",   icon:"👋", desc:"Company story" },
  { value:"contact",    label:"Contact Form",    icon:"📬", desc:"Get in touch" },
  { value:"gallery",    label:"Image Gallery",   icon:"🖼", desc:"Product/portfolio images" },
  { value:"stats",      label:"Stats Bar",       icon:"📊", desc:"Key numbers" },
];

const THEMES = [
  { value:"default", label:"Default (Getszy)", primary:"#2F7E7A" },
  { value:"dark",    label:"Dark Mode",         primary:"#1a1a2e" },
  { value:"minimal", label:"Minimal White",     primary:"#000000" },
  { value:"bold",    label:"Bold & Bright",     primary:"#7C3AED" },
  { value:"india",   label:"India (Saffron)",   primary:"#FF6B35" },
];

function SectionCard({ section, index, onChange, onDelete }) {
  const st = SECTION_TYPES.find(s=>s.value===section.type);
  return (
    <div className="p-4 bg-[var(--gs-surface-2)] rounded-xl border border-[var(--gs-border)] space-y-3">
      <div className="flex items-center gap-2">
        <GripVertical className="h-4 w-4 text-[var(--gs-muted)] flex-shrink-0"/>
        <span className="text-lg">{st?.icon||"📄"}</span>
        <span className="text-xs font-bold text-[var(--gs-teal)] bg-[var(--gs-teal-soft)] px-2 py-0.5 rounded-full">{st?.label||section.type}</span>
        <Input value={section.heading||""} onChange={e=>onChange({...section,heading:e.target.value})} placeholder="Section heading…" className="h-7 text-xs flex-1"/>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/></Button>
      </div>
      <Textarea value={section.content||""} onChange={e=>onChange({...section,content:e.target.value})} placeholder={section.type==="hero"?"Main headline + subtext…":section.type==="features"?"Feature 1: Title | Description\nFeature 2: Title | Description":section.type==="faq"?"Q: Question?\nA: Answer\n\nQ: Question 2?\nA: Answer 2":"Content…"} rows={3} className="text-xs resize-none"/>
      {(section.type==="hero"||section.type==="cta") && (
        <div className="grid grid-cols-2 gap-2">
          <Input value={section.ctaText||""} onChange={e=>onChange({...section,ctaText:e.target.value})} placeholder="CTA button text…" className="h-7 text-xs"/>
          <Input value={section.ctaUrl||""} onChange={e=>onChange({...section,ctaUrl:e.target.value})} placeholder="CTA URL…" className="h-7 text-xs"/>
        </div>
      )}
      {section.type==="pricing" && (
        <Textarea value={section.plans||""} onChange={e=>onChange({...section,plans:e.target.value})} placeholder={"Starter: ₹499/mo | 5 videos, 50 images\nPro: ₹999/mo | Unlimited videos\nEnterprise: Custom pricing"} rows={3} className="text-xs resize-none"/>
      )}
    </div>
  );
}

function SitePreview({ site }) {
  const theme = THEMES.find(t=>t.value===site.theme)||THEMES[0];
  const isDark = site.theme==="dark";
  return (
    <div className={`rounded-xl overflow-hidden border-2 border-[var(--gs-border)] ${isDark?"bg-[#0d0d0d] text-white":"bg-white text-gray-900"}`}>
      <div className="p-3 border-b flex items-center gap-2" style={{background:theme.primary}}>
        <div className="flex gap-1.5"><div className="h-3 w-3 rounded-full bg-red-400"/><div className="h-3 w-3 rounded-full bg-yellow-400"/><div className="h-3 w-3 rounded-full bg-green-400"/></div>
        <div className="flex-1 mx-3 h-5 rounded-full bg-white/20 text-[10px] text-white/80 flex items-center px-3">{site.domain||"yoursite.com"}</div>
      </div>
      <div className="max-h-96 overflow-y-auto p-4 space-y-4 text-xs">
        {site.sections.map((s,i) => {
          const st = SECTION_TYPES.find(x=>x.value===s.type);
          return (
            <div key={i} className={`p-3 rounded-lg border ${isDark?"border-white/10 bg-white/5":"border-gray-100 bg-gray-50"}`}>
              <p className="font-bold text-[10px] uppercase tracking-wider mb-1" style={{color:theme.primary}}>{st?.icon} {st?.label}</p>
              {s.heading && <p className="font-semibold">{s.heading}</p>}
              {s.content && <p className={`text-[10px] mt-1 ${isDark?"text-gray-400":"text-gray-500"}`}>{s.content.slice(0,100)}{s.content.length>100?"…":""}</p>}
              {s.ctaText && <button className="mt-2 px-3 py-1 rounded-lg text-white text-[10px] font-semibold" style={{background:theme.primary}}>{s.ctaText}</button>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function SiteBuilder() {
  const [site, setSite] = useState({
    name: "My Website", domain: "", theme: "default",
    sections: [
      { id:_id(), type:"hero",     heading:"India ka #1 AI Business OS", content:"Apna business automate karo — videos, products, analytics, sab ek jagah.", ctaText:"Free Trial Shuru Karo", ctaUrl:"#" },
      { id:_id(), type:"features", heading:"Kya milega aapko", content:"Video Studio: Professional videos banao AI se\nAI Images: FLUX HD images seconds mein\nCopilot: 24/7 AI business advisor" },
      { id:_id(), type:"pricing",  heading:"Simple Pricing", plans:"Starter: ₹499/mo | 5 videos, 50 images\nPro: ₹999/mo | Unlimited\nEnterprise: Custom" },
      { id:_id(), type:"cta",      heading:"Ready ho? Abhi shuru karo!", content:"", ctaText:"14-day Free Trial", ctaUrl:"#signup" },
    ]
  });
  const [preview, setPreview] = useState(false);
  const [generating, setGenerating] = useState(false);

  const addSection = (type) => setSite(s=>({...s, sections:[...s.sections,{ id:_id(), type, heading:"", content:"" }]}));
  const updateSection = (id,data) => setSite(s=>({...s, sections:s.sections.map(x=>x.id===id?data:x)}));
  const deleteSection = (id) => setSite(s=>({...s, sections:s.sections.filter(x=>x.id!==id)}));

  const generateContent = async () => {
    if (!site.name.trim()) { toast.error("Site ka naam likhein"); return; }
    setGenerating(true);
    try {
      const r = await api.post("/admin/ai-platform/playground", {
        model:"llama-3.1-8b-instant", provider:"groq",
        system:"You are a website copywriter for Indian SaaS products. Write compelling, conversion-focused copy in Hinglish.",
        message:`Write website copy for: "${site.name}". Generate content for each section: ${site.sections.map(s=>s.type).join(", ")}. For each section provide: heading and 2-3 lines of content. Keep it benefit-focused for Indian market. Return as JSON array with: type, heading, content.`,
        temperature:0.7, max_tokens:1200
      });
      try {
        const text = r.data.response||"";
        const match = text.match(/\[[\s\S]*\]/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          setSite(s=>({...s, sections: parsed.map((p,i)=>({ ...s.sections[i], id:s.sections[i]?.id||_id(), ...p }))}));
          toast.success("Website content generate ho gaya!");
        }
      } catch { toast.error("Parse error"); }
    } catch { toast.error("AI unavailable"); }
    finally { setGenerating(false); }
  };

  const exportHTML = () => {
    const theme = THEMES.find(t=>t.value===site.theme)||THEMES[0];
    const html = `<!DOCTYPE html><html><head><title>${site.name}</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:sans-serif;color:#111;}h1{font-size:2.5rem;}h2{font-size:1.8rem;}p{line-height:1.6;color:#555;}.btn{background:${theme.primary};color:#fff;padding:12px 28px;border-radius:8px;display:inline-block;text-decoration:none;font-weight:600;}.section{padding:60px 20px;max-width:900px;margin:0 auto;}</style></head><body>` +
      site.sections.map(s=>`<div class="section"><h2>${s.heading||""}</h2><p>${s.content||""}</p>${s.ctaText?`<br><a href="${s.ctaUrl||"#"}" class="btn">${s.ctaText}</a>`:""}</div>`).join("") +
      `</body></html>`;
    const blob = new Blob([html],{type:"text/html"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download=`${site.name||"site"}.html`; a.click();
    toast.success("HTML file download ho gayi!");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Globe className="h-7 w-7 text-blue-600"/>Website Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Section-by-section website banao — AI content ke saath</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={()=>setPreview(p=>!p)}><Eye className="h-3.5 w-3.5 mr-1"/>{preview?"Edit":"Preview"}</Button>
          <Button variant="outline" size="sm" onClick={exportHTML}><Code2 className="h-3.5 w-3.5 mr-1"/>Export HTML</Button>
          <Button size="sm" onClick={generateContent} disabled={generating} style={{background:"var(--gs-teal)",color:"#fff"}}>
            {generating?<Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/>:<Sparkles className="h-3.5 w-3.5 mr-1"/>}AI Content
          </Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="grid md:grid-cols-3 gap-3">
          <Input value={site.name} onChange={e=>setSite(s=>({...s,name:e.target.value}))} placeholder="Site/Product name…"/>
          <Input value={site.domain||""} onChange={e=>setSite(s=>({...s,domain:e.target.value}))} placeholder="Domain (e.g. getszy.com)"/>
          <Select value={site.theme} onValueChange={v=>setSite(s=>({...s,theme:v}))}>
            <SelectTrigger><SelectValue placeholder="Theme…"/></SelectTrigger>
            <SelectContent>{THEMES.map(t=><SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex gap-2 mt-3">
          <Badge variant="outline">{site.sections.length} sections</Badge>
        </div>
      </Card>

      {preview ? (
        <SitePreview site={site}/>
      ) : (
        <div className="grid lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-3">
            {site.sections.map((s,i) => (
              <SectionCard key={s.id} section={s} index={i} onChange={d=>updateSection(s.id,d)} onDelete={()=>deleteSection(s.id)}/>
            ))}
          </div>
          <div className="space-y-3">
            <Card className="p-4">
              <h3 className="font-semibold text-sm mb-3">Section Add Karo</h3>
              <div className="grid grid-cols-2 gap-1.5">
                {SECTION_TYPES.map(st => (
                  <button key={st.value} onClick={()=>addSection(st.value)} className="flex items-center gap-1.5 p-2 rounded-lg text-left text-xs hover:bg-[var(--gs-teal-soft)] hover:text-[var(--gs-teal)] transition-colors border border-[var(--gs-border)]">
                    <span>{st.icon}</span><span className="font-medium truncate">{st.label}</span>
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
