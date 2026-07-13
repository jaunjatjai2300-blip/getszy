import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Mic, Play, Loader2, History, ListVoice } from "lucide-react";
import { toast } from "sonner";

export default function VoiceGen() {
  const [text, setText] = useState("");
  const [voice, setVoice] = useState("en-US-AriaNeural");
  const [rate, setRate] = useState("+0%");
  const [generating, setGenerating] = useState(false);
  const [audioResult, setAudioResult] = useState(null);
  const [voices, setVoices] = useState([]);
  const [history, setHistory] = useState([]);
  const [loadingVoices, setLoadingVoices] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    loadVoices();
    loadHistory();
  }, []);

  const loadVoices = async () => {
    setLoadingVoices(true);
    try {
      const res = await api.get("/ai/voice/voices");
      setVoices(res.data.voices || []);
    } finally { setLoadingVoices(false); }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.get("/ai/voice/history?limit=20");
      setHistory(res.data.records || []);
    } finally { setLoadingHistory(false); }
  };

  const generate = async () => {
    if (!text.trim()) return toast.error("Enter text to convert");
    setGenerating(true);
    try {
      const res = await api.post("/ai/voice/tts", { text, voice, rate });
      setAudioResult(res.data);
      toast.success("Voice generated!");
      loadHistory();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Voice generation failed");
    } finally { setGenerating(false); }
  };

  const popularVoices = voices.filter(v =>
    ["en-US-AriaNeural", "en-US-GuyNeural", "en-IN-NeerjaNeural", "en-IN-PrabhatNeural",
     "hi-IN-SwaraNeural", "hi-IN-MadhurNeural"].includes(v.id)
  );

  return (
    <div className="space-y-6" data-testid="voice-gen-page">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-green-100 grid place-items-center">
          <Mic className="h-5 w-5 text-green-600" />
        </div>
        <div>
          <h1 className="text-2xl font-display">AI Voice Studio</h1>
          <p className="text-xs text-[var(--gs-muted)]">Edge-TTS — 400+ voices, 12 languages, completely free</p>
        </div>
      </div>

      <Tabs defaultValue="generate">
        <TabsList>
          <TabsTrigger value="generate"><Mic className="h-4 w-4 mr-1" /> Generate</TabsTrigger>
          <TabsTrigger value="voices"><ListVoice className="h-4 w-4 mr-1" /> Voices ({voices.length})</TabsTrigger>
          <TabsTrigger value="history" onClick={loadHistory}><History className="h-4 w-4 mr-1" /> History</TabsTrigger>
        </TabsList>

        <TabsContent value="generate" className="space-y-4">
          <Card className="p-5 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Text to speak</label>
              <Textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Welcome to Getszy — the AI Founder Operating System. Build, launch, and scale your startup with AI..."
                rows={5}
              />
              <p className="text-[11px] text-[var(--gs-muted)]">{text.length} characters</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--gs-muted)]">Voice</label>
                <select value={voice} onChange={e => setVoice(e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-[var(--gs-border)] bg-[var(--gs-surface)] text-sm">
                  {(popularVoices.length ? popularVoices : voices.slice(0, 20)).map(v => (
                    <option key={v.id} value={v.id}>{v.name || v.id} ({v.gender})</option>
                  ))}
                  {voices.length === 0 && <option>{voice}</option>}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--gs-muted)]">Speed</label>
                <select value={rate} onChange={e => setRate(e.target.value)}
                  className="w-full h-10 px-3 rounded-lg border border-[var(--gs-border)] bg-[var(--gs-surface)] text-sm">
                  <option value="-50%">Slow</option>
                  <option value="-25%">Slightly Slow</option>
                  <option value="+0%">Normal</option>
                  <option value="+25%">Slightly Fast</option>
                  <option value="+50%">Fast</option>
                </select>
              </div>
            </div>

            <Button onClick={generate} disabled={generating} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
              Generate Voice
            </Button>
          </Card>

          {audioResult && audioResult.audio && (
            <Card className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-display">Generated Audio</h3>
                <Badge variant="outline">{audioResult.voice}</Badge>
              </div>
              <audio controls src={`data:audio/mpeg;base64,${audioResult.audio}`} className="w-full" />
            </Card>
          )}
          {audioResult?.error && (
            <Card className="p-4 border-red-200 bg-red-50 text-red-600 text-sm">{audioResult.error}</Card>
          )}
        </TabsContent>

        <TabsContent value="voices">
          {loadingVoices ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {voices.map(v => (
                <Card key={v.id} className={`p-3 cursor-pointer hover:border-[var(--gs-teal)] transition-colors ${voice === v.id ? 'border-[var(--gs-teal)] ring-1 ring-[var(--gs-teal)]' : ''}`}
                  onClick={() => setVoice(v.id)}>
                  <div className="flex items-center gap-2">
                    <Mic className="h-4 w-4 text-[var(--gs-muted)]" />
                    <span className="text-sm font-medium truncate">{v.name || v.id}</span>
                  </div>
                  <div className="flex gap-2 mt-1">
                    <Badge variant="outline" className="text-[10px]">{v.locale}</Badge>
                    <Badge variant="outline" className="text-[10px]">{v.gender}</Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history">
          {loadingHistory ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : history.length === 0 ? (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No voice generations yet</Card>
          ) : (
            <div className="space-y-2">
              {history.map(r => (
                <Card key={r.id} className="p-3 flex items-center gap-3">
                  <Mic className="h-4 w-4 text-[var(--gs-teal)]" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{r.text}</p>
                    <p className="text-[10px] text-[var(--gs-muted)]">{r.voice} — {r.created_at?.slice(0, 16)}</p>
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
