import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Sparkles, Send, Plus, MessageSquare, Loader2, Trash2, Film, PenTool, TrendingUp, Zap, Flame, Globe, Youtube, Bot, Briefcase, Smartphone, Layers, BookOpen, Package, ArrowUp, RefreshCw, ExternalLink, Download, Rocket } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { undoableDelete, errorWithRetry } from "@/lib/ux";
import { ListSkeleton, EmptyState } from "@/components/ux/Skeletons";
import WorkspaceTabs from "@/components/workspace/WorkspaceTabs";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const KIND_ICONS = {
  script: PenTool, hook_score: Zap, viral_score: Flame, trends: TrendingUp,
  competitor_gap: TrendingUp, video_job: Film, channel_plan: Youtube,
  webapp: Globe, starter_mobileapp: Smartphone, starter_fullstack: Layers,
  starter_blog: BookOpen, workforce_run: Briefcase, sourcing_scan: Package,
  error: Zap,
};

const SUGGESTIONS = [
  { icon: PenTool,   text: "Write a Hinglish reel script: 5 AI tools for Indian students" },
  { icon: Film,      text: "Faceless video banao: how to save your first 10 lakhs (hinglish, 30 sec)" },
  { icon: Youtube,   text: "Plan a 30-day faceless channel about personal finance for Gen Z Indians" },
  { icon: Globe,     text: "Build a landing page for a Kathak academy in Jaipur" },
  { icon: TrendingUp,text: "Predict trending content topics for Indian food creators" },
  { icon: Briefcase, text: "Ask designer agent to create 3 thumbnail concepts for stock market video" },
];

