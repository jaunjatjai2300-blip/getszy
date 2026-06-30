import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { PenTool, TrendingUp, Zap, Flame, Repeat, Target, History, Sparkles, Loader2, Copy } from "lucide-react";
import { toast } from "sonner";

const FORMAT_OPTIONS = [
  { id: "youtube_short", label: "YouTube Short" },
  { id: "youtube_long", label: "YouTube long-form" },
  { id: "instagram_reel", label: "Instagram Reel" },
  { id: "facebook_reel", label: "Facebook Reel" },
  { id: "blog", label: "Blog Article" },
  { id: "tweet_thread", label: "X/Twitter Thread" },
  { id: "linkedin", label: "LinkedIn Post" },
];

const TONE_OPTIONS = ["energetic", "calm", "witty", "authoritative", "inspirational", "story-driven"];

function Section({ icon: Icon, title, subtitle, accent = "var(--gs-teal)", children }) {
  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: `${accent}22` }}>
          <Icon className="h-5 w-5" style={{ color: accent }} />
        </div>
        <div className="flex-1">
          <h3 className="font-display text-xl">{title}</h3>
          {subtitle && <p className="text-xs text-[var(--gs-muted)] mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {children}
    </Card>
  );
}

function JsonView({ data, testid }) {
  if (!data) return null;
  return (
    <div className="relative">
      <button
        onClick={() => { navigator.clipboard.writeText(JSON.stringify(data, null, 2)); toast.success("Copied"); }}
        className="absolute top-2 right-2 text-[10px] text-[var(--gs-muted)] hover:text-[var(--gs-ink)] flex items-center gap-1"
      >
        <Copy className="h-3 w-3" /> copy
      </button>
      <pre className="text-[11px] bg-[var(--gs-surface-2)] p-3 pr-14 rounded-xl max-h-96 overflow-auto" data-testid={testid}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default function CreatorOS() {
  const [providers, setProviders] = useState(null);
  const [history, setHistory] = useState([]);

  // Script writer state
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("youtube_short");
  const [tone, setTone] = useState("energetic");
  const [language, setLanguage] = useState("hinglish");
  const [scriptBusy, setScriptBusy] = useState(false);
  const [scriptOut, setScriptOut] = useState(null);

  // Trends
  const [niche, setNiche] = useState("");
  const [trendsBusy, setTrendsBusy] = useState(false);
  const [trendsOut, setTrendsOut] = useState(null);

  // Hook
  const [hook, setHook] = useState("");
  const [hookBusy, setHookBusy] = useState(false);
  const [hookOut, setHookOut] = useState(null);

  // Viral
  const [viralTitle, setViralTitle] = useState("");
  const [viralHook, setViralHook] = useState("");
  const [viralFormat, setViralFormat] = useState("reel");
  const [viralBusy, setViralBusy] = useState(false);
  const [viralOut, setViralOut] = useState(null);

  // Competitor
  const [competitor, setCompetitor] = useState("");
  const [compBusy, setCompBusy] = useState(false);
  const [compOut, setCompOut] = useState(null);

  // Repurpose
  const [repurposeTopic, setRepurposeTopic] = useState("");
  const [repurposeFormats, setRepurposeFormats] = useState(["youtube_short", "instagram_reel", "tweet_thread"]);
  const [repurposeBusy, setRepurposeBusy] = useState(false);
  const [repurposeOut, setRepurposeOut] = useState(null);

  const loadProviders = async () => {
    try { const r = await api.get("/creator/providers"); setProviders(r.data); } catch (e) {}
  };
  const loadHistory = async () => {
    try { const r = await api.get("/creator/history?limit=15"); setHistory(r.data.items || []); } catch (e) {}
  };
  useEffect(() => { loadProviders(); loadHistory(); }, []);

  const runScript = async () => {
    if (topic.trim().length < 4) return toast.error("Topic too short");
    setScriptBusy(true); setScriptOut(null);
    toast.loading("Writing script…", { id: "script", duration: 60000 });
    try {
      const r = await api.post("/creator/script", { topic, format, tone, language });
      setScriptOut(r.data);
      toast.success("Script ready ✅", { id: "script" });
      await loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Script generation failed", { id: "script" });
    } finally { setScriptBusy(false); }
  };

  const runTrends = async () => {
    setTrendsBusy(true); setTrendsOut(null);
    toast.loading("Forecasting trends…", { id: "trends", duration: 60000 });
    try {
      const r = await api.post("/creator/trends", { niche, count: 8 });
      setTrendsOut(r.data);
      toast.success("Trends ready ✅", { id: "trends" });
      await loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Trends failed", { id: "trends" });
    } finally { setTrendsBusy(false); }
  };

  const runHook = async () => {
    if (!hook.trim()) return toast.error("Enter a hook");
    setHookBusy(true); setHookOut(null);
    toast.loading("Scoring hook…", { id: "hook", duration: 30000 });
    try {
      const r = await api.post("/creator/score-hook", { hook });
      setHookOut(r.data);
      toast.success("Hook scored ✅", { id: "hook" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Hook scoring failed", { id: "hook" });
    } finally { setHookBusy(false); }
  };

  const runViral = async () => {
    if (!viralTitle.trim()) return toast.error("Enter a title");
    setViralBusy(true); setViralOut(null);
    toast.loading("Predicting viral score…", { id: "viral", duration: 30000 });
    try {
      const r = await api.post("/creator/viral-score", { content: { title: viralTitle, hook: viralHook, format: viralFormat } });
      setViralOut(r.data);
      toast.success("Viral score ready ✅", { id: "viral" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Viral score failed", { id: "viral" });
    } finally { setViralBusy(false); }
  };

  const runCompetitor = async () => {
    if (!competitor.trim()) return toast.error("Enter a competitor channel hint");
    setCompBusy(true); setCompOut(null);
    toast.loading("Analyzing competitor…", { id: "comp", duration: 45000 });
    try {
      const r = await api.post("/creator/competitor-gap", { competitor });
      setCompOut(r.data);
      toast.success("Gap analysis ready ✅", { id: "comp" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Analysis failed", { id: "comp" });
    } finally { setCompBusy(false); }
  };

  const runRepurpose = async () => {
    if (repurposeTopic.trim().length < 4) return toast.error("Topic too short");
    if (!repurposeFormats.length) return toast.error("Pick at least one format");
    setRepurposeBusy(true); setRepurposeOut(null);
    toast.loading("Repurposing across formats…", { id: "rep", duration: 90000 });
    try {
      const r = await api.post("/creator/repurpose", { long_script_topic: repurposeTopic, target_formats: repurposeFormats });
      setRepurposeOut(r.data);
      toast.success("Repurpose complete ✅", { id: "rep" });
      await loadHistory();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Repurpose failed", { id: "rep" });
    } finally { setRepurposeBusy(false); }
  };

  const toggleRepurposeFormat = (id) => {
    setRepurposeFormats((cur) => cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]);
  };

  return (
    <div className="space-y-6" data-testid="admin-creator-os-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Sparkles className="h-7 w-7 text-[var(--gs-teal)]" /> Creator OS
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            Script → Hook → Trend → Viral predict — all-in-one workflow for Indian creators.
          </p>
        </div>
        {providers && (
          <div className="flex flex-wrap gap-2" data-testid="creator-provider-badges">
            {Object.entries(providers.capabilities || {}).map(([cap, info]) => (
              <Badge key={cap} variant="outline" className="text-[10px]">
                {cap}: <span className="ml-1 font-semibold">{info.name}</span>
              </Badge>
            ))}
          </div>
        )}
      </div>

      <Tabs defaultValue="script" className="w-full">
        <TabsList className="grid grid-cols-3 md:grid-cols-6 w-full max-w-3xl">
          <TabsTrigger value="script" data-testid="tab-script"><PenTool className="h-4 w-4 mr-1 hidden md:inline" />Script</TabsTrigger>
          <TabsTrigger value="trends" data-testid="tab-trends"><TrendingUp className="h-4 w-4 mr-1 hidden md:inline" />Trends</TabsTrigger>
          <TabsTrigger value="hook" data-testid="tab-hook"><Zap className="h-4 w-4 mr-1 hidden md:inline" />Hook</TabsTrigger>
          <TabsTrigger value="viral" data-testid="tab-viral"><Flame className="h-4 w-4 mr-1 hidden md:inline" />Viral</TabsTrigger>
          <TabsTrigger value="repurpose" data-testid="tab-repurpose"><Repeat className="h-4 w-4 mr-1 hidden md:inline" />Repurpose</TabsTrigger>
          <TabsTrigger value="competitor" data-testid="tab-competitor"><Target className="h-4 w-4 mr-1 hidden md:inline" />Spy</TabsTrigger>
        </TabsList>

        <TabsContent value="script" className="mt-4">
          <Section icon={PenTool} title="Script Writer" subtitle="Multi-format scripts in Hinglish, Hindi, English — optimized for Indian audiences.">
            <div className="grid md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <label className="text-xs text-[var(--gs-muted)]">Topic *</label>
                <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. 5 AI tools every Indian student must use" data-testid="script-topic-input" />
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Format</label>
                <Select value={format} onValueChange={setFormat}>
                  <SelectTrigger data-testid="script-format-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{FORMAT_OPTIONS.map((f) => <SelectItem key={f.id} value={f.id}>{f.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Tone</label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger data-testid="script-tone-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{TONE_OPTIONS.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Language</label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger data-testid="script-language-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hinglish">Hinglish</SelectItem>
                    <SelectItem value="hindi">Hindi</SelectItem>
                    <SelectItem value="english">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={runScript} disabled={scriptBusy} className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="script-run-button">
              {scriptBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <PenTool className="h-4 w-4 mr-2" />}
              {scriptBusy ? "Writing…" : "Generate Script"}
            </Button>
            <JsonView data={scriptOut} testid="script-result" />
          </Section>
        </TabsContent>

        <TabsContent value="trends" className="mt-4">
          <Section icon={TrendingUp} title="Trend Predictor" subtitle="8 trending content topics for the next 14 days." accent="#e0a458">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Niche (optional)</label>
              <Input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="e.g. personal finance India" data-testid="trends-niche-input" />
            </div>
            <Button onClick={runTrends} disabled={trendsBusy} className="w-full bg-[#e0a458] hover:bg-[#e0a458]/90" data-testid="trends-run-button">
              {trendsBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <TrendingUp className="h-4 w-4 mr-2" />}
              {trendsBusy ? "Forecasting…" : "Predict Trends"}
            </Button>
            {trendsOut?.data?.predictions?.length > 0 && (
              <div className="grid md:grid-cols-2 gap-2" data-testid="trends-cards">
                {trendsOut.data.predictions.map((p, i) => (
                  <div key={i} className="gs-card p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">{p.topic}</span>
                      <Badge variant="outline">{p.trend_score}/100</Badge>
                    </div>
                    <div className="text-[11px] text-[var(--gs-muted)] mt-1">{p.why}</div>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      <Badge className="text-[9px]" variant="secondary">demand: {p.search_demand}</Badge>
                      <Badge className="text-[9px]" variant="secondary">comp: {p.competition}</Badge>
                      {p.format_recommendation && <Badge className="text-[9px]" variant="secondary">{p.format_recommendation}</Badge>}
                    </div>
                    {p.hook_idea && <div className="text-[11px] mt-2 italic">"{p.hook_idea}"</div>}
                  </div>
                ))}
              </div>
            )}
            <JsonView data={trendsOut} testid="trends-result" />
          </Section>
        </TabsContent>

        <TabsContent value="hook" className="mt-4">
          <Section icon={Zap} title="Hook Optimizer" subtitle="Score & rewrite your first 3 seconds." accent="#c97a87">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Hook *</label>
              <Textarea value={hook} onChange={(e) => setHook(e.target.value)} placeholder="Type your opening line…" data-testid="hook-input" />
            </div>
            <Button onClick={runHook} disabled={hookBusy} className="w-full bg-[#c97a87] hover:bg-[#c97a87]/90" data-testid="hook-run-button">
              {hookBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Zap className="h-4 w-4 mr-2" />}
              {hookBusy ? "Scoring…" : "Score Hook"}
            </Button>
            {hookOut?.score !== undefined && (
              <div className="gs-card p-4" data-testid="hook-score-card">
                <div className="flex items-center gap-3">
                  <div className="h-14 w-14 rounded-full grid place-items-center bg-[#c97a87]/20 text-[#c97a87] font-display text-2xl">{hookOut.score}</div>
                  <div className="flex-1 text-xs">{hookOut.rationale}</div>
                </div>
                {hookOut.suggested_rewrite && (
                  <div className="mt-3 p-3 bg-[var(--gs-surface-2)] rounded-xl text-sm">
                    <div className="text-[10px] text-[var(--gs-muted)] uppercase mb-1">Suggested rewrite</div>
                    {hookOut.suggested_rewrite}
                  </div>
                )}
              </div>
            )}
          </Section>
        </TabsContent>

        <TabsContent value="viral" className="mt-4">
          <Section icon={Flame} title="Viral Probability Score" subtitle="Pre-publish risk + drivers analysis." accent="#7c3aed">
            <div className="grid md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <label className="text-xs text-[var(--gs-muted)]">Title *</label>
                <Input value={viralTitle} onChange={(e) => setViralTitle(e.target.value)} data-testid="viral-title-input" />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs text-[var(--gs-muted)]">Hook (optional)</label>
                <Input value={viralHook} onChange={(e) => setViralHook(e.target.value)} data-testid="viral-hook-input" />
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Format</label>
                <Select value={viralFormat} onValueChange={setViralFormat}>
                  <SelectTrigger data-testid="viral-format-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reel">Reel/Short</SelectItem>
                    <SelectItem value="long">Long-form video</SelectItem>
                    <SelectItem value="post">Post/Thread</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={runViral} disabled={viralBusy} className="w-full bg-[#7c3aed] hover:bg-[#7c3aed]/90" data-testid="viral-run-button">
              {viralBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Flame className="h-4 w-4 mr-2" />}
              {viralBusy ? "Predicting…" : "Predict Viral Score"}
            </Button>
            {viralOut?.viral_score !== undefined && (
              <div className="gs-card p-4" data-testid="viral-score-card">
                <div className="flex items-center gap-3">
                  <div className="h-16 w-16 rounded-full grid place-items-center bg-[#7c3aed]/20 text-[#7c3aed] font-display text-3xl">{viralOut.viral_score}</div>
                  <div className="flex-1 text-xs">{viralOut.recommendation}</div>
                </div>
                {viralOut.drivers?.length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] text-[var(--gs-muted)] uppercase mb-1">Drivers</div>
                    <div className="flex flex-wrap gap-1">{viralOut.drivers.map((d, i) => <Badge key={i} variant="secondary" className="text-[10px]">{d}</Badge>)}</div>
                  </div>
                )}
                {viralOut.risks?.length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] text-rose-600 uppercase mb-1">Risks</div>
                    <div className="flex flex-wrap gap-1">{viralOut.risks.map((d, i) => <Badge key={i} className="text-[10px] bg-rose-100 text-rose-800">{d}</Badge>)}</div>
                  </div>
                )}
              </div>
            )}
          </Section>
        </TabsContent>

        <TabsContent value="repurpose" className="mt-4">
          <Section icon={Repeat} title="Multi-Format Repurpose" subtitle="One topic → reel, short, thread, blog — instantly." accent="#5d8f8e">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Topic *</label>
              <Input value={repurposeTopic} onChange={(e) => setRepurposeTopic(e.target.value)} data-testid="repurpose-topic-input" />
            </div>
            <div>
              <label className="text-xs text-[var(--gs-muted)] mb-2 block">Target formats</label>
              <div className="flex flex-wrap gap-2">
                {FORMAT_OPTIONS.map((f) => (
                  <button key={f.id} onClick={() => toggleRepurposeFormat(f.id)} data-testid={`repurpose-fmt-${f.id}`}
                    className={`text-xs px-3 py-1.5 rounded-full border transition ${repurposeFormats.includes(f.id) ? "bg-[var(--gs-teal)] text-white border-transparent" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}>
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={runRepurpose} disabled={repurposeBusy} className="w-full bg-[#5d8f8e] hover:bg-[#5d8f8e]/90" data-testid="repurpose-run-button">
              {repurposeBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Repeat className="h-4 w-4 mr-2" />}
              {repurposeBusy ? "Repurposing…" : `Repurpose into ${repurposeFormats.length} formats`}
            </Button>
            <JsonView data={repurposeOut} testid="repurpose-result" />
          </Section>
        </TabsContent>

        <TabsContent value="competitor" className="mt-4">
          <Section icon={Target} title="Competitor Gap Spy" subtitle="5 content gaps you can exploit." accent="#9b6a3f">
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Competitor channel / description *</label>
              <Textarea value={competitor} onChange={(e) => setCompetitor(e.target.value)} placeholder="e.g. CA Rachana Ranade — stocks education on YouTube" data-testid="competitor-input" />
            </div>
            <Button onClick={runCompetitor} disabled={compBusy} className="w-full bg-[#9b6a3f] hover:bg-[#9b6a3f]/90" data-testid="competitor-run-button">
              {compBusy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Target className="h-4 w-4 mr-2" />}
              {compBusy ? "Analyzing…" : "Find Content Gaps"}
            </Button>
            {compOut?.gaps?.length > 0 && (
              <div className="space-y-2" data-testid="competitor-gaps">
                {compOut.gaps.map((g, i) => (
                  <div key={i} className="gs-card p-3 text-sm">
                    <div className="font-semibold">{g.topic}</div>
                    <div className="text-[11px] text-[var(--gs-muted)] mt-1">{g.why_underserved}</div>
                    {g.angle && <div className="text-[11px] mt-1 italic">Angle: {g.angle}</div>}
                  </div>
                ))}
              </div>
            )}
          </Section>
        </TabsContent>
      </Tabs>

      <Section icon={History} title="Recent Creator Assets" subtitle="Last 15 generated assets" accent="#666">
        {history.length === 0 ? (
          <div className="text-sm text-[var(--gs-muted)] py-3">No assets yet — generate your first script above.</div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
            {history.map((h) => (
              <div key={h.id} className="py-2 flex items-center gap-3 text-sm" data-testid={`creator-history-${h.id}`}>
                <Badge variant="outline" className="text-[10px]">{h.kind || "asset"}</Badge>
                <span className="truncate flex-1">{h.topic || h.niche || h.id}</span>
                {h.format && <Badge variant="secondary" className="text-[10px]">{h.format}</Badge>}
                <span className="text-[10px] text-[var(--gs-muted)]">{new Date(h.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
