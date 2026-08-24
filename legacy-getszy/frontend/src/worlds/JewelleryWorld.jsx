/**
 * JewelleryWorld — "Quiet Luxury".
 *
 * Deliberately the opposite of FashionWorld's composition:
 *   Fashion is light, asymmetric, horizontal, photography-filled.
 *   Jewellery is dark, centred, vertical, and mostly empty.
 *
 * Each piece is given a full viewport band to itself with enormous negative
 * space around it. Glass appears as a display-case frame — a vitrine metaphor —
 * rather than as surface decoration. Motion is the slowest in the system:
 * stillness is the luxury signal here.
 */
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import { tierAllows } from "@/commerce/productModel";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem, Tilt } from "@/experience/primitives";

/* A single piece, alone in its own band. */
function Vitrine({ product, index }) {
  const addToBag = useCartAction();
  const img = product.assets.primary;
  const alignRight = index % 2 === 1;

  return (
    <Reveal className="gs-container py-24 sm:py-32" data-testid={`jewellery-vitrine-${product.id}`}>
      <div className={`grid items-center gap-12 md:grid-cols-12 ${alignRight ? "md:[direction:rtl]" : ""}`}>
        <RevealItem className="md:col-span-7 md:[direction:ltr]">
          <Tilt max={1.2}>
            {/* The display case: glass as vitrine, not as chrome. */}
            <div className="gs-glass-2 relative overflow-hidden !rounded-none p-3 sm:p-5">
              <div className="relative aspect-square overflow-hidden">
                {img ? (
                  <img
                    src={img}
                    alt={product.name}
                    loading={index === 0 ? "eager" : "lazy"}
                    className="h-full w-full object-cover transition-transform duration-[1400ms] ease-out hover:scale-[1.03]"
                  />
                ) : (
                  <div className="grid h-full w-full place-items-center" style={{ background: "var(--w-deep)" }}>
                    <span className="font-display text-2xl" style={{ color: "var(--w-champagne)" }}>{product.name}</span>
                  </div>
                )}
              </div>
            </div>
          </Tilt>
        </RevealItem>

        <RevealItem className="md:col-span-4 md:col-start-9 md:[direction:ltr]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em]" style={{ color: "var(--w-accent)" }}>
            {String(index + 1).padStart(2, "0")}
          </p>
          <h2 className="font-display mt-5 text-3xl leading-tight sm:text-4xl" style={{ color: "var(--w-ink)" }}>
            {product.name}
          </h2>
          {product.description && (
            <p className="mt-5 text-base leading-relaxed" style={{ color: "var(--w-muted)" }}>
              {product.description}
            </p>
          )}
          <p className="font-display mt-7 text-2xl" style={{ color: "var(--w-champagne)" }}>{fmtINR(product.price)}</p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <AddToBag product={product} onAdd={addToBag(product)} testId={`jewellery-add-${product.id}`} />
            <Link
              to={`/product/${product.id}`}
              className="text-sm font-semibold underline-offset-4 hover:underline"
              style={{ color: "var(--w-muted)" }}
            >
              View details
            </Link>
          </div>
        </RevealItem>
      </div>
    </Reveal>
  );
}

export default function JewelleryWorld({ catalog, config }) {
  const { products, category, tier } = catalog;
  const lead = products[0];

  return (
    <WorldShell config={config}>
      {/* Hero: one object, centred, with deliberate emptiness around it. */}
      <section className="relative overflow-hidden" data-testid="jewellery-hero">
        <div className="gs-container flex min-h-[78vh] flex-col items-center justify-center py-24 text-center">
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.2 }}
            className="text-[11px] font-semibold uppercase tracking-[0.34em]"
            style={{ color: "var(--w-accent)" }}
          >
            {category ? category.name : "Jewellery"}
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
            className="font-display mt-8 max-w-3xl gs-display"
            style={{ color: "var(--w-ink)" }}
          >
            Kept, not collected.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.4, delay: 0.5 }}
            className="mt-8 max-w-md text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Small things you reach for on the days that matter, and the days that do not."}
          </motion.p>

          {lead && lead.assets.primary && (
            <motion.div
              initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1.8, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
              className="mt-16 w-full max-w-lg"
            >
              <div className="relative aspect-[4/3] overflow-hidden">
                <img src={lead.assets.primary} alt="" className="h-full w-full object-cover" />
              </div>
            </motion.div>
          )}
        </div>
      </section>

      {/* Every piece gets its own band. No grid, at any catalog size, unless the
          catalog is genuinely large enough for browsing to beat contemplation. */}
      {products.map((p, i) => <Vitrine key={p.id} product={p} index={i} />)}

      <section className="gs-container pb-28 pt-8 text-center" data-testid="jewellery-cta">
        <Link
          to="/shop"
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full border px-8 text-sm font-semibold transition-colors"
          style={{ borderColor: "var(--w-accent)", color: "var(--w-champagne)" }}
        >
          See the full edit <ArrowRight className="h-4 w-4" />
        </Link>
        {tierAllows.collections(tier) && (
          <p className="mt-6 text-sm" style={{ color: "var(--w-muted)" }}>
            {products.length} pieces currently available
          </p>
        )}
      </section>
    </WorldShell>
  );
}
