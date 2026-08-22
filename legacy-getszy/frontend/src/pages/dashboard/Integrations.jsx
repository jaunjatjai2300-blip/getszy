import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Search, Link2, Unlink, Loader2, Plug, CheckCircle2, ExternalLink,
  Filter, Grid3X3, List,
} from "lucide-react";
import { toast } from "sonner";
import PageState from "@/components/dashboard/PageState";
import DashboardPageFrame from "@/components/dashboard/DashboardPageFrame";

export default function Integrations() {
  const [integrations, setIntegrations] = useState([]);
  const [categories, setCategories] = useState([]);
  const [connected, setConnected] = useState([]);
  const [cat, setCat] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState("grid");
  const [connecting, setConnecting] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [integRes, connRes] = await Promise.all([
        api.get("/integrations", { params: { category: cat, search } }),
        api.get("/integrations/connected"),
      ]);
      setIntegrations(integRes.data.integrations || []);
      setCategories(integRes.data.categories || []);
      setConnected(connRes.data.connections || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "We couldn't load integrations. Check your connection and try again.");
      toast.error("Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, [cat, search]);

  useEffect(() => { load(); }, [load]);

  const doSearch = async () => {
    setError(null);
    setLoading(true);
    try {
      const r = await api.get("/integrations", { params: { category: cat, search } });
      setIntegrations(r.data.integrations || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Search failed. Please try again.");
    } finally { setLoading(false); }
  };

  const connect = async (integ) => {
    // P0-7: no integration is production-ready for beta. UI shows Coming Soon
    // and offers to add the user to the waitlist. Backend also rejects — this
    // is a defence-in-depth guard, not just cosmetic.
    setConnecting(integ.id);
    try {
      await api.post("/integrations/waitlist", { integration_id: integ.id });
      toast.success(`You're on the ${integ.name} waitlist — we'll email you when it's live.`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't join waitlist");
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
    <DashboardPageFrame
      eyebrow="Connect"
      title="Bring your tools into one operating system"
      description="Find the integrations that fit your workflow, understand their readiness, and join the launch queue for features still in controlled rollout."
      icon={Plug}
      metrics={[{ label: "in catalog", value: integrations.length }, { label: "connected", value: connectedIds.size }]}
      hint="Use search to find your tool, then review its readiness before connecting or joining its launch waitlist."
      actions={
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-[var(--gs-teal)]/30 bg-[var(--gs-teal)]/10 text-xs text-[var(--gs-teal)]">{connectedIds.size} connected</Badge>
          <Button variant="outline" size="icon" onClick={() => setView(view === "grid" ? "list" : "grid")} aria-label={view === "grid" ? "Use list view" : "Use grid view"}>
            {view === "grid" ? <List className="h-4 w-4" /> : <Grid3X3 className="h-4 w-4" />}
          </Button>
        </div>
      }
    >

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
                onConnect={() => connect(integ)}
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
        {error ? (
          <PageState kind="error" title="Couldn't load integrations" message={error} onRetry={load} />
        ) : loading ? (
          <PageState kind="loading" title="Loading integrations…" />
        ) : integrations.filter((i) => !connectedIds.has(i.id)).length === 0 ? (
          <PageState kind="empty" title="No integrations found" message="Try a different category or search term." />
        ) : (
          <div className={view === "grid" ? "grid sm:grid-cols-2 lg:grid-cols-3 gap-3" : "space-y-2"}>
            {integrations.filter((i) => !connectedIds.has(i.id)).map((integ) => (
              <IntegrationCard
                key={integ.id}
                integ={integ}
                connected={false}
                onConnect={() => connect(integ)}
                onDisconnect={() => disconnect(integ.id)}
                busy={connecting === integ.id}
                view={view}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardPageFrame>
  );
}

function IntegrationCard({ integ, connected, onConnect, onDisconnect, busy, view }) {
  const [expanded, setExpanded] = useState(false);
  // P0-7: honour the backend availability flag. When `available === false`
  // (default for beta), the card renders in "Coming Soon" mode and the
  // connect action becomes a waitlist join.
  const comingSoon = integ.available === false || integ.coming_soon === true;

  if (view === "list") {
    return (
      <div className="gs-card p-3 flex items-center gap-3" data-testid={`integration-row-${integ.id}`}>
        <div className="h-10 w-10 rounded-xl grid place-items-center text-xl shrink-0"
          style={{ background: `${integ.color}22` }}>
          {integ.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">{integ.name}</span>
            {connected && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
            {comingSoon && (
              <Badge className="text-[9px] bg-amber-100 text-amber-800 border-amber-200" data-testid={`coming-soon-badge-${integ.id}`}>
                Coming Soon
              </Badge>
            )}
          </div>
          <p className="text-xs text-[var(--gs-muted)] truncate">{integ.description}</p>
        </div>
        {connected ? (
          <Button variant="outline" size="sm" onClick={onDisconnect} className="shrink-0 text-xs">
            <Unlink className="h-3 w-3 mr-1" /> Disconnect
          </Button>
        ) : comingSoon ? (
          <Button size="sm" onClick={onConnect} disabled={busy}
            className="shrink-0 text-xs" variant="outline"
            data-testid={`notify-me-btn-${integ.id}`}>
            {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
            Notify me
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
    <div className="gs-card p-4 hover:bg-[var(--gs-surface-2)] transition" data-testid={`integration-card-${integ.id}`}>
      <div className="flex items-start gap-3">
        <div className="h-12 w-12 rounded-2xl grid place-items-center text-2xl shrink-0"
          style={{ background: `${integ.color}22` }}>
          {integ.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-display text-base">{integ.name}</span>
            {connected && (
              <Badge className="text-[9px] bg-green-100 text-green-700 border-green-200">
                Connected
              </Badge>
            )}
            {comingSoon && (
              <Badge className="text-[9px] bg-amber-100 text-amber-800 border-amber-200"
                data-testid={`coming-soon-badge-${integ.id}`}>
                Coming Soon
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
        ) : comingSoon ? (
          <Button size="sm" onClick={onConnect} disabled={busy} variant="outline"
            className="text-xs h-7"
            data-testid={`notify-me-btn-${integ.id}`}>
            {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
            Notify me
          </Button>
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
