import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, fmtINR } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Package } from "lucide-react";

const STATUS_COLORS = { pending: "bg-amber-100 text-amber-800", forwarded: "bg-sky-100 text-sky-800", shipped: "bg-blue-100 text-blue-800", delivered: "bg-emerald-100 text-emerald-800", cancelled: "bg-rose-100 text-rose-800" };

export default function Account() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
    if (user) api.get("/orders/mine").then(({ data }) => setOrders(data));
  }, [user, loading, navigate]);

  if (!user) return null;

  return (
    <div className="gs-container gs-section" data-testid="account-page">
      <h1 className="font-display text-3xl mb-6">My Account</h1>
      <Tabs defaultValue="orders" data-testid="account-tabs">
        <TabsList><TabsTrigger value="orders">Orders</TabsTrigger><TabsTrigger value="profile">Profile</TabsTrigger></TabsList>
        <TabsContent value="orders" className="mt-6">
          {orders.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)]"><Package className="h-10 w-10 mx-auto mb-2"/>No orders yet</div>
          ) : (
            <div className="space-y-3">{orders.map((o) => (
              <div key={o.id} className="gs-card p-5 flex flex-wrap items-center gap-4" data-testid={`order-${o.order_number}`}>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold">{o.order_number}</div>
                  <div className="text-xs text-[var(--gs-muted)]">{new Date(o.created_at).toLocaleDateString()} · {o.items.length} item(s)</div>
                  {o.tracking_number && <div className="text-xs mt-1">Tracking: <span className="font-mono">{o.tracking_number}</span></div>}
                </div>
                <Badge className={`${STATUS_COLORS[o.status] || ""} hover:opacity-100 capitalize`}>{o.status}</Badge>
                <div className="font-semibold">{fmtINR(o.total)}</div>
              </div>
            ))}</div>
          )}
        </TabsContent>
        <TabsContent value="profile" className="mt-6">
          <div className="gs-card p-6 max-w-md">
            <div className="text-sm text-[var(--gs-muted)]">Name</div><div className="font-semibold mb-3">{user.name}</div>
            <div className="text-sm text-[var(--gs-muted)]">Email</div><div className="font-semibold mb-3">{user.email}</div>
            <div className="text-sm text-[var(--gs-muted)]">Role</div><div className="font-semibold capitalize">{user.role}</div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
