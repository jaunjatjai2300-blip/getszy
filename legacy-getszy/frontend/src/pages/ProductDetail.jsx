import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, fmtINR, API_BASE } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ShoppingBag, Plus, Minus, Truck, ShieldCheck, RotateCcw, ScanFace, Sparkles, Download, RefreshCw } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { toast } from "sonner";

const resolveUrl = (u) => {
  if (!u) return u;
  if (u.startsWith("/api/")) return `${API_BASE.replace(/\/api$/, "")}${u}`;
  return u;
};

const SETTINGS = [
  { id: "studio", label: "Studio Portrait" },
  { id: "outdoor", label: "Outdoor Lifestyle" },
  { id: "festive", label: "Festive Look" },
];

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { add } = useCart();
  const [p, setP] = useState(null);
  const [qty, setQty] = useState(1);

  // Mirror AI try-on state
  const [tryOnOpen, setTryOnOpen] = useState(false);
  const [setting, setSetting] = useState("studio");
  const [tryOnBusy, setTryOnBusy] = useState(false);
  const [tryOnResult, setTryOnResult] = useState(null);
  const [tryOnCost, setTryOnCost] = useState(null);

  useEffect(() => { api.get(`/products/${id}`).then(({ data }) => setP(data)).catch(() => setP(false)); }, [id]);
  useEffect(() => { if (user) api.get("/credits/costs").then(({ data }) => setTryOnCost(data.costs?.tryon)).catch(() => {}); }, [user]);

  if (p === null) return <div className="gs-container py-20 text-center">Loading…</div>;
  if (!p) return <div className="gs-container py-20 text-center">Product not found</div>;

  const img = (p.images && p.images[0]) || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=800";

  const onAdd = async () => {
    if (!user) { navigate("/login"); return; }
    try { await add(p.id, qty); toast.success(`Added ${qty} × ${p.name} to cart`); }
    catch { toast.error("Failed to add"); }
  };

  const runTryOn = async () => {
    if (!user) { navigate("/login"); return; }
    setTryOnBusy(true);
    setTryOnResult(null);
    toast.loading("Mirror AI is generating your virtual try-on… (~15s)", { id: "tryon", duration: 30000 });
    try {
      const r = await api.post("/media/tryon", {
        product_id: p.id,
        product_name: p.name,
        product_image: img,
        setting,
      });
      setTryOnResult(r.data);
      toast.success("Mirror AI ready!", { id: "tryon" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Mirror AI failed", { id: "tryon" });
    } finally { setTryOnBusy(false); }
  };

  // Mirror AI is shown only for physical products
  const showMirror = !p.is_digital;

  return (
    <div className="gs-container gs-section grid md:grid-cols-2 gap-10" data-testid="product-detail-page">
      <div className="rounded-2xl overflow-hidden" style={{ background: "var(--gs-surface-2)" }}>
        <img src={img} alt={p.name} className="w-full aspect-square object-cover"/>
      </div>
      <div>
        <div className="flex items-center gap-2 mb-2">
          {p.is_featured && <Badge className="bg-[var(--gs-champagne)] text-[var(--gs-ink)] hover:bg-[var(--gs-champagne)]">Bestseller</Badge>}
          {p.is_digital && <Badge className="bg-[var(--gs-teal)]">Digital</Badge>}
        </div>
        <h1 className="font-display text-3xl sm:text-4xl mb-3">{p.name}</h1>
        <div className="text-3xl font-display mb-4">{fmtINR(p.price)}</div>
        <p className="text-[var(--gs-muted)] mb-6">{p.description}</p>
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center border rounded-xl" style={{ borderColor: "var(--gs-border)" }}>
            <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="h-11 w-11 grid place-items-center" data-testid="product-detail-qty-minus"><Minus className="h-4 w-4"/></button>
            <span className="w-10 text-center font-medium" data-testid="product-detail-quantity-input">{qty}</span>
            <button onClick={() => setQty((q) => q + 1)} className="h-11 w-11 grid place-items-center" data-testid="product-detail-qty-plus"><Plus className="h-4 w-4"/></button>
          </div>
          <Button onClick={onAdd} className="h-12 px-6 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] flex-1" data-testid="product-detail-add-to-cart-button"><ShoppingBag className="h-4 w-4 mr-2"/>Add to Cart</Button>
        </div>

        {showMirror && (
          <Dialog open={tryOnOpen} onOpenChange={setTryOnOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="w-full h-12 mb-6 border-2 border-[var(--gs-teal)] text-[var(--gs-teal)] hover:bg-[var(--gs-teal-soft)] gap-2" data-testid="product-detail-mirror-ai-button">
                <ScanFace className="h-4 w-4"/>Try with Mirror AI
                <Badge className="ml-2 bg-[var(--gs-teal-soft)] text-[var(--gs-teal)] text-[10px]">NEW</Badge>
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl" data-testid="mirror-ai-dialog">
              <DialogHeader>
                <DialogTitle className="font-display text-2xl flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-[var(--gs-teal)]"/>Mirror AI · Virtual Try-On
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <p className="text-sm text-[var(--gs-muted)]">See how <strong>{p.name}</strong> looks on a model in your chosen setting. Powered by Getszy AI.</p>
                <div>
                  <label className="text-xs text-[var(--gs-muted)] mb-2 block">Choose a setting</label>
                  <div className="flex gap-2 flex-wrap">
                    {SETTINGS.map((s) => (
                      <button key={s.id} onClick={() => setSetting(s.id)} className={`px-4 py-2 rounded-full text-sm border ${setting === s.id ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "bg-white border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`} data-testid={`tryon-setting-${s.id}`}>
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>

                {tryOnBusy && (
                  <div className="aspect-[3/4] max-w-sm mx-auto rounded-xl bg-[var(--gs-surface-2)] grid place-items-center">
                    <div className="text-center">
                      <RefreshCw className="h-8 w-8 mx-auto animate-spin text-[var(--gs-teal)] mb-2"/>
                      <p className="text-sm text-[var(--gs-muted)]">Mirror AI is creating your look…</p>
                      <p className="text-xs text-[var(--gs-muted)] mt-1">Usually 10–20 seconds</p>
                    </div>
                  </div>
                )}

                {tryOnResult && !tryOnBusy && (
                  <div>
                    <img src={resolveUrl(tryOnResult.url)} alt={`Mirror AI: ${p.name}`} className="w-full max-w-sm mx-auto rounded-xl border" style={{ borderColor: "var(--gs-border)" }}/>
                    <a href={resolveUrl(tryOnResult.url)} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-xs text-[var(--gs-teal)]"><Download className="h-3 w-3"/>Download image</a>
                  </div>
                )}

                <Button onClick={runTryOn} disabled={tryOnBusy} className="w-full h-11 gap-2 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="mirror-ai-generate-button">
                  {tryOnBusy ? <RefreshCw className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
                  {tryOnResult ? "Try another look" : "Generate Mirror AI"}
                </Button>
                <p className="text-[10px] text-center text-[var(--gs-muted)]">{tryOnCost != null ? `Costs ${tryOnCost} credits per try-on.` : "Uses AI credits from your balance."} <Link to="/pricing" className="underline text-[var(--gs-teal)]">Top up</Link></p>
              </div>
            </DialogContent>
          </Dialog>
        )}

        <div className="grid grid-cols-3 gap-3 text-xs text-[var(--gs-muted)]">
          <div className="flex items-center gap-2"><Truck className="h-4 w-4 text-[var(--gs-teal)]"/>Free shipping over ₹999</div>
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[var(--gs-teal)]"/>Secure checkout</div>
          <div className="flex items-center gap-2"><RotateCcw className="h-4 w-4 text-[var(--gs-teal)]"/>7-day returns</div>
        </div>
      </div>
    </div>
  );
}
