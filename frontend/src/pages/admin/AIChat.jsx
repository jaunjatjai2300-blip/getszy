import { useEffect, useRef, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Send, Loader2, CheckCircle2, AlertCircle, Plus, History, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const SUGGESTIONS = [
  "Add product Rose Gold Hoops 899 in jewellery, supplier Meesho, cost 320",
  "Show today's orders",
  "Update order ORD1001 to shipped with tracking AWB123456",
  "Show low stock products",
  "Show this month's revenue stats",
  "Add supplier Surat Textiles, contact +91-9876543210",
  "List beauty category products",
  "Update Rose Gold Hoops price to 999",
];

function ResultCard({ result }) {
  if (!result) return null;
  if (!result.ok) return (
    <div className="mt-2 p-3 rounded-xl border bg-rose-50 border-rose-200 text-sm flex items-start gap-2"><AlertCircle className="h-4 w-4 text-rose-600 mt-0.5"/><span>{result.error}</span></div>
  );
  const t = result.type;
  const d = result.data;
  if (t === "product") return (
    <div className="mt-2 gs-card p-3 flex items-center gap-3" data-testid="ai-result-product">
      <img src={(d.images || [])[0]} alt="" className="h-14 w-14 rounded-lg object-cover" style={{ background: "var(--gs-surface-2)" }}/>
      <div className="flex-1"><div className="font-semibold text-sm">{d.name}</div><div className="text-xs text-[var(--gs-muted)]">{fmtINR(d.price)} · Stock: {d.stock} · {d.category}</div></div>
      <CheckCircle2 className="h-5 w-5 text-emerald-500"/>
    </div>
  );
  if (t === "product_list") return (
    <div className="mt-2 gs-card p-3" data-testid="ai-result-product-list"><div className="text-xs text-[var(--gs-muted)] mb-2">{result.count} products</div><div className="space-y-1.5 max-h-60 overflow-auto">{d.map((p) => (<div key={p.id} className="flex items-center gap-2 text-sm"><img src={(p.images||[])[0]} alt="" className="h-8 w-8 rounded object-cover"/><span className="flex-1 truncate">{p.name}</span><span className="font-semibold">{fmtINR(p.price)}</span><span className="text-xs text-[var(--gs-muted)] w-12 text-right">Stk {p.stock}</span></div>))}</div></div>
  );
  if (t === "order_list") return (
    <div className="mt-2 gs-card p-3" data-testid="ai-result-order-list"><div className="text-xs text-[var(--gs-muted)] mb-2">{result.count} orders</div><div className="space-y-1.5">{d.map((o) => (<div key={o.id} className="flex items-center gap-2 text-sm"><span className="font-mono">{o.order_number}</span><span className="flex-1 truncate">{o.customer_name}</span><Badge variant="outline" className="capitalize">{o.status}</Badge><span className="font-semibold">{fmtINR(o.total)}</span></div>))}</div></div>
  );
  if (t === "order") return (
    <div className="mt-2 gs-card p-3 text-sm" data-testid="ai-result-order"><div className="font-semibold">{d.order_number}</div><div className="text-xs text-[var(--gs-muted)]">Status: <span className="capitalize">{d.status}</span>{d.tracking_number && <> · Tracking: <span className="font-mono">{d.tracking_number}</span></>}</div></div>
  );
  if (t === "stats") return (
    <div className="mt-2 grid grid-cols-2 gap-2" data-testid="ai-result-stats">
      <div className="gs-card p-3"><div className="text-xs text-[var(--gs-muted)]">Revenue</div><div className="font-display text-xl">{fmtINR(d.revenue)}</div></div>
      <div className="gs-card p-3"><div className="text-xs text-[var(--gs-muted)]">Orders</div><div className="font-display text-xl">{d.orders_count}</div></div>
      <div className="gs-card p-3"><div className="text-xs text-[var(--gs-muted)]">Profit</div><div className="font-display text-xl text-[var(--gs-teal)]">{fmtINR(d.profit)}</div></div>
      <div className="gs-card p-3"><div className="text-xs text-[var(--gs-muted)]">Low stock</div><div className="font-display text-xl">{d.low_stock_count}</div></div>
    </div>
  );
  if (t === "supplier") return (<div className="mt-2 gs-card p-3 text-sm" data-testid="ai-result-supplier"><div className="font-semibold">{d.name}</div><div className="text-xs text-[var(--gs-muted)]">{d.contact}</div></div>);
  if (t === "supplier_list") return (<div className="mt-2 gs-card p-3 text-sm"><div className="text-xs text-[var(--gs-muted)] mb-2">{d.length} suppliers</div>{d.map((s) => (<div key={s.id} className="flex justify-between py-1"><span>{s.name}</span><span className="text-xs text-[var(--gs-muted)]">{s.contact}</span></div>))}</div>);
  if (t === "category_list") return (<div className="mt-2 gs-card p-3 text-sm flex flex-wrap gap-2">{d.map((c) => <Badge key={c.slug} variant="outline">{c.name}</Badge>)}</div>);
  if (t === "clarify") return (<div className="mt-2 p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm"><strong>Need more info:</strong> {d.question}</div>);
  if (t === "reject") return (<div className="mt-2 p-3 rounded-xl bg-rose-50 border border-rose-200 text-sm"><strong>Refused:</strong> {d.reason}</div>);
  if (t === "deleted_product") return (<div className="mt-2 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm">Deleted: <strong>{d.name}</strong></div>);
  return null;
}

export default function AdminAIChat() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessions, setSessions] = useState([]);
  const endRef = useRef(null);

  const loadSessions = async () => { const { data } = await api.get("/admin/chat/sessions"); setSessions(data); };
  useEffect(() => { loadSessions(); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const loadSession = async (sid) => {
    setSessionId(sid);
    const { data } = await api.get(`/admin/chat/history?session_id=${sid}`);
    setMessages(data);
  };
  const newChat = () => { setSessionId(null); setMessages([]); };

  const send = async (text) => {
    if (!text.trim() || busy) return;
    setInput("");
    const userMsg = { role: "user", text, id: Math.random().toString() };
    setMessages((m) => [...m, userMsg]);
    setBusy(true);
    try {
      const { data } = await api.post("/admin/chat", { message: text, session_id: sessionId });
      if (!sessionId) setSessionId(data.session_id);
      const asst = { role: "assistant", text: data.reply, intent: data.intent, params: data.params, result: data.result, id: Math.random().toString() };
      setMessages((m) => [...m, asst]);
      if (data.result?.ok) toast.success(data.reply || "Done", { description: data.intent });
      else if (data.result?.error) toast.error(data.result.error);
      loadSessions();
    } catch (e) { toast.error("Chat error: " + (e?.response?.data?.detail || e.message)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="admin-ai-chat-page" className="-m-4 md:-m-8 min-h-[calc(100vh-2rem)] grid lg:grid-cols-[280px_1fr] gs-ai-glow">
      <aside className="hidden lg:flex flex-col border-r p-4" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }} data-testid="admin-ai-chat-history">
        <Button onClick={newChat} className="mb-3 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="admin-ai-chat-new-button"><Plus className="h-4 w-4 mr-2"/>New chat</Button>
        <div className="text-xs uppercase tracking-wider text-[var(--gs-muted)] mb-2 flex items-center gap-1"><History className="h-3 w-3"/>History</div>
        <div className="flex-1 overflow-auto space-y-1">
          {sessions.map((s) => (
            <button key={s.session_id} onClick={() => loadSession(s.session_id)} className={`w-full text-left text-xs px-3 py-2 rounded-lg truncate hover:bg-[var(--gs-surface-2)] ${sessionId === s.session_id ? "bg-[var(--gs-surface-2)] font-semibold" : ""}`}>{s.last || "New chat"}</button>
          ))}
          {sessions.length === 0 && <div className="text-xs text-[var(--gs-muted)] px-3 py-2">No history yet</div>}
        </div>
      </aside>

      <section className="flex flex-col h-[calc(100vh-2rem)]">
        <div className="border-b p-4 flex items-center gap-3" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}>
          <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gs-teal-soft)" }}><Sparkles className="h-5 w-5 text-[var(--gs-teal)]"/></div>
          <div><div className="font-semibold">AI Admin Chat</div><div className="text-xs text-[var(--gs-muted)]">Type natural commands. I'll run them for you.</div></div>
        </div>

        <div className="flex-1 overflow-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 && (
            <div className="max-w-xl mx-auto text-center py-10">
              <div className="h-14 w-14 mx-auto rounded-2xl grid place-items-center mb-4" style={{ background: "var(--gs-teal-soft)" }}><Sparkles className="h-7 w-7 text-[var(--gs-teal)]"/></div>
              <h2 className="font-display text-2xl mb-2">What can I help you with today?</h2>
              <p className="text-sm text-[var(--gs-muted)] mb-6">Try one of these commands or type your own.</p>
              <div className="flex flex-wrap gap-2 justify-center">{SUGGESTIONS.map((s) => (<button key={s} onClick={() => send(s)} className="text-xs px-3 py-2 rounded-full border hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }} data-testid={`ai-suggestion-${s.slice(0,10)}`}>{s}</button>))}</div>
            </div>
          )}
          <AnimatePresence>
            {messages.map((m) => (
              <motion.div key={m.id || m.created_at} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${m.role === "user" ? "bg-white border" : ""}`} style={{ borderColor: m.role === "user" ? "var(--gs-border)" : undefined, background: m.role === "user" ? "#fff" : "var(--gs-teal-soft)" }}>
                  <div className="text-sm whitespace-pre-wrap" data-testid={`ai-msg-${m.role}`}>{m.text}</div>
                  {m.role === "assistant" && m.intent && <div className="text-[10px] uppercase tracking-wider mt-1 text-[var(--gs-teal)] opacity-70">{m.intent}</div>}
                  {m.role === "assistant" && <ResultCard result={m.result}/>}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {busy && (<div className="flex justify-start"><div className="px-4 py-3 rounded-2xl flex items-center gap-2 text-sm" style={{ background: "var(--gs-teal-soft)" }}><Loader2 className="h-4 w-4 animate-spin"/>Thinking…</div></div>)}
          <div ref={endRef}/>
        </div>

        <div className="border-t p-3 sm:p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)", paddingBottom: "60px" }} data-testid="admin-ai-chat-composer">
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-end gap-2 max-w-3xl mx-auto">
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a command. e.g., Add product Floral Dress 1299 in fashion…" rows={1} className="resize-none min-h-[48px] max-h-32" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }} data-testid="admin-ai-chat-input"/>
            <Button type="submit" disabled={busy || !input.trim()} className="h-12 w-12 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="admin-ai-chat-send-button">{busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>}</Button>
          </form>
        </div>
      </section>
    </div>
  );
}
