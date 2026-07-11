import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { FlaskConical, Send, Trash2, Copy, Clock, Zap, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";

export default function AIPlayground() {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful AI assistant for Getszy.");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [showSettings, setShowSettings] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadModels();
    loadHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadModels = async () => {
    try {
      const r = await api.get("/admin/ai-platform/playground/models");
      setModels(r.data.models || []);
      if (r.data.models?.length > 0) setSelectedModel(r.data.models[0].id);
    } catch { toast.error("Models load nahi ho sakin"); }
  };

  const loadHistory = async () => {
    try {
      const r = await api.get("/admin/ai-platform/playground/history?limit=10");
      setHistory(r.data || []);
    } catch {}
  };

  const send = async () => {
    if (!input.trim() || !selectedModel) return;
    const userMsg = { role: "user", content: input.trim() };
    const newMsgs = [...messages, userMsg];
    setMessages(newMsgs);
    setInput("");
    setLoading(true);
    try {
      const r = await api.post("/admin/ai-platform/playground/run", {
        model: selectedModel,
        messages: newMsgs,
        temperature,
        max_tokens: maxTokens,
        system_prompt: systemPrompt,
      });
      setMessages(m => [...m, { role: "assistant", content: r.data.content }]);
      loadHistory();
    } catch (e) {
      const msg = e.response?.data?.detail || "AI error hua";
      toast.error(msg);
      setMessages(m => [...m, { role: "assistant", content: `❌ Error: ${msg}`, error: true }]);
    } finally { setLoading(false); }
  };

  const clearChat = () => { setMessages([]); };
  const copyMsg = (content) => { navigator.clipboard.writeText(content); toast.success("Copied!"); };

  const modelInfo = models.find(m => m.id === selectedModel);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <FlaskConical className="h-7 w-7 text-[var(--gs-teal)]"/>AI Playground
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Koi bhi AI model test karo — free, real responses</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={()=>setShowHistory(h=>!h)}>
            <Clock className="h-4 w-4 mr-1.5"/>History
          </Button>
          <Button variant="outline" size="sm" onClick={clearChat} disabled={messages.length===0}>
            <Trash2 className="h-4 w-4 mr-1.5"/>Clear
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-3">
          <Card className="overflow-hidden">
            <div className="bg-[var(--gs-surface-2)] px-4 py-2 flex items-center justify-between border-b" style={{borderColor:"var(--gs-border)"}}>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"/>
                <span className="text-xs font-medium">{modelInfo?.name || selectedModel || "Model select karo"}</span>
                {modelInfo && <Badge className="text-[10px] bg-[var(--gs-teal-soft)] text-[var(--gs-teal)]">{modelInfo.provider}</Badge>}
              </div>
              <span className="text-[10px] text-[var(--gs-muted)]">{messages.length} messages</span>
            </div>

            <div className="h-[420px] overflow-y-auto p-4 space-y-4 bg-white">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center text-[var(--gs-muted)]">
                  <FlaskConical className="h-12 w-12 mb-3 opacity-20"/>
                  <p className="text-sm font-medium">Model select karo aur kuch pooch lo</p>
                  <p className="text-xs mt-1 opacity-70">Free models — unlimited testing</p>
                </div>
              ) : (
                messages.map((m, i) => (
                  <div key={i} className={`flex gap-3 ${m.role==="user" ? "flex-row-reverse" : ""}`}>
                    <div className={`h-7 w-7 rounded-full grid place-items-center flex-shrink-0 text-xs font-bold ${m.role==="user" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)]"}`}>
                      {m.role==="user" ? "U" : "AI"}
                    </div>
                    <div className={`max-w-[80%] group relative ${m.role==="user" ? "items-end" : ""}`}>
                      <div className={`rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${m.role==="user" ? "bg-[var(--gs-teal)] text-white" : m.error ? "bg-rose-50 text-rose-800" : "bg-[var(--gs-surface-2)] text-[var(--gs-ink)]"}`}>
                        {m.content}
                      </div>
                      <button onClick={()=>copyMsg(m.content)} className="absolute -top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded bg-white shadow border text-[10px]">
                        <Copy className="h-3 w-3"/>
                      </button>
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex gap-3">
                  <div className="h-7 w-7 rounded-full bg-[var(--gs-surface-2)] grid place-items-center"><RefreshCw className="h-3.5 w-3.5 text-[var(--gs-teal)] animate-spin"/></div>
                  <div className="bg-[var(--gs-surface-2)] rounded-2xl px-4 py-3 text-sm text-[var(--gs-muted)]">Soch raha hoon…</div>
                </div>
              )}
              <div ref={messagesEndRef}/>
            </div>

            <div className="p-3 border-t" style={{borderColor:"var(--gs-border)"}}>
              <div className="flex gap-2">
                <Textarea
                  value={input} onChange={e=>setInput(e.target.value)}
                  onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}}}
                  placeholder="Message likho… (Enter = send, Shift+Enter = newline)"
                  rows={2} className="resize-none text-sm"/>
                <Button onClick={send} disabled={loading||!input.trim()||!selectedModel}
                  style={{background:"var(--gs-teal)"}} className="text-white self-end px-4">
                  <Send className="h-4 w-4"/>
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-3">
          <Card className="p-4 space-y-4">
            <button onClick={()=>setShowSettings(s=>!s)} className="flex items-center justify-between w-full text-sm font-semibold">
              <span className="flex items-center gap-1.5"><Zap className="h-4 w-4 text-[var(--gs-teal)]"/>Settings</span>
              {showSettings ? <ChevronDown className="h-4 w-4"/> : <ChevronRight className="h-4 w-4"/>}
            </button>
            {showSettings && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium mb-1.5 block">Model</label>
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger className="text-xs h-8"><SelectValue placeholder="Model chuno"/></SelectTrigger>
                    <SelectContent>
                      {models.map(m=>(
                        <SelectItem key={m.id} value={m.id}>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs">{m.name}</span>
                            <Badge className="text-[9px] px-1 py-0">{m.provider}</Badge>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {modelInfo && <p className="text-[10px] text-[var(--gs-muted)] mt-1">ctx: {(modelInfo.ctx/1000).toFixed(0)}k tokens</p>}
                </div>
                <div>
                  <label className="text-xs font-medium mb-1.5 block flex items-center justify-between">
                    Temperature <span className="font-mono text-[var(--gs-teal)]">{temperature}</span>
                  </label>
                  <Slider value={[temperature]} onValueChange={([v])=>setTemperature(v)} min={0} max={2} step={0.1}/>
                  <div className="flex justify-between text-[9px] text-[var(--gs-muted)] mt-0.5"><span>Precise</span><span>Creative</span></div>
                </div>
                <div>
                  <label className="text-xs font-medium mb-1.5 block flex items-center justify-between">
                    Max Tokens <span className="font-mono text-[var(--gs-teal)]">{maxTokens}</span>
                  </label>
                  <Slider value={[maxTokens]} onValueChange={([v])=>setMaxTokens(v)} min={128} max={4096} step={128}/>
                </div>
                <div>
                  <label className="text-xs font-medium mb-1.5 block">System Prompt</label>
                  <Textarea value={systemPrompt} onChange={e=>setSystemPrompt(e.target.value)} rows={4} className="text-xs resize-none"/>
                </div>
              </div>
            )}
          </Card>

          {showHistory && (
            <Card className="p-4">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5"><Clock className="h-4 w-4 text-[var(--gs-teal)]"/>Recent Runs</h3>
              {history.length === 0 ? (
                <p className="text-xs text-[var(--gs-muted)] text-center py-4">Koi history nahi</p>
              ) : (
                <div className="space-y-2">
                  {history.map((h,i) => (
                    <div key={i} className="p-2 rounded-lg bg-[var(--gs-surface-2)] text-xs">
                      <div className="font-medium truncate">{h.model}</div>
                      <div className="text-[var(--gs-muted)] mt-0.5">{h.prompt_tokens+h.completion_tokens} tokens · {new Date(h.created_at).toLocaleTimeString("en-IN")}</div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
