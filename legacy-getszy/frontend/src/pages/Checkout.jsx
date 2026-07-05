import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";

export default function Checkout() {
  const { user } = useAuth();
  const { cart, refresh } = useCart();
  const navigate = useNavigate();
  const [address, setAddress] = useState({ full_name: user?.name || "", phone: user?.phone || "", line1: "", line2: "", city: "", state: "", pincode: "", country: "India" });
  const [notes, setNotes] = useState("");
  const [placed, setPlaced] = useState(null);
  const [busy, setBusy] = useState(false);

  if (!user) { navigate("/login"); return null; }
  if (placed) return (
    <div className="gs-container py-20 text-center max-w-lg mx-auto" data-testid="checkout-success-screen">
      <CheckCircle2 className="h-14 w-14 mx-auto text-[var(--gs-teal)] mb-4"/>
      <h1 className="font-display text-3xl mb-2">Order placed!</h1>
      <p className="text-[var(--gs-muted)] mb-4">Order number: <span className="font-semibold text-[var(--gs-ink)]">{placed.order_number}</span></p>
      <p className="text-sm text-[var(--gs-muted)] mb-6">Payment integration coming soon. Currently using Cash on Delivery for testing.</p>
      <Button onClick={() => navigate("/account")} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">View my orders</Button>
    </div>
  );

  const placeOrder = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/orders/checkout", { address, notes });
      setPlaced(data);
      await refresh();
      toast.success("Order placed successfully!");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to place order");
    } finally { setBusy(false); }
  };

  const shipping = cart.total >= 999 ? 0 : 49;

  return (
    <form onSubmit={placeOrder} className="gs-container gs-section grid lg:grid-cols-[1fr_360px] gap-8">
      <div>
        <h1 className="font-display text-3xl mb-6">Checkout</h1>
        <div className="gs-card p-6 space-y-4">
          <h2 className="font-semibold">Shipping details</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <Input required value={address.full_name} onChange={(e) => setAddress({ ...address, full_name: e.target.value })} placeholder="Full name" data-testid="checkout-name-input"/>
            <Input required value={address.phone} onChange={(e) => setAddress({ ...address, phone: e.target.value })} placeholder="Phone" data-testid="checkout-phone-input"/>
          </div>
          <Input required value={address.line1} onChange={(e) => setAddress({ ...address, line1: e.target.value })} placeholder="Address line 1" data-testid="checkout-line1-input"/>
          <Input value={address.line2} onChange={(e) => setAddress({ ...address, line2: e.target.value })} placeholder="Address line 2 (optional)"/>
          <div className="grid sm:grid-cols-3 gap-3">
            <Input required value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} placeholder="City" data-testid="checkout-city-input"/>
            <Input required value={address.state} onChange={(e) => setAddress({ ...address, state: e.target.value })} placeholder="State"/>
            <Input required value={address.pincode} onChange={(e) => setAddress({ ...address, pincode: e.target.value })} placeholder="Pincode" data-testid="checkout-pincode-input"/>
          </div>
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Order notes (optional)"/>
        </div>
        <div className="gs-card p-6 mt-4">
          <h2 className="font-semibold mb-2">Payment</h2>
          <div className="text-sm text-[var(--gs-muted)]">Cash on Delivery (Razorpay integration coming soon)</div>
        </div>
      </div>
      <aside>
        <div className="gs-card p-6 lg:sticky lg:top-24">
          <h2 className="font-semibold mb-4">Summary</h2>
          <div className="space-y-2 mb-3 max-h-60 overflow-auto">
            {cart.items.map((it) => (
              <div key={it.product_id} className="flex items-center gap-3 text-sm">
                <img src={(it.product?.images || [])[0]} alt="" className="h-12 w-12 rounded-lg object-cover"/>
                <div className="flex-1 truncate">{it.product?.name} ×{it.quantity}</div>
                <div>{fmtINR(it.line_total)}</div>
              </div>
            ))}
          </div>
          <div className="border-t pt-3 space-y-1 text-sm" style={{ borderColor: "var(--gs-border)" }}>
            <div className="flex justify-between"><span className="text-[var(--gs-muted)]">Subtotal</span><span>{fmtINR(cart.total)}</span></div>
            <div className="flex justify-between"><span className="text-[var(--gs-muted)]">Shipping</span><span>{shipping === 0 ? "Free" : fmtINR(shipping)}</span></div>
            <div className="flex justify-between font-semibold mt-2"><span>Total</span><span>{fmtINR(cart.total + shipping)}</span></div>
          </div>
          <Button type="submit" disabled={busy || !cart.items.length} className="w-full mt-4 h-12 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="checkout-place-order-button">{busy ? "Placing…" : "Place Order"}</Button>
        </div>
      </aside>
    </form>
  );
}
