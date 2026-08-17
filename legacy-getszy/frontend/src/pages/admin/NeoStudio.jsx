import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "sonner";
import { Sparkles, Copy, Languages, RefreshCw } from "lucide-react";

const TYPES = [
  { v: "product_description", l: "Product Description" },
  { v: "ad_copy", l: "Ad Copy" },
  { v: "email", l: "Email" },
  { v: "sms", l: "SMS" },
  { v: "social_post", l: "Social Post" },
  { v: "blog_idea", l: "Blog Idea" },
  { v: "seo_meta", l: "SEO Meta" },
];
const LANGS = [
  { v: "en", l: "English" }, { v: "hi", l: "Hindi" }, { v: "hinglish", l: "Hinglish" },
  { v: "ta", l: "Tamil" }, { v: "te", l: "Telugu" }, { v: "bn", l: "Bengali" },
  { v: "gu", l: "Gujarati" }, { v: "mr", l: "Marathi" }, { v: "es", l: "Spanish" },
  { v: "fr", l: "French" }, { v: "ar", l: "Arabic" }, { v: "zh", l: "Chinese" },
];
const TONES = ["professional", "playful", "luxury", "urgent", "friendly", "bold"];

export default function NeoStudio() {
  const [type, setType] = useState("product_description");
  const [language, setLanguage] = useState("en");
  const [tone, setTone] = useState("professional");
  const [maxWords, setMaxWords] = useState(120);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [features, setFeatures] = useState("");
  const [audience, setAudience] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const [trText, setTrText] = useState("");
  const [trTo, setTrTo] = useState("hi");
  const [trResult, setTrResult] = useState(null);
  const [trLoading, setTrLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/admin/neo-content/generate", {
        type, language, tone, max_words: maxWords,
        context: {
          name, category,
          features: features.split(",").map((s) => s.trim()).filter(Boolean),
          audience,
        },
      });
      setResult(data);
    } catch (e) {
      toast.error("Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const translate = async () => {
    if (!trText.trim()) return toast.error("Enter text to translate");
    setTrLoading(true);
    try {
      const { data } = await api.post("/admin/neo-content/translate", { text: trText, to: trTo });
      setTrResult(data);
    } catch (e) {
      toast.error("Translation failed");
    } finally {
      setTrLoading(false);
    }
  };

  const copy = (txt) => {
    navigator.clipboard?.writeText(txt);
    toast.success("Copied");
  };

  return (
    <div className="space-y-6" data-testid="admin-neostudio-page">
      <div className="flex items-center gap-2">
        <Sparkles className="h-6 w-6 text-[var(--gs-teal)]" />
        <h1 className="text-2xl font-semibold">Neo Studio — Universal Content Engine</h1>
      </div>
      <p className="text-sm text-[var(--gs-muted)] -mt-3">
        Generate and translate any commerce content in any language. Bharat-scale, AI-native.
      </p>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="p-5 space-y-3">
          <h3 className="font-semibold text-sm">Generate</h3>
          <div className="grid grid-cols-2 gap-2">
            <Select value={type} onValueChange={setType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{TYPES.map((t) => <SelectItem key={t.v} value={t.v}>{t.l}</SelectItem>)}</SelectContent>
            </Select>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{LANGS.map((l) => <SelectItem key={l.v} value={l.v}>{l.l}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Select value={tone} onValueChange={setTone}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{TONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
            <Input type="number" value={maxWords} onChange={(e) => setMaxWords(parseInt(e.target.value) || 120)} placeholder="Max words" />
          </div>
          <Input placeholder="Product / brand name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
          <Input placeholder="Features (comma separated)" value={features} onChange={(e) => setFeatures(e.target.value)} />
          <Input placeholder="Audience" value={audience} onChange={(e) => setAudience(e.target.value)} />
          <Button className="w-full bg-[var(--gs-teal)]" onClick={generate} disabled={loading}>
            {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
            Generate Content
          </Button>
          {result && (
            <div className="rounded-lg bg-[var(--gs-surface-2)] p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">
                  {result.source === 'ai' ? 'AI generated' : 'Template'} · {result.language}
                </span>
                <Button size="sm" variant="ghost" onClick={() => copy(result.content)}><Copy className="h-3.5 w-3.5" /></Button>
              </div>
              <pre className="whitespace-pre-wrap text-xs">{result.content}</pre>
            </div>
          )}
        </Card>

        <Card className="p-5 space-y-3">
          <h3 className="font-semibold text-sm flex items-center gap-2">
            <Languages className="h-4 w-4 text-[var(--gs-teal)]" /> Translate
          </h3>
          <Textarea rows={5} placeholder="Paste text to translate..." value={trText} onChange={(e) => setTrText(e.target.value)} />
          <div className="flex gap-2">
            <Select value={trTo} onValueChange={setTrTo}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>{LANGS.map((l) => <SelectItem key={l.v} value={l.v}>{l.l}</SelectItem>)}</SelectContent>
            </Select>
            <Button className="flex-1" onClick={translate} disabled={trLoading}>
              {trLoading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Languages className="h-4 w-4 mr-2" />}
              Translate
            </Button>
          </div>
          {trResult && (
            <div className="rounded-lg bg-[var(--gs-surface-2)] p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">→ {trResult.to}</span>
                <Button size="sm" variant="ghost" onClick={() => copy(trResult.translated)}><Copy className="h-3.5 w-3.5" /></Button>
              </div>
              <pre className="whitespace-pre-wrap text-xs">{trResult.translated}</pre>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