// ============================================================
// Root
// ============================================================
export default function ChatHome() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const location = typeof window !== "undefined" ? window.location.pathname : "/admin";
  // Route base: use /dashboard/chat for customers, /labs/chat for labs, else /admin/chat
  const base = location.startsWith("/dashboard") ? "/dashboard/chat"
             : location.startsWith("/labs") ? "/labs/chat"
             : "/admin/chat";
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(sessionId || null);

  const loadSessions = useCallback(async () => {
    try { const r = await api.get("/chat/sessions?limit=50"); setSessions(r.data.items || []); } catch (e) {}
  }, []);
  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { setActiveId(sessionId || null); }, [sessionId]);

  const startNew = async (firstMessage = null) => {
    try {
      const r = await api.post("/chat/session", firstMessage ? { first_message: firstMessage } : {});
      await loadSessions();
      navigate(`${base}/${r.data.id}`);
    } catch (e) { toast.error("Could not start session"); }
  };
  const del = async (id) => {
    const original = sessions;
    undoableDelete({
      itemLabel: "chat",
      onOptimisticRemove: () => setSessions(cur => cur.filter(x => x.id !== id)),
      onCommit: async () => {
        await api.delete(`/chat/session/${id}`);
        if (activeId === id) navigate(base);
        await loadSessions();
      },
      onRestore: () => setSessions(original),
    });
  };

  return (
    <div className="grid grid-cols-12 gap-4 h-[calc(100vh-88px)]" data-testid="admin-chat-home">
      {/* Sessions sidebar */}
      <div className="col-span-12 md:col-span-3 lg:col-span-2">
        <Card className="p-3 h-full flex flex-col">
          <Button className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" onClick={() => startNew()} data-testid="new-chat-btn">
            <Plus className="h-4 w-4 mr-2"/>New chat
          </Button>
          <div className="mt-3 text-[10px] uppercase text-[var(--gs-muted)] tracking-wider px-1">Recent</div>
          <div className="mt-2 flex-1 overflow-y-auto space-y-1 pr-1" data-testid="sessions-list">
            {sessions.length === 0 && <div className="text-[11px] text-[var(--gs-muted)] p-2">No chats yet.</div>}
            {sessions.map((s) => (
              <div key={s.id} className={`group flex items-center gap-1 px-2 py-2 rounded-lg cursor-pointer text-xs ${activeId === s.id ? "bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`} onClick={() => navigate(`${base}/${s.id}`)} data-testid={`session-${s.id}`}>
                <MessageSquare className="h-3.5 w-3.5 shrink-0"/>
                <span className="flex-1 truncate">{s.title || "Untitled"}</span>
                <button onClick={(e) => { e.stopPropagation(); del(s.id); }} className="opacity-0 group-hover:opacity-100 text-rose-500" title="Delete"><Trash2 className="h-3 w-3"/></button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Main workspace */}
      <div className="col-span-12 md:col-span-9 lg:col-span-10">
        {activeId ? (
          <ChatWorkspace key={activeId} sessionId={activeId} onProjectUpdate={loadSessions}/>
        ) : (
          <WelcomeScreen onStart={startNew}/>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Welcome screen (no active session)
// ============================================================
function WelcomeScreen({ onStart }) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async (text) => {
    const t = (text ?? input).trim();
    if (t.length < 3) return;
    setBusy(true);
    try { await onStart(t); } finally { setBusy(false); }
  };
  return (
    <Card className="h-full p-8 flex flex-col items-center justify-center text-center" data-testid="chat-welcome">
      <div className="h-16 w-16 rounded-3xl grid place-items-center bg-[var(--gs-teal)]/15 mb-4">
        <Sparkles className="h-8 w-8 text-[var(--gs-teal)]"/>
      </div>
      <h1 className="font-display text-4xl">Neo — Getszy's AI Builder</h1>
      <p className="text-sm text-[var(--gs-muted)] mt-2 max-w-xl">Ek chat, ek dashboard, sab kuch. Videos · Scripts · Web apps · Channels · Agents · Trends — bas bata kya banana hai.</p>

      <div className="max-w-2xl w-full mt-8">
        <div className="relative">
          <Textarea rows={3} value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) go(); }}
            placeholder="Bhai, kya banana hai? e.g. 'Ek reel script likho AI tools ke topic pe'" className="pr-14"
            data-testid="welcome-input"/>
          <button onClick={() => go()} disabled={busy || input.trim().length < 3}
            className="absolute right-3 bottom-3 h-9 w-9 rounded-xl bg-[var(--gs-teal)] text-white grid place-items-center disabled:opacity-40" data-testid="welcome-send">
            {busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <ArrowUp className="h-4 w-4"/>}
          </button>
        </div>
        <div className="text-[10px] text-[var(--gs-muted)] mt-2">Cmd/Ctrl + Enter to send</div>
      </div>

      <div className="grid sm:grid-cols-2 gap-2 mt-8 max-w-2xl w-full" data-testid="welcome-suggestions">
        {SUGGESTIONS.map((s, i) => {
          const Icon = s.icon;
          return (
            <button key={i} onClick={() => go(s.text)} className="text-left gs-card p-3 hover:bg-[var(--gs-surface-2)] transition flex items-start gap-2" data-testid={`suggestion-${i}`}>
              <Icon className="h-4 w-4 text-[var(--gs-teal)] mt-0.5 shrink-0"/>
              <span className="text-xs">{s.text}</span>
            </button>
          );
        })}
      </div>
    </Card>
  );
}

// ============================================================
// Chat workspace (active session)
// ============================================================
function ChatWorkspace({ sessionId, onProjectUpdate }) {
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [assets, setAssets] = useState([]);
  const [events, setEvents] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [activeAsset, setActiveAsset] = useState(null);
  const sinceRef = useRef("");
  const bottomRef = useRef(null);
  const pollRef = useRef(null);

  const loadFull = useCallback(async () => {
    try {
      const r = await api.get(`/chat/session/${sessionId}`);
      setProject(r.data.project);
      setMessages(r.data.messages || []);
      setAssets(r.data.assets || []);
      sinceRef.current = r.data.project?.updated_at || "";
      if (r.data.assets?.length) setActiveAsset(a => a || r.data.assets[r.data.assets.length - 1]);
    } catch (e) {}
  }, [sessionId]);

  useEffect(() => { loadFull(); return () => { if (pollRef.current) clearTimeout(pollRef.current); }; }, [loadFull]);

  const poll = useCallback(async () => {
    try {
      const r = await api.get(`/chat/session/${sessionId}/events?since=${encodeURIComponent(sinceRef.current)}`);
      if (r.data.messages?.length) {
        setMessages(cur => {
          const seen = new Set(cur.map(x => x.id));
          const merged = [...cur];
          r.data.messages.forEach(m => { if (!seen.has(m.id)) merged.push(m); });
          return merged;
        });
      }
      if (r.data.assets?.length) {
        setAssets(cur => {
          const seen = new Set(cur.map(x => x.id));
          const merged = [...cur];
          r.data.assets.forEach(a => { if (!seen.has(a.id)) { merged.push(a); setActiveAsset(a); } });
          return merged;
        });
      }
      if (r.data.events?.length) {
        setEvents(cur => [...cur, ...r.data.events].slice(-40));
      }
      if (r.data.server_time) sinceRef.current = r.data.server_time;
      // If a "done" event arrived, stop polling until next send
      const done = r.data.events?.some(e => e.kind === "done" || e.kind === "error");
      if (done) {
        setSending(false);
        onProjectUpdate?.();
      }
    } catch (e) {}
    // If still sending, schedule next poll
    if (sending) pollRef.current = setTimeout(poll, 1200);
  }, [sessionId, sending, onProjectUpdate]);

  useEffect(() => {
    if (sending) {
      pollRef.current = setTimeout(poll, 500);
    }
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [sending, poll]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length, events.length]);

  const send = async () => {
    const t = input.trim();
    if (t.length < 1) return;
    setInput("");
    setSending(true);
    // Optimistic: show a temp user message
    setMessages(cur => [...cur, { id: `temp-${Date.now()}`, role: "user", content: t, temp: true, created_at: new Date().toISOString() }]);
    try {
      await api.post(`/chat/session/${sessionId}/message`, { content: t });
      // On next poll we'll get the real user message + assistant reply
    } catch (e) {
      toast.error("Send failed");
      setSending(false);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-3 h-full">
      {/* Conversation column */}
      <Card className="col-span-12 lg:col-span-7 flex flex-col overflow-hidden">
        <div className="p-3 border-b flex items-center gap-2" style={{ borderColor: "var(--gs-border)" }}>
          <Sparkles className="h-4 w-4 text-[var(--gs-teal)]"/>
          <div className="font-display text-sm truncate flex-1">{project?.title || "New chat"}</div>
          {(project?.capabilities_used || []).slice(0, 3).map(c => <Badge key={c} variant="outline" className="text-[9px]">{c}</Badge>)}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="chat-messages">
          {messages.length === 0 && !sending && (
            <div className="text-center text-xs text-[var(--gs-muted)] py-8">Type kuch bhi neeche \u2014 script/video/webapp/channel/agent \u2014 Neo handle karega.</div>
          )}
          {messages.map((m) => <Bubble key={m.id} m={m} onOpenAsset={(id) => {
            const a = assets.find(x => x.id === id); if (a) setActiveAsset(a);
          }}/>)}
          {sending && <ThinkingBubble events={events.slice(-6)}/>}
          <div ref={bottomRef}/>
        </div>

        <div className="p-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
          <div className="relative">
            <Textarea rows={2} value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send(); }}
              placeholder="Type your request \u2014 script, video, webapp, channel, agent\u2026"
              className="pr-14" disabled={sending} data-testid="chat-input"/>
            <button onClick={send} disabled={sending || input.trim().length < 1}
              className="absolute right-3 bottom-3 h-9 w-9 rounded-xl bg-[var(--gs-teal)] text-white grid place-items-center disabled:opacity-40" data-testid="chat-send">
              {sending ? <Loader2 className="h-4 w-4 animate-spin"/> : <ArrowUp className="h-4 w-4"/>}
            </button>
          </div>
          <div className="text-[10px] text-[var(--gs-muted)] mt-1">Cmd/Ctrl + Enter to send</div>
        </div>
      </Card>

      {/* Workspace / asset preview column — now tabbed */}
      <WorkspaceTabs
        projectId={project?.id}
        assets={assets}
        activeAsset={activeAsset}
        setActiveAsset={setActiveAsset}
        renderAssetPreview={(a) => <AssetPreview asset={a}/>}
      />
    </div>
  );
}

