import { useEffect, useState, useRef } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Sparkles, Bot, Wrench, UserPlus, Send } from "lucide-react";

const TYPE_META = {
  expert: { label: "Expert Agents", icon: Bot, color: "#0ea5e9" },
  workforce: { label: "AI Workforce", icon: Wrench, color: "#7c3aed" },
  custom: { label: "Your Custom Agents", icon: UserPlus, color: "#16a34a" },
};

function fmtResult(out) {
  if (!out) return "No output.";
  if (out.error) return "Error: " + out.error;
  if (out.parsed && typeof out.parsed === "object") {
    try { return JSON.stringify(out.parsed, null, 2); } catch { return String(out.parsed); }
  }
  if (out.raw) return out.raw;
  if (typeof out === "string") return out;
  return JSON.stringify(out, null, 2);
}

export default function AIAgents() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [thread, setThread] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    let active = true;
    api.get("/agents/all")
      .then((r) => { if (active) setData(r.data); })
      .catch(() => { if (active) setLoadError("Could not load agents. Please refresh."); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [thread]);

  async function send() {
    if (!input.trim() || sending || !selected) return;
    const text = input.trim();
    setInput("");
    setThread((t) => [...t, { role: "user", text }]);
    setSending(true);
    try {
      let out;
      if (selected.type === "expert") {
        const res = await api.post(`/agents/${selected.id}/chat`, { message: text });
        out = res.data.response || "(no response)";
      } else if (selected.type === "workforce") {
        const res = await api.post(`/workforce/${selected.id}/task`, { params: { prompt: text } });
        out = fmtResult(res.data.output || res.data);
      } else {
        const res = await api.post(`/builder/agent/${selected.id}/run`, { params: { input: text } });
        out = fmtResult(res.data.output || res.data);
      }
      setThread((t) => [...t, { role: "agent", text: out }]);
    } catch (e) {
      const detail = e?.response?.data?.detail || "Request failed. Please try again.";
      setThread((t) => [...t, { role: "agent", text: "⚠ " + detail }]);
    } finally {
      setSending(false);
    }
  }

  function openAgent(a) {
    setSelected(a);
    setThread([]);
  }

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-[var(--gs-muted)]">Loading…</div>;
  }
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center max-w-md gs-card p-8">
          <Sparkles className="h-10 w-10 mx-auto mb-3 text-[var(--gs-teal)]" />
          <h1 className="font-display text-2xl mb-2">AI Agents Hub</h1>
          <p className="text-sm text-[var(--gs-muted)] mb-4">Login to chat with your expert agents, AI workforce, and custom agents.</p>
          <a href="/login" className="inline-block px-4 py-2 rounded-lg bg-[var(--gs-teal)] text-white text-sm font-medium">Login</a>
        </div>
      </div>
    );
  }

  const sections = data ? ["expert", "workforce", "custom"].filter((k) => (data[k] || []).length) : [];

  return (
    <div className="min-h-screen" style={{ background: "var(--gs-bg, #f8fafc)" }}>
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="flex items-center gap-3 mb-1">
          <Sparkles className="h-7 w-7 text-[var(--gs-teal)]" />
          <h1 className="font-display text-3xl">AI Agents Hub</h1>
        </div>
        <p className="text-sm text-[var(--gs-muted)] mb-6">
          {data
            ? `${data.total} agents ready — expert strategists, an AI workforce, and your own custom agents. Pick one and start.`
            : "Loading your agents…"}
        </p>

        {loadError && <div className="gs-card p-4 text-rose-600 text-sm mb-4">{loadError}</div>}

        <div className="grid md:grid-cols-[1fr_1.1fr] gap-6">
          <div className="space-y-6">
            {sections.map((k) => {
              const meta = TYPE_META[k];
              const Icon = meta.icon;
              return (
                <div key={k}>
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className="h-4 w-4" style={{ color: meta.color }} />
                    <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--gs-muted)]">{meta.label}</h2>
                    <span className="text-xs text-[var(--gs-muted)]">({data[k].length})</span>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {data[k].map((a) => (
                      <button
                        key={a.id}
                        onClick={() => openAgent({ ...a, type: k })}
                        className={`text-left gs-card gs-card-hover p-4 flex items-start gap-3 ${selected?.id === a.id ? "ring-2 ring-[var(--gs-teal)]" : ""}`}
                        data-testid={`agent-card-${a.id}`}
                      >
                        <span className="h-9 w-9 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0" style={{ background: a.color || meta.color }}>
                          {(a.name || a.id).slice(0, 1).toUpperCase()}
                        </span>
                        <span className="min-w-0">
                          <span className="block font-medium text-sm truncate">{a.name}</span>
                          <span className="block text-xs text-[var(--gs-muted)]">{a.role || a.tagline || "Custom agent"}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
            {!data && !loadError && <div className="gs-card p-8 text-center text-[var(--gs-muted)]">Loading agents…</div>}
          </div>

          <div className="gs-card flex flex-col h-[70vh] md:sticky md:top-24">
            {!selected ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-[var(--gs-muted)]">
                <Bot className="h-10 w-10 mb-3 opacity-40" />
                <p className="text-sm">Select an agent on the left to start a conversation.</p>
              </div>
            ) : (
              <>
                <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: "var(--gs-border)" }}>
                  <span className="h-8 w-8 rounded-lg flex items-center justify-center text-white text-xs font-bold" style={{ background: selected.color || "var(--gs-teal)" }}>
                    {(selected.name || selected.id).slice(0, 1).toUpperCase()}
                  </span>
                  <div>
                    <div className="text-sm font-semibold">{selected.name}</div>
                    <div className="text-xs text-[var(--gs-muted)]">{TYPE_META[selected.type].label}</div>
                  </div>
                </div>
                <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                  {thread.length === 0 && (
                    <p className="text-xs text-[var(--gs-muted)]">
                      Say hi to {selected.name}. Try: “Write a Hinglish Instagram caption for a festive saree drop.”
                    </p>
                  )}
                  {thread.map((m, i) => (
                    <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[85%] whitespace-pre-wrap text-sm rounded-2xl px-3 py-2 ${m.role === "user" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface)] text-[var(--gs-ink)]"}`}>
                        {m.text}
                      </div>
                    </div>
                  ))}
                  {sending && <div className="text-xs text-[var(--gs-muted)]">Agent is typing…</div>}
                </div>
                <div className="p-3 border-t flex gap-2" style={{ borderColor: "var(--gs-border)" }}>
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") send(); }}
                    placeholder={`Message ${selected.name}…`}
                    className="flex-1 px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2 focus:ring-[var(--gs-teal)]"
                    style={{ borderColor: "var(--gs-border)" }}
                  />
                  <button onClick={send} disabled={sending || !input.trim()} className="px-3 py-2 rounded-lg bg-[var(--gs-teal)] text-white disabled:opacity-40" data-testid="ai-send-button">
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
