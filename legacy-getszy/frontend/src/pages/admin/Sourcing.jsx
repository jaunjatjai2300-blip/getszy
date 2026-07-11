import { useEffect, useState } from "react";
import { api, fmtINR, API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { TrendingUp, Sparkles, Package, Truck, RefreshCw, Plus, IndianRupee, Globe, AlertCircle, CheckCircle2, Key, Search } from "lucide-react";
import { toast } from "sonner";

const AUDIENCE_COLORS = { women: "#9b6a3f", girls: "#c97a87", kids: "#5d8f8e" };
const resolveUrl = (u) => {
  if (!u) return u;
  if (u.startsWith("/api/")) return `${API_BASE.replace(/\/api$/, "")}${u}`;
  return u;
};

export default function AdminSourcing() {
  const [status, setStatus] = useState(null);
  const [trending, setTrending] = useState({ items: [], at: null });
  const [scanning, setScanning] = useState(false);
  const [importing, setImporting] = useState({});
  const [calc, setCalc] = useState({ cost: 200, is_digital: false, result: null });
  const [showKeyPanel, setShowKeyPanel] = useState(false);
  const [keys, setKeys] = useState({ CJ_EMAIL: "", CJ_API_KEY: "", SHIPROCKET_EMAIL: "", SHIPROCKET_PASSWORD: "" });
  const [savingKeys, setSavingKeys] = useState(false);
  const [cjSearch, setCjSearch] = useState({ keyword: "fashion", results: [], loading: false });

  const loadStatus = async () => {
    try { const r = await api.get("/admin/sourcing/status"); setStatus(r.data); setTrending(r.data.last_scan || { items: [], at: null }); } catch (e) {}
  };
  const loadTrending = async () => {
    try { const r = await api.get("/admin/sourcing/trending"); setTrending(r.data); } catch (e) {}
  };
  const saveKeys = async () => {
    setSavingKeys(true);
    try {
      const r = await api.post("/admin/sourcing/config/keys", keys);
      toast.success("Keys saved! CJ: " + (r.data.cj_configured ? "✓" : "✗") + " · Shiprocket: " + (r.data.shiprocket_configured ? "✓" : "✗"));
      await loadStatus();
      setShowKeyPanel(false);
    } catch (e) { toast.error("Save failed"); }
    finally { setSavingKeys(false); }
  };

  const searchCJ = async () => {
    setCjSearch(s => ({ ...s, loading: true }));
    try {
      const r = await api.get(`/admin/sourcing/cj/products?keyword=${encodeURIComponent(cjSearch.keyword)}`);
      if (r.data.status === "not_configured") { toast.error("CJ API keys not set. Use 'Configure Keys' button."); }
      else { setCjSearch(s => ({ ...s, results: r.data.items || [] })); }
    } catch (e) { toast.error("Search failed"); }
    finally { setCjSearch(s => ({ ...s, loading: false })); }
  };

  const scan = async () => {
    setScanning(true);
    try { const r = await api.post("/admin/sourcing/trending/scan?limit=12"); setTrending({ items: r.data.items, at: new Date().toISOString() }); toast.success(`${r.data.count} trending products discovered`); }
    catch (e) { toast.error("Scan failed"); } finally { setScanning(false); }
  };
  const importProduct = async (item) => {
    setImporting((p) => ({ ...p, [item.id]: true }));
    try {
      const r = await api.post("/admin/sourcing/import", {
        title: item.title, cost_price: item.cost_price, suggested_price: item.suggested_price,
        category: item.category, hero_image: item.hero_image, audience: item.audience, niche: item.niche,
      });
      toast.success(`Imported — ${r.data.margin.margin_pct}% margin locked in`);
    } catch (e) { toast.error("Import failed"); } finally { setImporting((p) => ({ ...p, [item.id]: false })); }
  };

  const recalcMarkup = async () => {
    try {
      const r = await api.post("/admin/sourcing/markup/check", { cost_price: Number(calc.cost), is_digital: calc.is_digital });
      setCalc((c) => ({ ...c, result: r.data }));
    } catch (e) {}
  };

  useEffect(() => { loadStatus(); loadTrending(); }, []);

  return (
    <div className="space-y-6" data-testid="admin-sourcing-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl">Getszy Source</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">AI-curated trending products + dropshipping automation for India</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowKeyPanel(p => !p)} className="gap-2 text-xs" data-testid="configure-keys-button">
            <Key className="h-3.5 w-3.5"/>Configure Keys
          </Button>
          <Button onClick={scan} disabled={scanning} data-testid="trending-scan-button" className="gap-2">
            {scanning ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
            {scanning ? "Scanning…" : "Scan trending"}
          </Button>
        </div>
      </div>

      {/* Key Config Panel */}
      {showKeyPanel && (
        <div className="gs-card p-5 border-amber-200 bg-amber-50/50 space-y-4" data-testid="key-config-panel">
          <h3 className="font-semibold flex items-center gap-2"><Key className="h-4 w-4 text-amber-600"/>API Key Configuration</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider">CJ Dropshipping</p>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">CJ Email</label>
                <Input value={keys.CJ_EMAIL} onChange={e => setKeys(k => ({...k, CJ_EMAIL: e.target.value}))} placeholder="you@example.com" className="mt-1 text-sm" data-testid="cj-email-input"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">CJ API Key</label>
                <Input type="password" value={keys.CJ_API_KEY} onChange={e => setKeys(k => ({...k, CJ_API_KEY: e.target.value}))} placeholder="CJ API key" className="mt-1 text-sm" data-testid="cj-key-input"/>
              </div>
              <p className="text-[10px] text-[var(--gs-muted)]">Get from <span className="font-mono">app.cjdropshipping.com → API</span></p>
            </div>
            <div className="space-y-3">
              <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider">Shiprocket</p>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Shiprocket Email</label>
                <Input value={keys.SHIPROCKET_EMAIL} onChange={e => setKeys(k => ({...k, SHIPROCKET_EMAIL: e.target.value}))} placeholder="shiprocket@you.com" className="mt-1 text-sm" data-testid="sr-email-input"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Shiprocket Password</label>
                <Input type="password" value={keys.SHIPROCKET_PASSWORD} onChange={e => setKeys(k => ({...k, SHIPROCKET_PASSWORD: e.target.value}))} placeholder="Account password" className="mt-1 text-sm" data-testid="sr-pass-input"/>
              </div>
              <p className="text-[10px] text-[var(--gs-muted)]">Same credentials as <span className="font-mono">app.shiprocket.in</span></p>
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <Button onClick={saveKeys} disabled={savingKeys} className="gap-2" data-testid="save-keys-button">
              {savingKeys ? <RefreshCw className="h-4 w-4 animate-spin"/> : <CheckCircle2 className="h-4 w-4"/>}
              {savingKeys ? "Saving…" : "Save & Activate"}
            </Button>
            <Button variant="outline" onClick={() => setShowKeyPanel(false)}>Cancel</Button>
          </div>
        </div>
      )}

      {/* Supplier Network Status */}
      <div className="grid sm:grid-cols-3 gap-4" data-testid="supplier-status-grid">
        <SupplierCard
          icon={Globe} title={status?.getszy_source?.label || "Getszy Source"} subtitle={`${status?.getszy_source?.supplier_count || 4} Indian suppliers`}
          deliveryDays={status?.getszy_source?.avg_delivery_days || "5-7"} enabled={true} note="Always free · no key needed"
        />
        <SupplierCard
          icon={Package} title="CJ Dropshipping" subtitle={status?.cj_dropshipping?.enabled ? "Connected" : "Add API key to enable"}
          deliveryDays={status?.cj_dropshipping?.avg_delivery_days || "7-12"} enabled={!!status?.cj_dropshipping?.enabled}
          note="Set CJ_EMAIL + CJ_API_KEY env vars"
        />
        <SupplierCard
          icon={Truck} title="Shiprocket" subtitle={status?.shiprocket?.enabled ? "Active" : "Configure for 5–6 day shipping"}
          deliveryDays={status?.shiprocket?.avg_delivery_days || "5-6"} enabled={!!status?.shiprocket?.enabled}
          note="Set SHIPROCKET_EMAIL + PASSWORD env vars"
        />
      </div>

      {/* Margin Calculator */}
      <div className="gs-card p-5">
        <div className="flex items-center gap-2 mb-3"><IndianRupee className="h-4 w-4 text-[var(--gs-teal)]"/><h3 className="font-display text-xl">Margin Guard</h3></div>
        <p className="text-sm text-[var(--gs-muted)] mb-4">Physical floor: 40% · Digital floor: 70%. Prices auto-corrected on import.</p>
        <div className="flex flex-wrap items-end gap-3">
          <div><label className="text-xs text-[var(--gs-muted)]">Supplier cost (₹)</label><Input type="number" value={calc.cost} onChange={(e) => setCalc((c) => ({ ...c, cost: e.target.value }))} className="w-32" data-testid="markup-cost-input"/></div>
          <div className="flex items-center gap-2 h-10">
            <input type="checkbox" id="is_digital" checked={calc.is_digital} onChange={(e) => setCalc((c) => ({ ...c, is_digital: e.target.checked }))}/>
            <label htmlFor="is_digital" className="text-sm">Digital product</label>
          </div>
          <Button variant="outline" onClick={recalcMarkup} data-testid="markup-calc-button">Calculate</Button>
          {calc.result && (
            <div className="flex items-center gap-4 text-sm ml-2">
              <div><span className="text-[var(--gs-muted)]">Sell at</span> <span className="font-bold text-[var(--gs-teal)]">{fmtINR(calc.result.suggested_price)}</span></div>
              <div><span className="text-[var(--gs-muted)]">Margin</span> <span className="font-bold">{calc.result.margin_pct}%</span></div>
              <div><span className="text-[var(--gs-muted)]">Profit/unit</span> <span className="font-bold">{fmtINR(calc.result.profit)}</span></div>
            </div>
          )}
        </div>
      </div>

      {/* CJ Dropshipping search */}
      {status?.cj_dropshipping?.enabled && (
        <div className="gs-card p-5 space-y-3" data-testid="cj-search-panel">
          <h3 className="font-semibold flex items-center gap-2"><Package className="h-4 w-4 text-[var(--gs-teal)]"/>CJ Dropshipping Search</h3>
          <div className="flex gap-2">
            <Input value={cjSearch.keyword} onChange={e => setCjSearch(s => ({...s, keyword: e.target.value}))} placeholder="e.g. fashion, kids toys, gadgets" className="flex-1" data-testid="cj-search-input" onKeyDown={e => e.key === "Enter" && searchCJ()}/>
            <Button onClick={searchCJ} disabled={cjSearch.loading} className="gap-2" data-testid="cj-search-button">
              {cjSearch.loading ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Search className="h-4 w-4"/>}Search
            </Button>
          </div>
          {cjSearch.results.length > 0 && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-2">
              {cjSearch.results.slice(0, 9).map((it, i) => (
                <div key={i} className="border rounded-xl p-3 space-y-1" style={{ borderColor: "var(--gs-border)" }}>
                  <div className="text-sm font-semibold line-clamp-2">{it.productNameEn || it.productName}</div>
                  <div className="text-xs text-[var(--gs-muted)]">{it.categoryName}</div>
                  <div className="text-xs font-mono text-[var(--gs-teal)]">${it.sellPrice || "—"}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Trending grid */}
      <div>
        <div className="flex items-center gap-2 mb-3"><TrendingUp className="h-5 w-5 text-[var(--gs-teal)]"/><h2 className="font-display text-2xl">Trending picks for India</h2></div>
        {!trending.items?.length ? (
          <div className="gs-card p-10 text-center">
            <Sparkles className="h-10 w-10 mx-auto text-[var(--gs-muted)] mb-2"/>
            <p className="text-sm text-[var(--gs-muted)] mb-3">No scan yet — hit “Scan trending now” to let the AI agents curate today’s picks.</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="trending-grid">
            {trending.items.map((it) => (
              <article key={it.id} className="gs-card overflow-hidden flex flex-col">
                <div className="aspect-[4/3] bg-[var(--gs-surface-2)] relative overflow-hidden">
                  <div className="absolute inset-0 grid place-items-center text-[var(--gs-muted)]">
                    <Sparkles className="h-8 w-8 animate-pulse opacity-40"/>
                  </div>
                  <img src={resolveUrl(it.hero_image)} alt={it.title} loading="lazy" className="relative w-full h-full object-cover" onLoad={(e) => e.currentTarget.classList.add("opacity-100")} onError={(e) => { e.currentTarget.style.display = "none"; }} style={{ opacity: 0, transition: "opacity 300ms" }}/>
                  <div className="absolute top-2 left-2 flex items-center gap-1 bg-white/90 backdrop-blur px-2 py-1 rounded-full text-xs font-semibold"><TrendingUp className="h-3 w-3 text-[var(--gs-teal)]"/>{it.trend_score}</div>
                  <Badge className="absolute top-2 right-2 capitalize" style={{ background: AUDIENCE_COLORS[it.audience] || "#666", color: "white" }}>{it.audience}</Badge>
                </div>
                <div className="p-4 flex-1 flex flex-col">
                  <h3 className="font-semibold text-base leading-snug line-clamp-2">{it.title}</h3>
                  <p className="text-xs text-[var(--gs-muted)] mt-1">{it.niche}</p>
                  <div className="flex items-center justify-between mt-3 text-sm">
                    <div><span className="text-[var(--gs-muted)] text-xs">Cost</span><div className="font-semibold">{fmtINR(it.cost_price)}</div></div>
                    <div><span className="text-[var(--gs-muted)] text-xs">Sell</span><div className="font-semibold text-[var(--gs-teal)]">{fmtINR(it.suggested_price)}</div></div>
                    <div><span className="text-[var(--gs-muted)] text-xs">Margin</span><div className="font-semibold">{it.margin_pct}%</div></div>
                  </div>
                  <div className="flex items-center gap-2 mt-3 text-xs text-[var(--gs-muted)]"><Truck className="h-3 w-3"/>Ships in {it.shipping_days} days</div>
                  <Button onClick={() => importProduct(it)} disabled={!!importing[it.id]} className="mt-4 gap-2" data-testid={`import-${it.id}`}>
                    {importing[it.id] ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Plus className="h-4 w-4"/>}
                    Import to store
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SupplierCard({ icon: Icon, title, subtitle, deliveryDays, enabled, note }) {
  return (
    <div className="gs-card p-4" data-testid={`supplier-card-${title.toLowerCase().replace(/[^a-z]/g, "-")}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: enabled ? "var(--gs-teal-soft)" : "var(--gs-surface-2)" }}>
            <Icon className={`h-5 w-5 ${enabled ? "text-[var(--gs-teal)]" : "text-[var(--gs-muted)]"}`}/>
          </div>
          <div>
            <div className="font-semibold text-sm">{title}</div>
            <div className="text-xs text-[var(--gs-muted)]">{subtitle}</div>
          </div>
        </div>
        {enabled ? <CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)]"/> : <AlertCircle className="h-4 w-4 text-amber-500"/>}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="text-[var(--gs-muted)]">Avg delivery</span>
        <span className="font-bold">{deliveryDays} days</span>
      </div>
      {!enabled && <div className="mt-2 text-[10px] text-[var(--gs-muted)] leading-snug">{note}</div>}
    </div>
  );
}
