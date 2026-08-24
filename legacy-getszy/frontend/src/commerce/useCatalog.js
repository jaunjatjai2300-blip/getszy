/**
 * Shared commerce engine — catalog access for every visual world.
 *
 * Owns: API calls, category resolution, sorting, loading/error/empty state and
 * the density tier. Owns NO visual decisions. A world changes its entire look
 * without touching this file, and this file changes without touching any world.
 */
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { toProductViews, densityTier } from "./productModel";

export const SORTS = {
  featured: { label: "Featured", cmp: (a, b) => (b.isFeatured ? 1 : 0) - (a.isFeatured ? 1 : 0) },
  "price-low": { label: "Price: Low to High", cmp: (a, b) => a.price - b.price },
  "price-high": { label: "Price: High to Low", cmp: (a, b) => b.price - a.price },
  name: { label: "Name (A-Z)", cmp: (a, b) => a.name.localeCompare(b.name) },
};

/**
 * @param {string=} slug     category slug; omit for the all-products shop
 * @param {string=} search   free-text query
 */
export function useCatalog(slug, search) {
  const [raw, setRaw] = useState([]);
  const [category, setCategory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sort, setSort] = useState("featured");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);

    const q = {};
    if (slug) q.category = slug;
    if (search) q.search = search;
    const qs = new URLSearchParams(q).toString();

    api
      .get(`/products${qs ? `?${qs}` : ""}`)
      .then(({ data }) => {
        if (!alive) return;
        setRaw(toProductViews(data));
      })
      .catch(() => {
        if (!alive) return;
        setRaw([]);
        setError(true);
      })
      .finally(() => alive && setLoading(false));

    if (slug) {
      api
        .get("/categories")
        .then(({ data }) => alive && setCategory((data || []).find((c) => c.slug === slug) || null))
        .catch(() => alive && setCategory(null));
    } else {
      setCategory(null);
    }

    return () => { alive = false; };
  }, [slug, search]);

  const products = useMemo(() => {
    const cmp = (SORTS[sort] || SORTS.featured).cmp;
    return [...raw].sort(cmp);
  }, [raw, sort]);

  const featured = useMemo(() => products.filter((p) => p.isFeatured), [products]);

  return {
    products,
    featured,
    category,
    loading,
    error,
    isEmpty: !loading && !error && products.length === 0,
    count: products.length,
    tier: densityTier(products.length),
    sort,
    setSort,
  };
}