// ============================================================
// Message bubble
// ============================================================
function Bubble({ m, onOpenAsset }) {
  const isUser = m.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`} data-testid={`msg-${m.id}`}>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${isUser ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)]"}`}>
        <div className="whitespace-pre-wrap break-words">{m.content}</div>
        {m.asset_id && !isUser && (
          <button onClick={() => onOpenAsset(m.asset_id)} className="mt-2 text-[10px] underline opacity-80" data-testid={`open-asset-${m.asset_id}`}>
            View asset \u2192
          </button>
        )}
      </div>
    </motion.div>
  );
}

function ThinkingBubble({ events }) {
  const lastMsg = [...events].reverse().find(e => e.payload?.msg)?.payload?.msg || "Neo is thinking…";
  return (
    <div className="flex justify-start" data-testid="thinking-bubble">
      <div className="max-w-[85%] rounded-2xl px-3 py-2 text-sm bg-[var(--gs-surface-2)] flex items-center gap-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--gs-teal)]"/>
        <span className="text-[var(--gs-muted)]">{lastMsg}</span>
      </div>
    </div>
  );
}

// ============================================================
// Asset preview dispatcher
// ============================================================
function AssetPreview({ asset }) {
  const d = asset.data || {};
  const kind = asset.kind;
  if (kind === "webapp") return <WebappPreview asset={asset}/>;
  if (kind === "video_job") return <VideoPreview asset={asset}/>;
  if (kind === "channel_plan") return <ChannelPreview asset={asset}/>;
  if (kind === "script") return <ScriptPreview asset={asset}/>;
  if (kind === "trends") return <TrendsPreview asset={asset}/>;
  if (kind === "hook_score" || kind === "viral_score") return <ScorePreview asset={asset}/>;
  if (kind?.startsWith("starter_")) return <StarterPreview asset={asset}/>;
  if (kind === "workforce_run") return <WorkforcePreview asset={asset}/>;
  if (kind === "sourcing_scan") return <SourcingPreview asset={asset}/>;
  if (kind === "competitor_gap") return <GapsPreview asset={asset}/>;
  if (kind === "error") return <ErrorPreview asset={asset}/>;
  return <JsonPreview data={d}/>;
}

