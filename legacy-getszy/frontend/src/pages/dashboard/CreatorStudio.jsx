import { useState } from "react";
import {
  Sparkles, Clapperboard, Flame, ListOrdered, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import PageState from "@/components/dashboard/PageState";

const STYLES = [
  { id: "story", label: "Story" },
  { id: "meme", label: "Meme" },
  { id: "documentary", label: "Documentary" },
];

export default function CreatorStudio() {
  // ── Viral Hooks ──
  const [niche, setNiche] = useState("");
  const [count, setCount] = useState(5);
  const [blendTrends, setBlendTrends] = useState(false);
  const [hooksLoading, setHooksLoading] = useState(false);
  const [hooks, setHooks] = useState(null);
  const [hooksError, setHooksError] = useState(null);

  // ── Meme / Story Mode ──
  const [source, setSource] = useState("");
  const [style, setStyle] = useState("story");
  const [scenes, setScenes] = useState(6);
  const [storyLoading, setStoryLoading] = useState(false);
  const [storyboard, setStoryboard] = useState(null);
  const [storyError, setStoryError] = useState(null);

  const generateHooks = async () => {
    if (niche.trim().length < 2) return toast.error("Enter a niche (e.g. history facts)");
    setHooksLoading(true);
    setHooksError(null);
    setHooks(null);
    try {
      const { data } = await api.post("/creator/viral-hooks", {
        niche: niche.trim(), count, language: "hinglish", blend_trends: blendTrends,
      });
      setHooks(data.hooks || []);
    } catch (e) {
      setHooksError(e?.response?.data?.detail || "Could not generate hooks");
      toast.error("Hook generation failed");
    } finally {
      setHooksLoading(false);
    }
  };

  const generateStory = async () => {
    if (source.trim().length < 10) return toast.error("Paste at least 10 characters of source text");
    setStoryLoading(true);
    setStoryError(null);
    setStoryboard(null);
    try {
      const { data } = await api.post("/creator/meme-mode", {
        source_text: source.trim(), style, scenes, language: "hinglish",
      });
      setStoryboard(data.storyboard || []);
    } catch (e) {
      setStoryError(e?.response?.data?.detail || "Could not build storyboard");
      toast.error("Storyboard generation failed");
    } finally {
      setStoryLoading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="creator-studio-page">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2">
          <Clapperboard className="h-7 w-7 text-[var(--gs-teal)]" /> Creator Studio
        </h1>
        <p className="mt-1 text-sm text-[var(--gs-muted)]">
          The Viral Engine for YouTubers, Reel creators &amp; faceless channels — cheap, fast, Hinglish-native.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Viral Hooks */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Flame className="h-5 w-5 text-rose-500" />
            <h2 className="font-display text-xl">Viral Hook Generator</h2>
            <Badge className="bg-rose-100 text-rose-700 ml-auto">Hook</Badge>
          </div>
          <div className="space-y-3">
            <label className="text-xs font-medium">Niche / topic</label>
            <Input value={niche} onChange={(e) => setNiche(e.target.value)} placeholder="history facts, finance tips…" data-testid="hook-niche" />
            <div className="flex items-center gap-3">
              <label className="text-xs font-medium">Hooks</label>
              <Input type="number" min={1} max={10} value={count} onChange={(e) => setCount(Number(e.target.value) || 5)} className="w-20" />
              <label className="flex items-center gap-1.5 text-xs ml-auto cursor-pointer">
                <input type="checkbox" checked={blendTrends} onChange={(e) => setBlendTrends(e.target.checked)} />
                Blend live trends
              </label>
            </div>
            <Button onClick={generateHooks} disabled={hooksLoading} className="w-full bg-rose-600 hover:bg-rose-700" data-testid="hook-generate">
              {hooksLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              {hooksLoading ? "Generating…" : "Generate Hooks"}
            </Button>

            {hooksError ? (
              <PageState compact kind="error" title="Couldn't generate hooks" message={hooksError} onRetry={generateHooks} />
            ) : hooksLoading ? (
              <PageState compact kind="loading" title="Writing viral hooks…" />
            ) : hooks && hooks.length === 0 ? (
              <PageState compact kind="empty" title="No hooks yet" message="Generate hook openers for your niche." />
            ) : hooks ? (
              <ol className="space-y-2">
                {hooks.map((h, i) => (
                  <li key={i} className="flex gap-2 items-start rounded-lg border bg-[var(--gs-surface-2)] p-2 text-sm">
                    <span className="font-semibold text-rose-500">{i + 1}.</span>
                    <span>{h}</span>
                  </li>
                ))}
              </ol>
            ) : null}
          </div>
        </Card>

        {/* Meme / Story Mode */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <ListOrdered className="h-5 w-5 text-[var(--gs-teal)]" />
            <h2 className="font-display text-xl">Meme &amp; Story Mode</h2>
            <Badge className="bg-[var(--gs-teal)]/15 text-[var(--gs-teal)] ml-auto">Faceless</Badge>
          </div>
          <div className="space-y-3">
            <label className="text-xs font-medium">Source text (story, fact, post…)</label>
            <Textarea value={source} onChange={(e) => setSource(e.target.value)} rows={4}
              placeholder="Paste a Reddit story, historical fact, or long text to turn into a video storyboard…"
              data-testid="story-source" />
            <div className="flex items-center gap-3">
              <label className="text-xs font-medium">Style</label>
              <select value={style} onChange={(e) => setStyle(e.target.value)}
                className="rounded-lg border bg-white px-2 py-1 text-sm" data-testid="story-style">
                {STYLES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
              <label className="text-xs font-medium ml-auto">Scenes</label>
              <Input type="number" min={2} max={12} value={scenes} onChange={(e) => setScenes(Number(e.target.value) || 6)} className="w-20" />
            </div>
            <Button onClick={generateStory} disabled={storyLoading} className="w-full" data-testid="story-generate">
              {storyLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Clapperboard className="mr-2 h-4 w-4" />}
              {storyLoading ? "Building storyboard…" : "Build Storyboard"}
            </Button>

            {storyError ? (
              <PageState compact kind="error" title="Couldn't build storyboard" message={storyError} onRetry={generateStory} />
            ) : storyLoading ? (
              <PageState compact kind="loading" title="Composing scenes…" />
            ) : storyboard && storyboard.length === 0 ? (
              <PageState compact kind="empty" title="No scenes yet" message="Paste source text and build a storyboard." />
            ) : storyboard ? (
              <div className="space-y-2">
                {storyboard.map((s, i) => (
                  <div key={i} className="rounded-lg border p-2">
                    <div className="text-xs font-semibold text-[var(--gs-teal)]">Scene {s.scene ?? i + 1}</div>
                    <div className="text-sm">{s.visual}</div>
                    {s.caption ? <div className="text-xs text-[var(--gs-muted)] mt-0.5">“{s.caption}”</div> : null}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
