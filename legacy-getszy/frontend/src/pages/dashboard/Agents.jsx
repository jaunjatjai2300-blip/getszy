import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Send, Loader2, ArrowLeft, Plus, MessageSquare, Sparkle, Copy,
  Briefcase, PenTool, Search, BarChart3, Scale, MessageCircle, Handshake,
} from "lucide-react";
import { toast } from "sonner";
import PageState from "@/components/dashboard/PageState";
import DashboardPageFrame from "@/components/dashboard/DashboardPageFrame";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const AGENT_ICONS = {
  'business-advisor': Briefcase,
  'creative-writer': PenTool,
  'seo-consultant': Search,
  'marketing-planner': BarChart3,
  'legal-advisor': Scale,
  'customer-comms': MessageCircle,
  'sales-outreach': Handshake,
};

const AGENT_STARTERS = {
  'business-advisor': ["Help me validate this offer. Give me the target customer, problem, positioning, risks, and next 3 tests: ", "Create a practical 30-day growth plan for this business. Ask only the missing questions first: "],
  'creative-writer': ["Write three distinct landing-page headline and CTA directions for this offer. Explain the audience and promise behind each: ", "Turn this rough idea into a reel script with hook, beats, on-screen text, CTA, and platform caption: "],
  'seo-consultant': ["Build an SEO brief for this page: audience intent, primary keyword, supporting keywords, title, meta description, headings, and internal-link ideas: "],
  'marketing-planner': ["Create a focused campaign plan for this offer: objective, audience, message, channel mix, budget assumptions, metrics, and weekly actions: "],
  'legal-advisor': ["List the compliance questions and documents I should review before launching this business idea in India. Flag what needs a qualified legal professional: "],
  'customer-comms': ["Create a customer-support pack for this situation: empathetic reply, FAQ answer, escalation rule, and follow-up message: "],
  'sales-outreach': ["Create a respectful outreach sequence for this target customer. Include research angle, first message, follow-up, objection response, and opt-out-safe wording: "],
};

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [activeAgent, setActiveAgent] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setError(null);
    setLoading(true);
    try {
      const [agentsRes, sessionsRes] = await Promise.all([
        api.get("/agents"),
        api.get("/agents/sessions"),
      ]);
      setAgents(agentsRes.data.agents || []);
      setSessions(sessionsRes.data.sessions || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "We couldn't load your agents. Check your connection and try again.");
      toast.error("Failed to load agents");
    } finally {
      setLoading(false);
    }
  };

  if (activeAgent) {
    return <AgentChat agent={activeAgent} initialSessionId={activeSessionId} onBack={() => { setActiveAgent(null); setActiveSessionId(null); }} />;
  }

  return (
    <DashboardPageFrame
      eyebrow="Guidance"
      title="Your expert bench, ready when you are"
      description="Choose a specialist for business strategy, content, growth, compliance, or customer conversations. Every chat remains in your workspace history."
      icon={Sparkle}
      metrics={[{ label: "specialists", value: agents.length || 7 }, { label: "recent threads", value: sessions.length }]}
      hint="Choose the specialist closest to your current outcome, then start with a concrete business question or draft."
    >

      {error ? (
        <PageState kind="error" title="Couldn't load agents" message={error} onRetry={loadData} />
      ) : loading ? (
        <PageState kind="loading" title="Loading your agents…" />
      ) : agents.length === 0 ? (
        <PageState kind="empty" title="No agents available" message="Expert agents will appear here once they're enabled for your workspace." />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const Icon = AGENT_ICONS[agent.id] || Sparkle;
            return (
              <button
                key={agent.id}
                onClick={() => { setActiveAgent(agent); setActiveSessionId(null); }}
                className="gs-card p-5 text-left hover:bg-[var(--gs-surface-2)] transition group"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="h-12 w-12 rounded-2xl grid place-items-center text-2xl"
                    style={{ background: `${agent.color}22` }}
                  >
                    {agent.avatar}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-display text-lg">{agent.name}</div>
                    <div className="text-xs text-[var(--gs-muted)] truncate">
                      {agent.tagline}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-[var(--gs-muted)] mt-3 line-clamp-2">
                  {agent.description}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex gap-1">
                    {(agent.tools || []).slice(0, 3).map((t) => (
                      <Badge key={t} variant="outline" className="text-[9px] px-1.5 py-0">
                        {t.replace(/_/g, " ")}
                      </Badge>
                    ))}
                  </div>
                  <span
                    className="text-xs font-semibold flex items-center gap-1"
                    style={{ color: agent.color }}
                  >
                    Chat <Sparkle className="h-3 w-3" />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {sessions.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-display text-lg">Recent Sessions</h2>
          <div className="space-y-2">
            {sessions.slice(0, 10).map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  const agent = agents.find((a) => a.id === s.agent_id);
                  if (agent) { setActiveAgent(agent); setActiveSessionId(s.session_id || null); }
                }}
                className="w-full gs-card p-3 flex items-center gap-3 text-left hover:bg-[var(--gs-surface-2)]"
              >
                <span className="text-xl">{s.agent_avatar}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold">{s.agent_name}</div>
                  <div className="text-xs text-[var(--gs-muted)] truncate">
                    {s.last_message}
                  </div>
                </div>
                <Badge variant="outline" className="text-[10px] shrink-0">
                  {s.message_count} msgs
                </Badge>
              </button>
            ))}
          </div>
        </div>
      )}
    </DashboardPageFrame>
  );
}

