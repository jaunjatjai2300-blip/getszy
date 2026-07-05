import { Link } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fmtINR } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export function ProductCard({ product }) {
  const { user } = useAuth();
  const { add } = useCart();
  const navigate = useNavigate();
  const img = (product.images && product.images[0]) || "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600";

  const onAdd = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) { navigate("/login"); return; }
    try { await add(product.id, 1); toast.success("Added to cart", { description: product.name }); }
    catch { toast.error("Could not add to cart"); }
  };

  return (
    <Link to={`/product/${product.id}`} data-testid={`product-card-${product.id}`} className="group block">
      <div className="gs-card gs-card-hover overflow-hidden">
        <div className="relative aspect-square overflow-hidden" style={{ background: "var(--gs-surface-2)" }}>
          <img src={img} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy"/>
          {product.is_featured && <Badge className="absolute top-3 left-3 bg-white text-[var(--gs-ink)] hover:bg-white">Bestseller</Badge>}
          {product.is_digital && <Badge className="absolute top-3 right-3 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]">Digital</Badge>}
        </div>
        <div className="p-4">
          <div className="text-sm font-semibold truncate">{product.name}</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="font-display text-lg">{fmtINR(product.price)}</span>
            <Button size="sm" onClick={onAdd} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-9" data-testid={`product-card-add-${product.id}`}>
              <ShoppingBag className="h-4 w-4"/>
            </Button>
          </div>
        </div>
      </div>
    </Link>
  );
}
