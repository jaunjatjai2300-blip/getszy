import { useEffect, useState, useCallback } from "react";
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
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);

  const add = async (product_id, quantity = 1) => {
    await api.post("/cart/add", { product_id, quantity });
    await refresh();
  };
  const update = async (product_id, quantity) => {
    await api.post("/cart/update", { product_id, quantity });
    await refresh();
  };
  const clear = async () => {
    await api.post("/cart/clear");
    await refresh();
  };
  return { cart, loading, add, update, clear, refresh };
}
