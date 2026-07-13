import { useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ImageIcon, Loader2, Download, History, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function ImageGen() {
  const [prompt, setPrompt] = useState("");
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [style, setStyle] = useState("photorealistic");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const generate = async () => {
    if (!prompt.trim()) return toast.error("Enter a prompt");
    setGenerating(true);
    try {
      const res = await api.post("/ai/images/generate", { prompt, width, height, style });
      setResult(res.data);
      toast.success("Image generated!");
      loadHistory();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Generation failed");
    } finally { setGenerating(false); }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.get("/ai/images/history?limit=20");
      setHistory(res.data.images || []);
    } finally { setLoadingHistory(false); }
  };

  return (
    <div className="space-y-6" data-testid="image-gen-page">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-purple-100 grid place-items-center">
          <ImageIcon className="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <h1 className="text-2xl font-display">AI Image Generator</h1>
          <p className="text-xs text-[var(--gs-muted)]">FLUX via HuggingFace + Pollinations fallback</p>
        </div>
      </div>

      <Tabs defaultValue="generate">
        <TabsList>
          <TabsTrigger value="generate"><Sparkles className="h-4 w-4 mr-1" /> Generate</TabsTrigger>
          <TabsTrigger value="history" onClick={loadHistory}><History className="h-4 w-4 mr-1" /> History</TabsTrigger>
        </TabsList>

        <TabsContent value="generate" className="space-y-4">
          <Card className="p-5 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Prompt</label>
              <Textarea
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                placeholder="A futuristic AI dashboard with holographic charts, cyberpunk style..."
                rows={4}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--gs-muted)]">Width</label>
                <Input type="number" value={width} onChange={e => setWidth(+e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--gs-muted)]">Height</label>
                <Input type="number" value={height} onChange={e => setHeight(+e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--gs-muted)]">Style</label>
                <select value={style} onChange={e => setStyle(e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-[var(--gs-border)] bg-[var(--gs-surface)] text-sm">
                  <option value="photorealistic">Photorealistic</option>
                  <option value="illustration">Illustration</option>
                  <option value="digital-art">Digital Art</option>
                  <option value="anime">Anime</option>
                  <option value="oil-painting">Oil Painting</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={generate} disabled={generating} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
                {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Generate Image
              </Button>
            </div>
          </Card>

          {result && (
            <Card className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-display">Generated Image</h3>
                <Badge variant="outline">{result.provider}</Badge>
              </div>
              {result.image && (
                <img src={`data:image/png;base64,${result.image}`} alt="Generated" className="w-full rounded-xl" />
              )}
              {result.error && <p className="text-red-500 text-sm">{result.error}</p>}
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history">
          {loadingHistory ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : history.length === 0 ? (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No images generated yet</Card>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {history.map(img => (
                <Card key={img.id} className="overflow-hidden">
                  <div className="aspect-square bg-[var(--gs-surface-2)] grid place-items-center">
                    <ImageIcon className="h-8 w-8 text-[var(--gs-muted)]" />
                  </div>
                  <div className="p-2">
                    <p className="text-xs truncate">{img.prompt}</p>
                    <p className="text-[10px] text-[var(--gs-muted)]">{img.created_at?.slice(0, 10)}</p>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
