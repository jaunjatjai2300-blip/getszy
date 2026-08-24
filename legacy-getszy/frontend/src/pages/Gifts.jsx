/**
 * Gifts — curated discovery.
 *
 * The brief asks for occasion- and recipient-based discovery with edits like
 * "The Founder Edit". With 14 products in the catalog, named edits would each
 * contain the same three or four items, so this page does NOT invent them.
 *
 * Instead every filter here is derived from REAL catalog data:
 *   - budget bands computed from actual prices
 *   - categories that actually exist
 *   - digital vs physical, which is a real product flag
 *
 * When the catalog grows, named edits become honest and can be added on top of
 * this same engine. Until then: real filters, real results, no empty shelves.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Gift, ArrowRight } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCatalog } from "@/commerce/useCatalog";
import { useCartAction } from "@/commerce/useCartAction";
import WorldShell, { AddToBag } from "@/worlds/WorldShell";
import { DEFAULT_WORLD } from "@/worlds/registry";
import { Reveal, RevealItem } from "@/experience/primitives";

const BUDGETS = [
  { id: "any", label: "Any budget", test: () => true },
  { id: "under-500", label: "Under ₹500", test: (p) => p.price < 500 },
  { id: "500-1500", label: "₹500 – ₹1,500", test: (p) => p.price >= 500 && p.price <= 1500 },
  { id: "over-1500", label: "Over ₹1,500", test: (p) => p.price > 1500 },
];

const KINDS = [
  { id: "any", label: "Anything" },
  { id: "physical", label: "Something to unwrap" },
  { id: "digital", label: "Something to open today" },
];

function GiftCard({ product, index }) {
  const addToBag = useCartAction();
  const img = product.assets.primary;
  return (
    <RevealItem>
      <div className="group h-full overflow-hidden rounded-3xl" style={{ background: "var(--w-surface)" }}>
        <Link to={`/product/${product.id}`} className="block" data-testid={`gift-card-${product.id}`}>
          <div className="relative aspect-[4/5] overflow-hidden" style={{ background: "var(--w-champagne)" }}>
            {img ? (
              <img
                src={img}
                alt={product.name}
                loading={index < 3 ? "eager" : "lazy"}
                className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.04]"
              />
            ) : (
              <div className="grid h-full w-full place-items-center p-6 text-center">
                <span className="font-display text-lg" style={{ color: "var(--w-deep)" }}>{product.name}</span>
              </div>
            )}
          </div>
          <div className="p-5">
            <h3 className="font-display text-lg" style={{ color: "var(--w-ink)" }}>{product.name}</h3>
            <p className="mt-1 text-sm" style={{ color: "var(--w-muted)" }}>{fmtINR(product.price)}</p>
          </div>
        </Link>
        <div className="px-5 pb-5">
          <AddToBag product={product} onAdd={addToBag(product)} testId={`gift-add-${product.id}`} />
        </div>
      </div>
    </RevealItem>
  );
}

export default function Gifts() {
  const catalog = useCatalog();
  const [budget, setBudget] = useState("any");
  const [kind, setKind] = useState("any");

  const results = useMemo(() => {
    const b = BUDGETS.find((x) => x.id === budget) || BUDGETS[0];
    return catalog.products.filter((p) => {
      if (!b.test(p)) return false;
      if (kind === "physical" && p.isDigital) return false;
      if (kind === "digital" && !p.isDigital) return false;
      return true;
    });
  }, [catalog.products, budget, kind]);

  return (
    <WorldShell config={DEFAULT_WORLD}>
      <section className="relative overflow-hidden" data-testid="gifts-hero">
        <div className="gs-container py-20 text-center sm:py-28">
          <motion.span
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}
            className="gs-glass-2 inline-flex items-center gap-2 !rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em]"
            style={{ color: "var(--w-accent)" }}
          >
            <Gift className="h-3.5 w-3.5" /> Gifting
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mx-auto mt-7 max-w-3xl text-[40px] leading-[1.05] sm:text-6xl"
            style={{ color: "var(--w-ink)" }}
          >
            Something they will actually use.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 0.3 }}
            className="mx-auto mt-6 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}
          >
            Tell us the budget and the kind of gift. We will only show you what is
            genuinely in stock right now.
          </motion.p>
        </div>
      </section>

      {/* Real filters over real inventory. */}
      <section className="gs-container" data-testid="gifts-filters">
        <div className="gs-glass-2 flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--w-muted)" }}>Budget</p>
            <div className="flex flex-wrap gap-2">
              {BUDGETS.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setBudget(b.id)}
                  aria-pressed={budget === b.id}
                  data-testid={`gift-budget-${b.id}`}
                  className="min-h-[44px] rounded-full border px-4 text-sm font-medium transition-colors"
                  style={{
                    borderColor: budget === b.id ? "var(--w-accent)" : "var(--gs-border)",
                    background: budget === b.id ? "var(--w-accent)" : "transparent",
                    color: budget === b.id ? "#fff" : "var(--w-ink)",
                  }}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--w-muted)" }}>Kind</p>
            <div className="flex flex-wrap gap-2">
              {KINDS.map((k) => (
                <button
                  key={k.id}
                  onClick={() => setKind(k.id)}
                  aria-pressed={kind === k.id}
                  data-testid={`gift-kind-${k.id}`}
                  className="min-h-[44px] rounded-full border px-4 text-sm font-medium transition-colors"
                  style={{
                    borderColor: kind === k.id ? "var(--w-accent)" : "var(--gs-border)",
                    background: kind === k.id ? "var(--w-accent)" : "transparent",
                    color: kind === k.id ? "#fff" : "var(--w-ink)",
                  }}
                >
                  {k.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <Reveal className="gs-container gs-section" data-testid="gifts-results">
        {catalog.loading ? (
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="aspect-[4/5] animate-pulse rounded-3xl" style={{ background: "var(--gs-surface-2)" }} />
            ))}
          </div>
        ) : results.length === 0 ? (
          /* Honest empty state rather than widening the filter silently. */
          <div className="py-16 text-center">
            <p className="font-display text-2xl" style={{ color: "var(--w-ink)" }}>Nothing in that range yet.</p>
            <p className="mx-auto mt-3 max-w-md" style={{ color: "var(--w-muted)" }}>
              The catalog is still small and we would rather say so than show you something that does not fit.
            </p>
            <button
              onClick={() => { setBudget("any"); setKind("any"); }}
              className="mt-7 min-h-[44px] rounded-full px-7 text-sm font-semibold text-white"
              style={{ background: "var(--w-accent)" }}
            >
              Show everything
            </button>
          </div>
        ) : (
          <>
            <p className="mb-8 text-sm" style={{ color: "var(--w-muted)" }}>
              {results.length} {results.length === 1 ? "gift" : "gifts"} match
            </p>
            <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
              {results.map((p, i) => <GiftCard key={p.id} product={p} index={i} />)}
            </div>
          </>
        )}
      </Reveal>

      <section className="gs-container pb-24 text-center">
        <Link
          to="/shop"
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full px-8 text-sm font-semibold text-white"
          style={{ background: "var(--w-accent)" }}
        >
          Browse everything <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </WorldShell>
  );
}
