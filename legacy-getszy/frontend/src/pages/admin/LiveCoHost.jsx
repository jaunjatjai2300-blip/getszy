import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Radio, Sparkle, Mic, Wand2, Loader2, ChevronRight, RefreshCw, Tv
} from "lucide-react";

const VIBES = ["energetic", "chill", "professional", "funny"];
const PLATFORMS = ["youtube", "instagram", "facebook", "linkedin", "kick"];

export default function LiveCoHost() {
  const [topics, setTopics] = useState([]);
  const [topic, setTopic] = useState("");
  const [vibe, setVibe] = useState("energetic");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [starting, setStarting] = useState(false);

  const [session, setSession] = useState(null);     // created session doc
  const [cue, setCue] = useState(null);              // current co-host cue
  const [progress, setProgress] = useState("");
  const [cta, setCta] = useState("");
  const [done, setDone] = useState(false);
  const [nexting, setNexting] = useState(false);

  const [hostLine, setHostLine] = useState("");
  const [suggested, setSuggested] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  const loadTopics = useCallback(async () => {
    try {
      const r = await api.get("/live/topics");
      setTopics(r.data.topics || []);
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { loadTopics(); }, [loadTopics]);

  const start = async () => {
    if (topic.trim().length < 4) { toast.error("Topic daalo (4+ chars)"); return; }
    setStarting(true);
    try {
      const r = await api.post("/live/session", {
        topic: topic.trim(), vibe, audience: audience.trim(), platform,
      });
      setSession(r.data);
      setCue(null); setDone(false); setCta(r.data.cta || ""); setProgress("");
      setSuggested(""); setHostLine("");
      toast.success("Live session ready — Neo co-hosting!");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not start session");
    } finally {
      setStarting(false);
    }
  };

  const nextCue = async () => {
    if (!session) return;
    setNexting(true);
    try {
      const r = await api.post(`/live/session/${session.id}/next`);
      if (r.data.done) {
        setDone(true);
        setCue(null);
        setCta(r.data.cta || cta);
      } else {
        setCue(r.data.cue);
        setCta(r.data.cta || "");
      }
      setProgress(r.data.progress || "");
    } catch (e) {
      toast.error("Could not fetch next cue");
    } finally {
      setNexting(false);
    }
  };

  const suggest = async () => {
    if (!session) return;
    if (!hostLine.trim()) { toast.error("Apni last line likho pehle"); return; }
    setSuggesting(true);
    try {
      const r = await api.post(`/live/session/${session.id}/suggest`, { transcript: hostLine.trim() });
      setSuggested(r.data.line || "");
    } catch (e) {
      toast.error("Suggestion fail hui");
    } finally {
      setSuggesting(false);
    }
  };

  const reset = () => {
    setSession(null); setCue(null); setDone(false); setCta(""); setProgress("");
    setSuggested(""); setHostLine("");
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <div className="h-9 w-9 rounded-xl bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] grid place-items-center">
          <Radio className="h-5 w-5" />
        </div>
        <div>
          <h1 className="font-display text-2xl">Live Co-Host</h1>
          <p className="text-xs text-[var(--gs-muted)]">Neo tumhari livestream ka co-host — opening, cues aur real-time lines.</p>
        </div>
      </div>

      {!session ? (
        <Card className="p-5 mt-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] mb-2">Suggested topics</div>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {(topics.length ? topics : [
              "Q&A with my audience — clear their top doubts live",
              "Product launch livestream — build the hype",
              "Behind the scenes of my creator journey",
            ]).map((t, i) => (
              <button key={i} onClick={() => setTopic(t)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] text-[var(--gs-ink)]" data-testid="live-topic-chip">
                {t}
              </button>
            ))}
          </div>

          <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">Show topic</label>
          <Textarea rows={2} value={topic} onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. AI tools ke saath income kaise badhayein — live Q&A"
            className="mb-3 mt-1" data-testid="live-topic-input" />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">Vibe</label>
              <select value={vibe} onChange={(e) => setVibe(e.target.value)}
                className="w-full text-xs h-9 rounded-lg border bg-white px-2 mt-1" style={{ borderColor: "var(--gs-border)" }} data-testid="live-vibe-select">
                {VIBES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">Platform</label>
              <select value={platform} onChange={(e) => setPlatform(e.target.value)}
                className="w-full text-xs h-9 rounded-lg border bg-white px-2 mt-1" style={{ borderColor: "var(--gs-border)" }} data-testid="live-platform-select">
                {PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)]">Audience (optional)</label>
              <Input value={audience} onChange={(e) => setAudience(e.target.value)}
                placeholder="Indian students" className="text-xs h-9 mt-1" data-testid="live-audience-input" />
            </div>
          </div>

          <Button onClick={start} disabled={starting} className="bg-[var(--gs-teal)] mt-4 w-full sm:w-auto" data-testid="live-start-btn">
            {starting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Tv className="h-4 w-4 mr-1" />}
            Start Live Session
          </Button>
        </Card>
      ) : (
        <div className="space-y-4 mt-4">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="text-[10px]">{session.platform}</Badge>
            <Badge variant="outline" className="text-[10px]">{session.vibe}</Badge>
            <span className="text-sm font-semibold flex-1 truncate">{session.topic}</span>
            <Button size="sm" variant="ghost" onClick={reset} data-testid="live-new-btn"><RefreshCw className="h-3 w-3 mr-1" />New</Button>
          </div>

          {/* Teleprompter */}
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Mic className="h-4 w-4 text-[var(--gs-teal)]" />
              <span className="font-semibold text-sm">Teleprompter</span>
              {progress && <Badge variant="outline" className="text-[9px] ml-auto">{progress}</Badge>}
            </div>

            {!cue && !done && (
              <div className="text-sm p-3 bg-[var(--gs-surface-2)] rounded-xl mb-3">
                <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Opening</div>
                {session.opening || "—"}
              </div>
            )}

            {cue && (
              <div className="text-sm p-3 bg-[var(--gs-teal)]/10 rounded-xl mb-3" data-testid="live-cue">
                <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">{cue.title}</div>
                {cue.line}
              </div>
            )}

            {done && (
              <div className="text-sm p-3 bg-emerald-50 text-emerald-800 rounded-xl mb-3">
                <div className="text-[10px] uppercase text-emerald-600 mb-1">CTA — repeat karo</div>
                {cta || "Thanks for watching! Subscribe & comment."}
              </div>
            )}

            <div className="flex gap-2">
              <Button size="sm" onClick={nextCue} disabled={nexting || done} className="bg-[var(--gs-teal)]" data-testid="live-next-btn">
                {nexting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <ChevronRight className="h-3 w-3 mr-1" />}
                {done ? "All cues done" : "Next cue"}
              </Button>
            </div>
          </Card>

          {/* Real-time suggestion */}
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Wand2 className="h-4 w-4 text-[var(--gs-teal)]" />
              <span className="font-semibold text-sm">Co-host suggestion (real-time)</span>
            </div>
            <p className="text-[11px] text-[var(--gs-muted)] mb-2">Jo tumne abhi bola, woh yahan likho — Neo co-host ki next line suggest karega.</p>
            <Textarea rows={2} value={hostLine} onChange={(e) => setHostLine(e.target.value)}
              placeholder="e.g. Toh pehla tool hai NotebookLM jo research automate karta hai…"
              className="mb-2" data-testid="live-host-input" />
            <Button size="sm" onClick={suggest} disabled={suggesting} className="bg-[var(--gs-teal)] mb-3" data-testid="live-suggest-btn">
              {suggesting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Sparkle className="h-3 w-3 mr-1" />}
              Suggest co-host line
            </Button>
            {suggested && (
              <div className="text-sm p-3 bg-[var(--gs-surface-2)] rounded-xl" data-testid="live-suggestion">
                <div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Neo says</div>
                {suggested}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
