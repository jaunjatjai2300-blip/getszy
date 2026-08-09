import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search, Link2, Unlink, Loader2, Plug, CheckCircle2, ExternalLink,
  Filter, Grid3X3, List,
} from "lucide-react";
import { toast } from "sonner";

export default function Integrations() {
  const [integrations, setIntegrations] = useState([]);
  const [categories, setCategories] = useState([]);
  const [connected, setConnected] = useState([]);
  const [cat, setCat] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("grid");
  const [connecting, setConnecting] = useState(null);

  useEffect(() => { load(); }, [cat]);

  const load = async () => {
    try {
      const [integRes, connRes] = await Promise.all([
        api.get("/integrations", { params: { category: cat, search } }),
        api.get("/integrations/connected"),
      ]);
      setIntegrations(integRes.data.integrations || []);
      setCategories(integRes.data.categories || []);
      setConnected(connRes.data.connections || []);
    } catch (e) {
      toast.error("Failed to load integrations");
    } finally {
      setLoading(false);
    }
  };

  const doSearch = async () => {
    setLoading(true);
    try {
      const r = await api.get("/integrations", { params: { category: cat, search } });
      setIntegrations(r.data.integrations || []);
    } catch (e) { /* ignore */ }
    finally { setLoading(false); }
  };

  const connect = async (id) => {
    setConnecting(id);
    try {
      await api.post("/integrations/connect", { integration_id: id });
      toast.success("Connected!");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Connection failed");
    } finally {
      setConnecting(null);
    }
  };

  const disconnect = async (id) => {
    try {
      await api.post("/integrations/disconnect", { integration_id: id });
      toast.success("Disconnected");
      load();
    } catch (e) {
      toast.error("Failed to disconnect");
    }
  };

  const connectedIds = new Set(connected.map((c) => c.integration_id));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Plug className="h-7 w-7 text-[var(--gs-teal)]" /> Integrations
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            Connect your favorite tools. {integrations.length} integrations available.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {connectedIds.size} connected
          </Badge>
          <button onClick={() => setView(view === "grid" ? "list" : "grid")}
            className="p-2 rounded-lg hover:bg-[var(--gs-surface-2)]">
            {view === "grid" ? <List className="h-4 w-4" /> : <Grid3X3 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div className="flex gap-3 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--gs-muted)]" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            placeholder="Search integrations..."
            className="pl-9"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button onClick={() => setCat("")}
          className={`px-3 py-1.5 rounded-lg text-xs transition-all ${
            !cat ? "bg-[var(--gs-teal)] text-white" : "bg-white border hover:bg-[var(--gs-surface-2)]"
          }`}>
          All
        </button>
        {categories.map((c) => (
          <button key={c.id} onClick={() => setCat(c.id)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-all ${
              cat === c.id ? "bg-[var(--gs-teal)] text-white" : "bg-white border hover:bg-[var(--gs-surface-2)]"
            }`}>
            {c.icon} {c.label}
          </button>
        ))}
      </div>

      {connectedIds.size > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs uppercase tracking-wider text-[var(--gs-muted)] font-semibold">
            Connected
          </h2>
          <div className={view === "grid" ? "grid sm:grid-cols-2 lg:grid-cols-3 gap-3" : "space-y-2"}>
            {integrations.filter((i) => connectedIds.has(i.id)).map((integ) => (
              <IntegrationCard
                key={integ.id}
                integ={integ}
                connected={true}
                onConnect={() => connect(integ.id)}
                onDisconnect={() => disconnect(integ.id)}
                busy={connecting === integ.id}
                view={view}
              />
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h2 className="text-xs uppercase tracking-wider text-[var(--gs-muted)] font-semibold">
          {cat ? categories.find((c) => c.id === cat)?.label || cat : "All Integrations"}
        </h2>
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" />
          </div>
        ) : (
          <div className={view === "grid" ? "grid sm:grid-cols-2 lg:grid-cols-3 gap-3" : "space-y-2"}>
            {integrations.filter((i) => !connectedIds.has(i.id)).map((integ) => (
              <IntegrationCard
                key={integ.id}
                integ={integ}
                connected={false}
                onConnect={() => connect(integ.id)}
                onDisconnect={() => disconnect(integ.id)}
                busy={connecting === integ.id}
                view={view}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IntegrationCard({ integ, connected, onConnect, onDisconnect, busy, view }) {
  const [expanded, setExpanded] = useState(false);

  if (view === "list") {
    return (
      <div className="gs-card p-3 flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl grid place-items-center text-xl shrink-0"
          style={{ background: `${integ.color}22` }}>
          {integ.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{integ.name}</span>
            {connected && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
          </div>
          <p className="text-xs text-[var(--gs-muted)] truncate">{integ.description}</p>
        </div>
        {connected ? (
          <Button variant="outline" size="sm" onClick={onDisconnect} className="shrink-0 text-xs">
            <Unlink className="h-3 w-3 mr-1" /> Disconnect
          </Button>
        ) : (
          <Button size="sm" onClick={onConnect} disabled={busy} className="shrink-0 text-xs bg-[var(--gs-teal)] text-white">
            {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Link2 className="h-3 w-3 mr-1" />}
            Connect
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="gs-card p-4 hover:bg-[var(--gs-surface-2)] transition">
      <div className="flex items-start gap-3">
        <div className="h-12 w-12 rounded-2xl grid place-items-center text-2xl shrink-0"
          style={{ background: `${integ.color}22` }}>
          {integ.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-display text-base">{integ.name}</span>
            {connected && (
              <Badge className="text-[9px] bg-green-100 text-green-700 border-green-200">
                Connected
              </Badge>
            )}
          </div>
          <p className="text-xs text-[var(--gs-muted)] mt-1 line-clamp-2">
            {integ.description}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[9px]">{integ.auth_type}</Badge>
          <Badge variant="outline" className="text-[9px]">{integ.category}</Badge>
        </div>
        {connected ? (
          <div className="flex gap-1.5">
            <Button variant="ghost" size="sm" className="text-xs h-7" onClick={() => setExpanded(!expanded)}>
              <ExternalLink className="h-3 w-3 mr-1" /> Settings
            </Button>
            <Button variant="outline" size="sm" className="text-xs h-7 text-red-500" onClick={onDisconnect}>
              Disconnect
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={onConnect} disabled={busy}
            className="text-xs h-7 bg-[var(--gs-teal)] text-white">
            {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Link2 className="h-3 w-3 mr-1" />}
            Connect
          </Button>
        )}
      </div>

      {expanded && connected && (
        <div className="mt-3 p-3 rounded-xl bg-[var(--gs-surface-2)] text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-[var(--gs-muted)]">Status</span>
            <span className="text-green-600 font-semibold">Active</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--gs-muted)]">Connected</span>
            <span>{integ.connected_at ? new Date(integ.connected_at).toLocaleDateString() : "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--gs-muted)]">Auth Type</span>
            <span className="capitalize">{integ.auth_type?.replace(/_/g, " ")}</span>
          </div>
        </div>
      )}
    </div>
  );
}
