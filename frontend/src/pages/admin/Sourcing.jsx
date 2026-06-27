import { useEffect, useState } from "react";
import { api, fmtINR, API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { TrendingUp, Sparkles, Package, Truck, RefreshCw, Plus, IndianRupee, Globe, AlertCircle, CheckCircle2 } from "lucide-react";
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

  const loadStatus = async () => {
    try { const r = await api.get("/admin/sourcing/status"); setStatus(r.data); setTrending(r.data.last_scan || { items: [], at: null }); } catch (e) {}
  };
  const loadTrending = async () => {
    try { const r = await api.get("/admin/sourcing/trending"); setTrending(r.data); } catch (e) {}
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
        <Button onClick={scan} disabled={scanning} data-testid="trending-scan-button" className="gap-2">
          {scanning ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
          {scanning ? "Scanning trends…" : "Scan trending now"}
        </Button>
      </div>

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
                <div className="aspect-[4/3] bg-[var(--gs-surface-2)] relative">
                  <img src={resolveUrl(it.hero_image)} alt={it.title} loading="lazy" className="w-full h-full object-cover"/>
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