function AssetHeader({ asset, right }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Badge variant="outline" className="text-[10px]">{asset.kind}</Badge>
      <div className="font-semibold text-sm truncate flex-1">{asset.title}</div>
      {right}
    </div>
  );
}

function WebappPreview({ asset }) {
  const d = asset.data || {};
  return (
    <div>
      <AssetHeader asset={asset} right={
        <a href={`${BACKEND_URL}${d.preview_url}`} target="_blank" rel="noreferrer" className="text-xs flex items-center gap-1 text-[var(--gs-teal)]" data-testid="asset-open-tab"><ExternalLink className="h-3 w-3"/>Open</a>
      }/>
      <iframe src={`${BACKEND_URL}${d.preview_url}`} className="w-full h-[520px] rounded-xl border bg-white" title={asset.title} data-testid="asset-webapp-iframe"/>
      <div className="text-[10px] text-[var(--gs-muted)] mt-2">{Math.round((d.size_bytes || 0) / 1024)} KB · single-file HTML</div>
    </div>
  );
}

function VideoPreview({ asset }) {
  const d = asset.data || {};
  const [job, setJob] = useState(null);
  const [poll, setPoll] = useState(0);
  useEffect(() => {
    let t;
    const tick = async () => {
      try {
        const r = await api.get(d.status_endpoint);
        setJob(r.data);
        if (r.data.status !== "done" && r.data.status !== "failed") t = setTimeout(tick, 5000);
      } catch (e) {}
    };
    tick();
    return () => t && clearTimeout(t);
  }, [d.status_endpoint, poll]);
  return (
    <div>
      <AssetHeader asset={asset} right={
        <button onClick={() => setPoll(p => p + 1)} className="text-xs text-[var(--gs-muted)]" data-testid="asset-video-refresh"><RefreshCw className="h-3 w-3"/></button>
      }/>
      {job?.status !== "done" && (
        <>
          <div className="text-xs text-[var(--gs-muted)] mb-2">{job?.status || "queued"} · {job?.percent || 0}%</div>
          <div className="h-2 rounded-full bg-[var(--gs-surface-2)] overflow-hidden">
            <div className="h-full bg-[var(--gs-teal)] transition-all" style={{ width: `${job?.percent || 5}%` }}/>
          </div>
        </>
      )}
      {job?.status === "done" && job?.video_url && (
        <>
          <video src={`${BACKEND_URL}${job.video_url}`} controls className="w-full mt-2 rounded-xl bg-black" data-testid="asset-video-player"/>
          <div className="flex gap-3 mt-2 text-xs">
            <a href={`${BACKEND_URL}${job.video_url}`} download className="flex items-center gap-1"><Download className="h-3 w-3"/>MP4</a>
            {job.srt_url && <a href={`${BACKEND_URL}${job.srt_url}`} download className="flex items-center gap-1"><Download className="h-3 w-3"/>SRT</a>}
          </div>
        </>
      )}
      {job?.status === "failed" && <div className="text-xs text-rose-600 mt-2">{job.error}</div>}
    </div>
  );
}

