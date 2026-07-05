import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Bot, Send, RefreshCw, X, Sparkles, Zap, ChevronUp } from "lucide-react";

const SUGGESTIONS = [
  "Yesterday ki sales report do",
  "5 trending products import kar do",
  "Logo banao Diwali Sale ke liye",
  "Margin audit chalao, jo kam hai fix karo",
  "System health check",
];

export default function CopilotSidebar() {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([]);
  const endRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    api.get("/admin/copilot/history?limit=20").then(({ data }) => {
      const hist = [];
      (data.items || []).forEach((m) => {
        hist.push({ role: "user", content: m.user_msg, id: m.id + "_u" });
        const r = m.response || {};
        hist.push({ role: "assistant", kind: r.kind, content: r.text || r.summary || r.skill, skill: r.skill, result: r.result, id: m.id });
      });
      setMessages(hist);
    }).catch(() => {});
  }, [open]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (text) => {
    const content = (text ?? msg).trim();
    if (!content || busy) return;
    const userMsg = { role: "user", content, id: `u_${Date.now()}` };
    setMessages((m) => [...m, userMsg]);
    setMsg("");
    setBusy(true);
    try {
      const r = await api.post("/admin/copilot/chat", { message: content, history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })) });
      const a = r.data;
      setMessages((m) => [...m, { role: "assistant", kind: a.kind, content: a.text || a.summary || a.skill, skill: a.skill, result: a.result, id: a.id }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", kind: "error", content: e?.response?.data?.detail || "Copilot error", id: `e_${Date.now()}` }]);
    } finally { setBusy(false); }
  };

  return (
    <>
      {!open && (
        <button onClick={() => setOpen(true)} data-testid="copilot-open-button"
          className="fixed bottom-5 right-5 z-50 h-14 w-14 rounded-full grid place-items-center shadow-lg transition-transform hover:scale-105"
          style={{ background: "linear-gradient(135deg, var(--gs-teal), var(--gs-primary))", color: "#fff" }}>
          <Bot className="h-6 w-6"/>
        </button>
      )}

      {open && (
        <div className="fixed bottom-5 right-5 z-50 w-[min(420px,calc(100vw-2rem))] h-[min(640px,calc(100vh-2rem))] rounded-2xl shadow-2xl border bg-white flex flex-col overflow-hidden" style={{ borderColor: "var(--gs-border)" }} data-testid="copilot-panel">
          <header className="px-4 py-3 flex items-center gap-2 border-b" style={{ borderColor: "var(--gs-border)", background: "linear-gradient(135deg, var(--gs-teal-soft), white)" }}>
            <div className="h-8 w-8 rounded-full grid place-items-center" style={{ background: "var(--gs-teal)", color: "#fff" }}><Bot className="h-4 w-4"/></div>
            <div className="flex-1">
              <div className="font-semibold text-sm">Getszy Copilot</div>
              <div className="text-[10px] text-[var(--gs-muted)]">Hinglish AI ops assistant</div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-white/60" data-testid="copilot-close-button"><X className="h-4 w-4"/></button>
          </header>

          <div className="flex-1 overflow-y-auto p-3 space-y-3 text-sm" data-testid="copilot-messages">
            {messages.length === 0 && (
              <div className="text-center mt-6">
                <div className="h-12 w-12 rounded-full mx-auto grid place-items-center mb-2" style={{ background: "var(--gs-teal-soft)" }}><Sparkles className="h-6 w-6 text-[var(--gs-teal)]"/></div>
                <h4 className="font-display text-lg">Namaste! Main aapki kaise help karu?</h4>
                <p className="text-xs text-[var(--gs-muted)] mb-4">Try one of these:</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SUGGESTIONS.map((s, i) => (
                    <button key={i} onClick={() => send(s)} className="text-[11px] px-3 py-1.5 rounded-full border bg-white hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }} data-testid={`copilot-suggestion-${i}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 ${m.role === "user" ? "bg-[var(--gs-teal)] text-white" : m.kind === "error" ? "bg-rose-50 text-rose-900 border border-rose-200" : "bg-[var(--gs-surface-2)]"}`}>
                  {m.kind === "skill_result" && (
                    <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider mb-1 opacity-70"><Zap className="h-3 w-3"/>Ran skill: {m.skill}</div>
                  )}
                  <div className="whitespace-pre-wrap text-sm">{m.content}</div>
                  {m.kind === "skill_result" && m.result && (
                    <pre className="mt-2 text-[10px] bg-black/5 rounded p-2 max-h-40 overflow-auto">{JSON.stringify(m.result, null, 2)}</pre>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="bg-[var(--gs-surface-2)] rounded-2xl px-3 py-2 text-sm flex items-center gap-2"><RefreshCw className="h-3 w-3 animate-spin"/>Soch raha hu…</div>
              </div>
            )}
            <div ref={endRef}/>
          </div>

          <div className="p-3 border-t flex gap-2" style={{ borderColor: "var(--gs-border)" }}>
            <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Apna sawal ya command likho…" rows={2} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} className="text-sm" data-testid="copilot-input"/>
            <Button onClick={() => send()} disabled={busy || !msg.trim()} className="self-end h-9 px-3 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="copilot-send-button">
              <Send className="h-4 w-4"/>
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