function AgentChat({ agent, initialSessionId, onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId] = useState(() => initialSessionId || `session_${Date.now()}`);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHistory = useCallback(async () => {
    try {
      const r = await api.get(`/agents/${agent.id}/history`, {
        params: { session_id: sessionId, limit: 50 },
      });
      const history = r.data.items || [];
      const formatted = [];
      for (const h of history) {
        formatted.push({ role: "user", content: h.user_message });
        formatted.push({ role: "assistant", content: h.agent_response });
      }
      setMessages(formatted);
    } catch (e) {
      /* ignore */
    }
  }, [agent.id, sessionId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const send = async () => {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setBusy(true);

    try {
      const history = messages.slice(-8).map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const r = await api.post(`/agents/${agent.id}/chat`, {
        message: msg,
        history,
        session_id: sessionId,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: r.data.response },
      ]);
    } catch (e) {
      toast.error("Agent unavailable. Try again.");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-8rem)] h-[calc(100dvh-8rem)]">
      <div className="flex items-center gap-3 mb-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div
          className="h-10 w-10 rounded-xl grid place-items-center text-xl"
          style={{ background: `${agent.color}22` }}
        >
          {agent.avatar}
        </div>
        <div>
          <h2 className="font-display text-xl">{agent.name}</h2>
          <p className="text-xs text-[var(--gs-muted)]">{agent.tagline}</p>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pb-4">
        {messages.length === 0 && (
          <div className="mx-auto max-w-2xl py-8 text-center text-[var(--gs-muted)]">
            <div className="text-4xl mb-3">{agent.avatar}</div>
            <p className="text-sm font-medium text-[var(--gs-ink)]">Start with an outcome, not a vague question</p>
            <p className="mx-auto mt-1 max-w-lg text-xs">Include the customer, offer, goal, constraints, and any real facts you already have. Review important business, legal, financial, or customer-facing claims before acting on them.</p>
            <div className="mx-auto mt-4 grid max-w-xl gap-2 text-left">
              {(AGENT_STARTERS[agent.id] || ["Help me create a clear action plan for this goal: "]).map((starter) => (
                <button key={starter} type="button" onClick={() => setInput(starter)} className="rounded-xl border px-3 py-3 text-left text-xs hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}>
                  <span className="font-medium text-[var(--gs-ink)]">Use a structured brief</span><span className="block mt-1 line-clamp-2">{starter}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] break-words rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-[var(--gs-teal)] text-white"
                  : "bg-white border"
              }`}
            >
              {m.role === "user" ? (
                <span className="whitespace-pre-wrap">{m.content}</span>
              ) : (
                <div>
                  <div className="prose-dashboard max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(m.content)}
                    className="mt-1 inline-flex items-center gap-1 text-[11px] text-[var(--gs-muted)] hover:text-[var(--gs-teal)]"
                  >
                    <Copy className="h-3 w-3" /> Copy
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-2xl px-4 py-2.5 flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span className="text-xs text-[var(--gs-muted)]">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 pt-2 pb-[env(safe-area-inset-bottom)] border-t" style={{ borderColor: "var(--gs-border)" }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder={`Give ${agent.name} the customer, goal and context…`}
          disabled={busy}
          className="flex-1"
        />
        <Button
          onClick={send}
          disabled={busy || !input.trim()}
          size="icon"
          className="text-white shrink-0"
          style={{ background: agent.color }}
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