function ChannelPreview({ asset }) {
  const d = asset.data || {}; const plan = d.plan || {};
  return (
    <div>
      <AssetHeader asset={asset}/>
      <p className="text-xs text-[var(--gs-muted)] mb-2">{plan.channel_bio}</p>
      <div className="flex flex-wrap gap-1 mb-3">{(plan.pillars || []).map((p, i) => <Badge key={i} variant="secondary" className="text-[10px]">{p.theme || p}</Badge>)}</div>
      <div className="space-y-1 max-h-[440px] overflow-y-auto">
        {(plan.videos || []).map((v, i) => (
          <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
            <Badge variant="outline" className="text-[9px]">Day {v.day}</Badge>
            <span className="flex-1 truncate">{v.topic}</span>
            <Badge variant="secondary" className="text-[9px]">{v.format || "reel"}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScriptPreview({ asset }) {
  const d = asset.data || {};
  return (
    <div>
      <AssetHeader asset={asset}/>
      {d.hook && <div className="p-3 bg-[var(--gs-surface-2)] rounded-xl mb-3"><div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Hook</div><div className="text-sm">{d.hook}</div></div>}
      {d.body && <div className="text-xs whitespace-pre-wrap p-3 bg-[var(--gs-surface-2)] rounded-xl mb-3">{d.body}</div>}
      {d.cta && <div className="p-3 bg-[var(--gs-teal)]/10 rounded-xl mb-3"><div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">CTA</div><div className="text-sm">{d.cta}</div></div>}
      {d.hashtags && (
        <div className="flex flex-wrap gap-1">{(d.hashtags || []).map((h, i) => <Badge key={i} variant="outline" className="text-[9px]">{h}</Badge>)}</div>
      )}
      <details className="mt-3"><summary className="text-[10px] text-[var(--gs-muted)] cursor-pointer">Show raw JSON</summary><JsonPreview data={d}/></details>
    </div>
  );
}

function TrendsPreview({ asset }) {
  const preds = asset.data?.predictions || [];
  return (
    <div>
      <AssetHeader asset={asset}/>
      <div className="space-y-2">
        {preds.map((p, i) => (
          <div key={i} className="p-3 bg-[var(--gs-surface-2)] rounded-xl">
            <div className="flex items-center gap-2">
              <div className="font-semibold text-sm flex-1">{p.topic}</div>
              <Badge variant="outline">{p.trend_score || "?"}/100</Badge>
            </div>
            <div className="text-[11px] text-[var(--gs-muted)] mt-1">{p.why}</div>
            {p.hook_idea && <div className="text-[11px] mt-1 italic">"{p.hook_idea}"</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScorePreview({ asset }) {
  const d = asset.data || {};
  const score = d.score ?? d.viral_score;
  return (
    <div>
      <AssetHeader asset={asset}/>
      <div className="flex items-center gap-4 mb-3">
        <div className="h-20 w-20 rounded-full grid place-items-center bg-[var(--gs-teal)]/10 text-[var(--gs-teal)] font-display text-4xl">{score}</div>
        <div className="text-xs text-[var(--gs-muted)] flex-1">{d.rationale || d.recommendation}</div>
      </div>
      {d.suggested_rewrite && <div className="p-3 bg-[var(--gs-surface-2)] rounded-xl text-sm"><div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Suggested rewrite</div>{d.suggested_rewrite}</div>}
      {(d.drivers || []).length > 0 && (<div className="mt-3"><div className="text-[10px] uppercase text-[var(--gs-muted)] mb-1">Drivers</div><div className="flex flex-wrap gap-1">{d.drivers.map((x, i) => <Badge key={i} variant="secondary" className="text-[10px]">{x}</Badge>)}</div></div>)}
      {(d.risks || []).length > 0 && (<div className="mt-3"><div className="text-[10px] uppercase text-rose-600 mb-1">Risks</div><div className="flex flex-wrap gap-1">{d.risks.map((x, i) => <Badge key={i} className="text-[10px] bg-rose-100 text-rose-800">{x}</Badge>)}</div></div>)}
    </div>
  );
}

function StarterPreview({ asset }) {
  const d = asset.data || {};
  return (
    <div>
      <AssetHeader asset={asset}/>
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-xl grid place-items-center bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]"><Download className="h-6 w-6"/></div>
          <div className="flex-1">
            <div className="font-semibold text-sm">{asset.title}</div>
            <div className="text-[10px] text-[var(--gs-muted)]">{Math.round((d.size_bytes || 0) / 1024)} KB</div>
          </div>
          <a href={`${BACKEND_URL}${d.download_url}`} download className="text-xs bg-[var(--gs-teal)] text-white px-3 py-1.5 rounded-lg" data-testid="starter-download">Download</a>
        </div>
      </Card>
    </div>
  );
}

function WorkforcePreview({ asset }) {
  return (
    <div>
      <AssetHeader asset={asset}/>
      <JsonPreview data={asset.data?.parsed || asset.data}/>
    </div>
  );
}

function SourcingPreview({ asset }) {
  const items = asset.data?.items || [];
  return (
    <div>
      <AssetHeader asset={asset}/>
      <div className="space-y-2">
        {items.slice(0, 20).map((it, i) => (
          <div key={i} className="text-xs p-2 bg-[var(--gs-surface-2)] rounded-lg">
            <div className="font-semibold truncate">{it.title || it.name}</div>
            {it.price && <Badge variant="outline" className="text-[9px]">₹{it.price}</Badge>}
          </div>
        ))}
      </div>
    </div>
  );
}

function GapsPreview({ asset }) {
  const gaps = asset.data?.gaps || [];
  return (
    <div>
      <AssetHeader asset={asset}/>
      <div className="space-y-2">
        {gaps.map((g, i) => (
          <div key={i} className="p-3 bg-[var(--gs-surface-2)] rounded-xl">
            <div className="font-semibold text-sm">{g.topic}</div>
            <div className="text-[11px] text-[var(--gs-muted)] mt-1">{g.why_underserved}</div>
            {g.angle && <div className="text-[11px] italic mt-1">Angle: {g.angle}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorPreview({ asset }) {
  return (
    <div>
      <AssetHeader asset={asset}/>
      <div className="p-3 bg-rose-50 text-rose-800 rounded-xl text-xs">{asset.data?.error || "Something failed."}</div>
    </div>
  );
}

function JsonPreview({ data }) {
  return <pre className="text-[11px] bg-[var(--gs-surface-2)] p-3 rounded-xl max-h-96 overflow-auto">{JSON.stringify(data, null, 2)}</pre>;
}
