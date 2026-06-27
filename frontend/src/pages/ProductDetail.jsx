import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShoppingBag, Plus, Minus, Truck, ShieldCheck, RotateCcw } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { toast } from "sonner";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { add } = useCart();
  const [p, setP] = useState(null);
  const [qty, setQty] = useState(1);

  useEffect(() => { api.get(`/products/${id}`).then(({ data }) => setP(data)).catch(() => setP(false)); }, [id]);

  if (p === null) return <div className="gs-container py-20 text-center">Loading…</div>;
  if (!p) return <div className="gs-container py-20 text-center">Product not found</div>;

  const img = (p.images && p.images[0]) || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=800";

  const onAdd = async () => {
    if (!user) { navigate("/login"); return; }
    try { await add(p.id, qty); toast.success(`Added ${qty} × ${p.name} to cart`); }
    catch { toast.error("Failed to add"); }
  };

  return (
    <div className="gs-container gs-section grid md:grid-cols-2 gap-10">
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
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center border rounded-xl" style={{ borderColor: "var(--gs-border)" }}>
            <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="h-11 w-11 grid place-items-center" data-testid="product-detail-qty-minus"><Minus className="h-4 w-4"/></button>
            <span className="w-10 text-center font-medium" data-testid="product-detail-quantity-input">{qty}</span>
            <button onClick={() => setQty((q) => q + 1)} className="h-11 w-11 grid place-items-center" data-testid="product-detail-qty-plus"><Plus className="h-4 w-4"/></button>
          </div>
          <Button onClick={onAdd} className="h-12 px-6 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] flex-1" data-testid="product-detail-add-to-cart-button"><ShoppingBag className="h-4 w-4 mr-2"/>Add to Cart</Button>
        </div>
        <div className="grid grid-cols-3 gap-3 text-xs text-[var(--gs-muted)]">
          <div className="flex items-center gap-2"><Truck className="h-4 w-4 text-[var(--gs-teal)]"/>Free shipping over ₹999</div>
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[var(--gs-teal)]"/>Secure checkout</div>
          <div className="flex items-center gap-2"><RotateCcw className="h-4 w-4 text-[var(--gs-teal)]"/>7-day returns</div>
        </div>
      </div>
    </div>
  );
}
