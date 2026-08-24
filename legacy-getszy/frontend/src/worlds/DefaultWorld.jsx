/**
 * DefaultWorld — the honest fallback.
 *
 * Rendered for the all-products shop, for search results, and for any category
 * whose bespoke world is configured but not yet built. It intentionally matches
 * the previous Shop.jsx presentation so unimplemented categories do not regress
 * while their worlds are being designed one at a time.
 */
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ProductCard } from "@/components/ProductCard";
import { SORTS } from "@/commerce/useCatalog";

export default function DefaultWorld({ catalog, search }) {
  const { products, category, loading, error, isEmpty, count, sort, setSort } = catalog;

  const title = category ? category.name : search ? `Results for "${search}"` : "All Products";

  return (
    <div className="gs-container gs-section">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl">{title}</h1>
          {!loading && !error && <p className="mt-1 text-sm text-[var(--gs-muted)]">{count} items</p>}
        </div>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="w-44" data-testid="shop-sort-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(SORTS).map(([key, s]) => (
              <SelectItem key={key} value={key}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="aspect-[3/4] animate-pulse rounded-2xl" style={{ background: "var(--gs-surface-2)" }} />
          ))}
        </div>
      ) : error ? (
        <div className="py-20 text-center text-[var(--gs-muted)]">Couldn't load products. Please refresh the page.</div>
      ) : isEmpty ? (
        <div className="py-20 text-center text-[var(--gs-muted)]">No products found.</div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4" data-testid="shop-product-grid">
          {products.map((p) => (
            <ProductCard key={p.id} product={{ ...p, images: [p.assets.primary].filter(Boolean), is_featured: p.isFeatured, is_digital: p.isDigital }} />
          ))}
        </div>
      )}
    </div>
  );
}
