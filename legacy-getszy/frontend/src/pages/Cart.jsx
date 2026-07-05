import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { Button } from "@/components/ui/button";
import { Minus, Plus, Trash2, ArrowRight, ShoppingBag } from "lucide-react";
import { fmtINR } from "@/lib/api";

export default function Cart() {
  const { user } = useAuth();
  const { cart, update } = useCart();
  const navigate = useNavigate();

  if (!user) return (
    <div className="gs-container py-20 text-center">
      <h1 className="font-display text-3xl mb-3">Sign in to view your cart</h1>
      <Button onClick={() => navigate("/login")} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Login</Button>
    </div>
  );

  if (!cart.items.length) return (
    <div className="gs-container py-20 text-center" data-testid="cart-empty-state">
      <ShoppingBag className="h-12 w-12 mx-auto text-[var(--gs-muted)] mb-3"/>
      <h1 className="font-display text-3xl mb-2">Your cart is empty</h1>
      <p className="text-[var(--gs-muted)] mb-6">Discover beautiful pieces curated for you.</p>
      <Link to="/shop"><Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Shop now <ArrowRight className="h-4 w-4 ml-2"/></Button></Link>
    </div>
  );

  const shipping = cart.total >= 999 ? 0 : 49;
  const grand = cart.total + shipping;

  return (
    <div className="gs-container gs-section grid lg:grid-cols-[1fr_360px] gap-8">
      <div>
        <h1 className="font-display text-3xl mb-6">Your Cart</h1>
        <div className="space-y-3">
          {cart.items.map((it) => (
            <div key={it.product_id} className="gs-card p-4 flex gap-4 items-center" data-testid={`cart-item-${it.product_id}`}>
              <img src={(it.product?.images || [])[0]} alt={it.product?.name} className="h-20 w-20 rounded-xl object-cover" style={{ background: "var(--gs-surface-2)" }}/>
              <div className="flex-1 min-w-0">
                <Link to={`/product/${it.product_id}`} className="font-semibold truncate block hover:underline">{it.product?.name}</Link>
                <div className="text-sm text-[var(--gs-muted)]">{fmtINR(it.product?.price)}</div>
              </div>
              <div className="flex items-center border rounded-xl" style={{ borderColor: "var(--gs-border)" }}>
                <button className="h-9 w-9 grid place-items-center" onClick={() => update(it.product_id, it.quantity - 1)}><Minus className="h-3 w-3"/></button>
                <span className="w-8 text-center text-sm">{it.quantity}</span>
                <button className="h-9 w-9 grid place-items-center" onClick={() => update(it.product_id, it.quantity + 1)}><Plus className="h-3 w-3"/></button>
              </div>
              <button onClick={() => update(it.product_id, 0)} className="text-[var(--gs-muted)] hover:text-[var(--destructive)]" data-testid={`cart-remove-${it.product_id}`}><Trash2 className="h-4 w-4"/></button>
              <div className="w-24 text-right font-semibold hidden sm:block">{fmtINR(it.line_total)}</div>
            </div>
          ))}
        </div>
      </div>
      <aside className="lg:sticky lg:top-24 lg:self-start">
        <div className="gs-card p-6">
          <h2 className="font-semibold mb-4">Order Summary</h2>
          <div className="flex justify-between text-sm py-1"><span className="text-[var(--gs-muted)]">Subtotal</span><span>{fmtINR(cart.total)}</span></div>
          <div className="flex justify-between text-sm py-1"><span className="text-[var(--gs-muted)]">Shipping</span><span>{shipping === 0 ? "Free" : fmtINR(shipping)}</span></div>
          <div className="border-t my-3" style={{ borderColor: "var(--gs-border)" }}/>
          <div className="flex justify-between font-semibold mb-4"><span>Total</span><span>{fmtINR(grand)}</span></div>
          <Button onClick={() => navigate("/checkout")} className="w-full h-12 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="cart-checkout-button">Checkout <ArrowRight className="h-4 w-4 ml-2"/></Button>
          {cart.total < 999 && <p className="text-xs text-[var(--gs-muted)] mt-3 text-center">Add {fmtINR(999 - cart.total)} more for free shipping</p>}
        </div>
      </aside>
    </div>
  );
}
