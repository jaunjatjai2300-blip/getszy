import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api } from "./api";
import { useAuth } from "./auth";

export function useCart() {
  const { user } = useAuth();
  const [cart, setCart] = useState({ items: [], total: 0, count: 0 });
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) { setCart({ items: [], total: 0, count: 0 }); return; }
    setLoading(true);
    try {
      const { data } = await api.get("/cart");
      setCart(data);
    } catch {
      toast.error("Couldn't load your cart. Please try again.");
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);

  const add = async (product_id, quantity = 1) => {
    try {
      await api.post("/cart/add", { product_id, quantity });
      await refresh();
    } catch {
      toast.error("Couldn't add item to cart. Please try again.");
    }
  };
  const update = async (product_id, quantity) => {
    try {
      await api.post("/cart/update", { product_id, quantity });
      await refresh();
    } catch {
      toast.error("Couldn't update cart. Please try again.");
    }
  };
  const clear = async () => {
    try {
      await api.post("/cart/clear");
      await refresh();
    } catch {
      toast.error("Couldn't clear cart. Please try again.");
    }
  };
  return { cart, loading, add, update, clear, refresh };
}
