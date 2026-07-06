import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { ProductCard } from "@/components/ProductCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Shop() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const search = params.get("search");
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState("featured");
  const [cat, setCat] = useState(null);

  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    const q = {};
    if (slug) q.category = slug;
    if (search) q.search = search;
    const qs = new URLSearchParams(q).toString();
    api.get(`/products${qs ? `?${qs}` : ""}`)
      .then(({ data }) => { setProducts(data); setLoading(false); })
      .catch(() => { setProducts([]); setLoading(false); setError(true); });
    if (slug) api.get("/categories").then(({ data }) => setCat(data.find((c) => c.slug === slug))).catch(() => setCat(null));
    else setCat(null);
  }, [slug, search]);

  const sorted = [...products].sort((a, b) => {
    if (sort === "price-low") return a.price - b.price;
    if (sort === "price-high") return b.price - a.price;
    if (sort === "name") return a.name.localeCompare(b.name);
    return (b.is_featured ? 1 : 0) - (a.is_featured ? 1 : 0);
  });

  return (
    <div className="gs-container gs-section">
      <div className="mb-6 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl">{cat ? cat.name : search ? `Results for "${search}"` : "All Products"}</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{sorted.length} items</p>
        </div>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-44" data-testid="shop-sort-select"><SelectValue/></SelectTrigger>
          <SelectContent>
            <SelectItem value="featured">Featured</SelectItem>
            <SelectItem value="price-low">Price: Low to High</SelectItem>
            <SelectItem value="price-high">Price: High to Low</SelectItem>
            <SelectItem value="name">Name (A-Z)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="aspect-[3/4] rounded-2xl animate-pulse" style={{ background: "var(--gs-surface-2)" }}/>)}</div>
      ) : error ? (
        <div className="text-center py-20 text-[var(--gs-muted)]">Couldn't load products. Please refresh the page.</div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-20 text-[var(--gs-muted)]">No products found.</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-5" data-testid="shop-product-grid">{sorted.map((p) => <ProductCard key={p.id} product={p}/>)}</div>
      )}
    </div>
  );
}
