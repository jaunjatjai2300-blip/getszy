/**
 * Shared add-to-bag behaviour. Business logic, so it lives in the commerce
 * engine — every world calls this and none of them re-implement the
 * auth-check / cart-call / toast sequence.
 */
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

export function useCartAction() {
  const { user } = useAuth();
  const { add } = useCart();
  const navigate = useNavigate();

  return useCallback(
    (product) => async (e) => {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      if (!user) { navigate("/login"); return; }
      try {
        await add(product.id, 1);
        toast.success("Added to bag", { description: product.name });
      } catch {
        toast.error("Could not add to bag");
      }
    },
    [user, add, navigate]
  );
}
