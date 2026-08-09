import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Users, MessageSquare, TrendingUp, Loader2, Save, Settings,
} from "lucide-react";
import { toast } from "sonner";

export default function AgentsAdmin() {
  const [agents, setAgents] = useState([]);
  const [analytics, setAnalytics] = useState([]);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const [agentsRes, analyticsRes] = await Promise.all([
        api.get("/admin/agents"),
        api.get("/admin/agents/analytics"),
      ]);
      setAgents(agentsRes.data.agents || []);
      setAnalytics(analyticsRes.data.analytics || []);
    } catch (e) {
      toast.error("Failed to load");
    } finally {
      setLoading(false);
    }
  };

  const saveAgent = async (agentId, updates) => {
    try {
      await api.put(`/admin/agents/${agentId}`, updates);
      toast.success("Updated");
      setEditing(null);
      load();
    } catch (e) {
      toast.error("Failed to update");
    }
  };

  const analyticsMap = {};
  analytics.forEach((a) => { analyticsMap[a.agent_id] = a; });

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Expert Agents</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">
          Manage AI specialist agents and view usage analytics.
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Total Agents</div>
          <div className="text-2xl font-bold mt-1">{agents.length}</div>
        </div>
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Total Chats</div>
          <div className="text-2xl font-bold mt-1">
            {agents.reduce((s, a) => s + (a.total_chats || 0), 0)}
          </div>
        </div>
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Unique Users</div>
          <div className="text-2xl font-bold mt-1">
            {agents.reduce((s, a) => s + (a.unique_users || 0), 0)}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {agents.map((agent) => {
          const stats = analyticsMap[agent.id] || {};
          const isEditing = editing === agent.id;

          return (
            <div key={agent.id} className="gs-card p-5">
              <div className="flex items-start gap-4">
                <div className="h-14 w-14 rounded-2xl grid place-items-center text-2xl shrink-0"
                  style={{ background: `${agent.color}22` }}>
                  {agent.avatar}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-display text-lg">{agent.name}</h3>
                    <Badge variant="outline" className="text-[10px]">
                      {agent.total_chats || 0} chats
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      {agent.unique_users || 0} users
                    </Badge>
                  </div>
                  <p className="text-xs text-[var(--gs-muted)] mt-1">{agent.description}</p>

                  <div className="flex gap-1.5 mt-2">
                    {(agent.tools || []).map((t) => (
                      <Badge key={t} variant="outline" className="text-[9px]">
                        {t.replace(/_/g, " ")}
                      </Badge>
                    ))}
                  </div>

                  {isEditing ? (
                    <div className="mt-4 space-y-3">
                      <div>
                        <label className="text-xs text-[var(--gs-muted)]">System Prompt</label>
                        <Textarea
                          defaultValue={agent.system}
                          rows={4}
                          className="mt-1 text-xs font-mono"
                          id={`sys-${agent.id}`}
                        />
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="text-xs bg-[var(--gs-teal)] text-white"
                          onClick={() => {
                            const sys = document.getElementById(`sys-${agent.id}`)?.value;
                            saveAgent(agent.id, { system: sys });
                          }}
                        >
                          <Save className="h-3 w-3 mr-1" /> Save
                        </Button>
                        <Button size="sm" variant="outline" className="text-xs" onClick={() => setEditing(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-xs mt-2"
                      onClick={() => setEditing(agent.id)}
                    >
                      <Settings className="h-3 w-3 mr-1" /> Configure
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
