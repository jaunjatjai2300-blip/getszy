import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Plug, Search, Users, Link2, Loader2, TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

export default function IntegrationsAdmin() {
  const [integrations, setIntegrations] = useState([]);
  const [analytics, setAnalytics] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const [integRes, analyticsRes] = await Promise.all([
        api.get("/admin/integrations"),
        api.get("/admin/integrations/analytics"),
      ]);
      setIntegrations(integRes.data.integrations || []);
      setAnalytics(analyticsRes.data.analytics || []);
    } catch (e) {
      toast.error("Failed to load");
    } finally {
      setLoading(false);
    }
  };

  const analyticsMap = {};
  analytics.forEach((a) => { analyticsMap[a.integration_id] = a; });

  const filtered = search
    ? integrations.filter(
        (i) =>
          i.name.toLowerCase().includes(search.toLowerCase()) ||
          i.description.toLowerCase().includes(search.toLowerCase())
      )
    : integrations;

  const totalConnections = integrations.reduce((s, i) => s + (i.total_connections || 0), 0);
  const totalActive = integrations.reduce((s, i) => s + (i.active_connections || 0), 0);

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
        <h1 className="font-display text-3xl">Integrations</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">
          Manage the integration marketplace and view connection analytics.
        </p>
      </div>

      <div className="grid sm:grid-cols-4 gap-4">
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Total Integrations</div>
          <div className="text-2xl font-bold mt-1">{integrations.length}</div>
        </div>
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Total Connections</div>
          <div className="text-2xl font-bold mt-1">{totalConnections}</div>
        </div>
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Active Connections</div>
          <div className="text-2xl font-bold mt-1 text-green-600">{totalActive}</div>
        </div>
        <div className="gs-card p-4">
          <div className="text-xs text-[var(--gs-muted)]">Categories</div>
          <div className="text-2xl font-bold mt-1">
            {new Set(integrations.map((i) => i.category)).size}
          </div>
        </div>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search integrations..."
          className="pl-9"
        />
      </div>

      <div className="gs-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: "var(--gs-border)" }}>
                <th className="text-left p-3 text-xs text-[var(--gs-muted)] font-semibold">Integration</th>
                <th className="text-left p-3 text-xs text-[var(--gs-muted)] font-semibold">Category</th>
                <th className="text-left p-3 text-xs text-[var(--gs-muted)] font-semibold">Auth</th>
                <th className="text-right p-3 text-xs text-[var(--gs-muted)] font-semibold">Connections</th>
                <th className="text-right p-3 text-xs text-[var(--gs-muted)] font-semibold">Active</th>
                <th className="text-right p-3 text-xs text-[var(--gs-muted)] font-semibold">Users</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((integ) => {
                const stats = analyticsMap[integ.id] || {};
                return (
                  <tr key={integ.id} className="border-b hover:bg-[var(--gs-surface-2)]"
                    style={{ borderColor: "var(--gs-border)" }}>
                    <td className="p-3">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg grid place-items-center text-lg shrink-0"
                          style={{ background: `${integ.color}22` }}>
                          {integ.icon}
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{integ.name}</div>
                          <div className="text-xs text-[var(--gs-muted)] truncate max-w-[300px]">
                            {integ.description}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge variant="outline" className="text-[10px]">{integ.category}</Badge>
                    </td>
                    <td className="p-3">
                      <Badge variant="outline" className="text-[10px]">{integ.auth_type}</Badge>
                    </td>
                    <td className="p-3 text-right text-sm font-semibold">
                      {integ.total_connections || stats.total || 0}
                    </td>
                    <td className="p-3 text-right">
                      <span className="text-sm font-semibold text-green-600">
                        {integ.active_connections || stats.active || 0}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Users className="h-3 w-3 text-[var(--gs-muted)]" />
                        <span className="text-sm">{stats.unique_users || 0}</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
