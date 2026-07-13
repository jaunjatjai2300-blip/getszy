import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ShoppingCart, Package, Boxes, RefreshCw, Loader2, ExternalLink } from "lucide-react";
import { toast } from "sonner";

export default function WooSync() {
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState({ products: false, orders: false, inventory: false });
  const [configured, setConfigured] = useState(true);

  useEffect(() => { loadProducts(); }, []);

  const loadProducts = async () => {
    setLoading(l => ({ ...l, products: true }));
    try {
      const res = await api.get("/extras/woo/products");
      if (res.data.error) {
        setConfigured(false);
        return;
      }
      setProducts(res.data.products || []);
      setConfigured(true);
    } catch { setConfigured(false); }
    finally { setLoading(l => ({ ...l, products: false })); }
  };

  const loadOrders = async () => {
    setLoading(l => ({ ...l, orders: true }));
    try {
      const res = await api.get("/extras/woo/orders");
      setOrders(res.data.orders || []);
    } finally { setLoading(l => ({ ...l, orders: false })); }
  };

  const loadInventory = async () => {
    setLoading(l => ({ ...l, inventory: true }));
    try {
      const res = await api.get("/extras/woo/inventory");
      setInventory(res.data.items || []);
    } finally { setLoading(l => ({ ...l, inventory: false })); }
  };

  if (!configured) {
    return (
      <div className="space-y-6" data-testid="woo-sync-page">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-purple-100 grid place-items-center">
            <ShoppingCart className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-display">WooCommerce Sync</h1>
            <p className="text-xs text-[var(--gs-muted)]">Connect your WooCommerce store</p>
          </div>
        </div>
        <Card className="p-8 text-center space-y-4">
          <ShoppingCart className="h-12 w-12 text-[var(--gs-muted)] mx-auto" />
          <h3 className="font-display text-lg">WooCommerce Not Configured</h3>
          <p className="text-sm text-[var(--gs-muted)] max-w-md mx-auto">
            Set the following environment variables to connect your WooCommerce store:
          </p>
          <pre className="text-xs bg-[var(--gs-surface-2)] p-4 rounded-xl text-left max-w-lg mx-auto">
{`WOO_URL=https://your-store.com
WOO_CONSUMER_KEY=ck_xxx
WOO_CONSUMER_SECRET=cs_xxx`}
          </pre>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="woo-sync-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-purple-100 grid place-items-center">
            <ShoppingCart className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-display">WooCommerce Sync</h1>
            <p className="text-xs text-[var(--gs-muted)]">Products, orders, inventory</p>
          </div>
        </div>
        <Badge className="bg-green-100 text-green-700">Connected</Badge>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <Package className="h-6 w-6 text-[var(--gs-teal)] mx-auto mb-1" />
          <div className="text-2xl font-display">{products.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Products</p>
        </Card>
        <Card className="p-4 text-center">
          <ShoppingCart className="h-6 w-6 text-purple-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{orders.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Orders</p>
        </Card>
        <Card className="p-4 text-center">
          <Boxes className="h-6 w-6 text-amber-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{inventory.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">In Stock</p>
        </Card>
      </div>

      <Tabs defaultValue="products">
        <TabsList>
          <TabsTrigger value="products" onClick={loadProducts}>Products</TabsTrigger>
          <TabsTrigger value="orders" onClick={loadOrders}>Orders</TabsTrigger>
          <TabsTrigger value="inventory" onClick={loadInventory}>Inventory</TabsTrigger>
        </TabsList>

        <TabsContent value="products">
          {loading.products ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : (
            <div className="space-y-2">
              {products.map(p => (
                <Card key={p.id} className="p-3 flex items-center gap-4">
                  {p.images?.[0]?.src && <img src={p.images[0].src} alt="" className="h-12 w-12 rounded-lg object-cover" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{p.name}</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">{p.sku || "No SKU"}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">₹{p.price || "0"}</p>
                    <Badge variant="outline" className="text-[10px]">{p.stock_status}</Badge>
                  </div>
                </Card>
              ))}
              {products.length === 0 && <Card className="p-8 text-center text-[var(--gs-muted)]">No products found</Card>}
            </div>
          )}
        </TabsContent>

        <TabsContent value="orders">
          {loading.orders ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : (
            <div className="space-y-2">
              {orders.map(o => (
                <Card key={o.id} className="p-3 flex items-center gap-4">
                  <ShoppingCart className="h-5 w-5 text-[var(--gs-muted)]" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">Order #{o.number || o.id}</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">{o.billing?.first_name} {o.billing?.last_name} — {o.date_created?.slice(0, 10)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">₹{o.total}</p>
                    <Badge variant="outline" className="text-[10px]">{o.status}</Badge>
                  </div>
                </Card>
              ))}
              {orders.length === 0 && <Card className="p-8 text-center text-[var(--gs-muted)]">No orders found</Card>}
            </div>
          )}
        </TabsContent>

        <TabsContent value="inventory">
          {loading.inventory ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : (
            <div className="space-y-2">
              {inventory.map(item => (
                <Card key={item.id} className="p-3 flex items-center gap-4">
                  <Boxes className="h-5 w-5 text-amber-600" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.name}</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">SKU: {item.id}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{item.stock} units</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">₹{item.price}</p>
                  </div>
                </Card>
              ))}
              {inventory.length === 0 && <Card className="p-8 text-center text-[var(--gs-muted)]">No inventory data</Card>}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
