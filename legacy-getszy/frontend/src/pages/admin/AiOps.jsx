import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sparkles, Wand2, Bot, GraduationCap, Activity, Zap, Cpu, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

const AGENT_ICONS = { Builder: Wand2, "Admin Chat": Bot, "AI Tutor": GraduationCap };
const FEED_ICONS = { wand: Wand2, bot: Bot, graduation: GraduationCap };

export default function AdminAiOps() {
  const [data, setData] = useState(null);

  const load = async () => { const r = await api.get("/admin/ai-ops/stats"); setData(r.data); };
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  if (!data) return <div className="p-6 text-center">Loading…</div>;

  return (
    <div className="space-y-6" data-testid="admin-ai-ops-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl">AI Operations</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Live overview of every AI agent powering getszy</p>
        </div>
        <div className="gs-card px-4 py-3 flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gs-teal-soft)" }}><Cpu className="h-4 w-4 text-[var(--gs-teal)]"/></div>
          <div>
            <div className="text-xs text-[var(--gs-muted)] uppercase tracking-wider">Engine</div>
            <div className="font-semibold text-sm">Getszy AI · <span className="text-[var(--gs-teal)]">{data.engine?.provider === "ollama" ? "Local" : "Hosted"}</span></div>
          </div>
        </div>
      </div>

      {/* Agents */}
      <div className="grid sm:grid-cols-3 gap-4" data-testid="ai-ops-agents-grid">
        {data.agents.map((a) => {
          const Icon = AGENT_ICONS[a.name] || Sparkles;
          return (
            <div key={a.name} className="gs-card p-5 relative overflow-hidden">
              <div className="absolute inset-x-0 top-0 h-1" style={{ background: "var(--gs-teal)" }}/>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2"><div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gs-teal-soft)" }}><Icon className="h-4 w-4 text-[var(--gs-teal)]"/></div><div className="font-semibold">{a.name}</div></div>
                <Badge className="bg-emerald-100 text-emerald-700 hover:opacity-100"><span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse"/>Online</Badge>
              </div>
              <p className="text-xs text-[var(--gs-muted)] mb-3">{a.description}</p>
              <div className="grid grid-cols-2 gap-3">
                <div><div className="text-xs text-[var(--gs-muted)]">Today</div><div className="font-display text-2xl">{a.today}</div></div>
                <div><div className="text-xs text-[var(--gs-muted)]">Total</div><div className="font-display text-2xl">{a.total}</div></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Activity series */}
      <div className="gs-card p-5">
        <div className="flex items-center justify-between mb-3"><h3 className="font-semibold flex items-center gap-2"><TrendingUp className="h-4 w-4 text-[var(--gs-teal)]"/>Agent activity · last 7 days</h3></div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data.series_7d}>
            <defs>
              <linearGradient id="b" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#C58B7A" stopOpacity={0.5}/><stop offset="100%" stopColor="#C58B7A" stopOpacity={0}/></linearGradient>
              <linearGradient id="c" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2F7E7A" stopOpacity={0.5}/><stop offset="100%" stopColor="#2F7E7A" stopOpacity={0}/></linearGradient>
              <linearGradient id="t" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#A86B5B" stopOpacity={0.5}/><stop offset="100%" stopColor="#A86B5B" stopOpacity={0}/></linearGradient>
            </defs>
            <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
            <XAxis dataKey="date" stroke="#6B625B" fontSize={12}/><YAxis stroke="#6B625B" fontSize={12} allowDecimals={false}/>
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #E7D9CE", borderRadius: 8 }}/>
            <Legend wrapperStyle={{ fontSize: 12 }}/>
            <Area type="monotone" dataKey="builds" stroke="#A86B5B" fill="url(#b)" name="Builder"/>
            <Area type="monotone" dataKey="chats" stroke="#2F7E7A" fill="url(#c)" name="Admin Chat"/>
            <Area type="monotone" dataKey="tutor" stroke="#C58B7A" fill="url(#t)" name="AI Tutor"/>
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Top intents */}
        <div className="gs-card p-5">
          <h3 className="font-semibold flex items-center gap-2 mb-3"><Zap className="h-4 w-4 text-[var(--gs-teal)]"/>Top Admin Chat intents</h3>
          {(!data.intents || data.intents.length === 0) ? (
            <div className="text-sm text-[var(--gs-muted)] py-6 text-center">No intent data yet</div>
          ) : (
            <div className="space-y-2">
              {data.intents.map((i) => {
                const max = data.intents[0]?.count || 1;
                return (
                  <div key={i.intent}>
                    <div className="flex justify-between text-sm mb-1"><span className="font-mono text-xs">{i.intent}</span><span className="font-semibold">{i.count}</span></div>
                    <div className="h-1.5 rounded-full bg-[var(--gs-surface-2)] overflow-hidden"><div className="h-full bg-[var(--gs-teal)]" style={{ width: `${(i.count / max) * 100}%` }}/></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Live activity feed */}
        <div className="gs-card p-5" data-testid="ai-ops-feed">
          <h3 className="font-semibold flex items-center gap-2 mb-3"><Activity className="h-4 w-4 text-[var(--gs-teal)]"/>Live activity</h3>
          {data.feed.length === 0 ? (
            <div className="text-sm text-[var(--gs-muted)] py-6 text-center">No activity yet</div>
          ) : (
            <div className="space-y-2 max-h-[320px] overflow-auto pr-1">
              {data.feed.map((f, i) => {
                const Icon = FEED_ICONS[f.icon] || Sparkles;
                return (
                  <div key={i} className="flex items-start gap-2 text-sm py-1.5">
                    <div className="h-7 w-7 rounded-lg grid place-items-center flex-shrink-0" style={{ background: "var(--gs-teal-soft)" }}><Icon className="h-3.5 w-3.5 text-[var(--gs-teal)]"/></div>
                    <div className="flex-1 min-w-0"><div className="truncate">{f.label}</div><div className="text-[10px] text-[var(--gs-muted)]">{f.agent} · {new Date(f.at).toLocaleString()}</div></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
