/**
 * TechLifestyleWorld — "Premium Physical Technology" (gadgets).
 *
 * Explicitly NOT DigitalWorld: these are physical goods that ship in a box, so
 * the photograph stays the hero and there is no simulated software UI.
 * Explicitly NOT a SaaS dashboard either — no charts, no metric tiles.
 *
 * Composition idea: precision. A strict centred axis, tight measured spacing,
 * and quiet technical annotations — the visual grammar of a spec sheet, kept
 * elegant. Motion is small and exact rather than flowing.
 */
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem, Tilt } from "@/experience/primitives";

function TechPiece({ product, index }) {
  const addToBag = useCartAction();
  const img = product.assets.primary;

  return (
    <Reveal className="gs-container py-20 sm:py-28" data-testid={`tech-piece-${product.id}`}>
      <div className="mx-auto max-w-3xl text-center">
        <RevealItem>
          <p className="font-mono text-[11px] uppercase tracking-[0.3em]" style={{ color: "var(--w-accent)" }}>
            {String(index + 1).padStart(2, "0")} / {product.inStock ? "In stock" : "Out of stock"}
          </p>
        </RevealItem>

        <RevealItem className="mt-10">
          <Tilt max={1.5}>
            <div className="relative mx-auto aspect-[4/3] w-full overflow-hidden rounded-2xl" style={{ background: "var(--w-champagne)" }}>
              {img ? (
                <img
                  src={img}
                  alt={product.name}
                  loading={index === 0 ? "eager" : "lazy"}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="grid h-full w-full place-items-center">
                  <span className="font-display text-2xl" style={{ color: "var(--w-deep)" }}>{product.name}</span>
                </div>
              )}
            </div>
          </Tilt>
        </RevealItem>

        <RevealItem>
          <h2 className="font-display mt-12 text-3xl sm:text-[40px]" style={{ color: "var(--w-ink)" }}>
            {product.name}
          </h2>
          {product.description && (
            <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed" style={{ color: "var(--w-muted)" }}>
              {product.description}
            </p>
          )}

          {/* Measured rule + price. The only "spec" values shown are ones the
              catalog actually provides — nothing is invented to fill the row. */}
          <div className="mx-auto mt-10 h-px w-24" style={{ background: "var(--w-accent)" }} />
          <p className="font-display mt-8 text-2xl" style={{ color: "var(--w-ink)" }}>{fmtINR(product.price)}</p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <AddToBag product={product} onAdd={addToBag(product)} testId={`tech-add-${product.id}`} />
            <Link
              to={`/product/${product.id}`}
              className="text-sm font-semibold underline-offset-4 hover:underline"
              style={{ color: "var(--w-muted)" }}
            >
              Full details
            </Link>
          </div>
        </RevealItem>
      </div>
    </Reveal>
  );
}

export default function TechLifestyleWorld({ catalog, config }) {
  const { products, category } = catalog;

  return (
    <WorldShell config={config}>
      <section className="relative overflow-hidden" data-testid="tech-hero">
        <div className="gs-container flex min-h-[62vh] flex-col items-center justify-center py-24 text-center">
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }}
            className="font-mono text-[11px] uppercase tracking-[0.32em]"
            style={{ color: "var(--w-accent)" }}
          >
            {category ? category.name : "Technology"}
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mt-7 max-w-3xl gs-display"
            style={{ color: "var(--w-ink)" }}
          >
            Technology that stays out of the way.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.3 }}
            className="mt-7 max-w-lg text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Chosen for how they behave on an ordinary Tuesday, not for the spec sheet."}
          </motion.p>
        </div>
      </section>

      {products.map((p, i) => <TechPiece key={p.id} product={p} index={i} />)}

      <section className="gs-container pb-24 text-center" data-testid="tech-cta">
        <Link
          to="/shop"
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full px-8 text-sm font-semibold text-white transition-colors"
          style={{ background: "var(--w-accent)" }}
        >
          Explore the shop <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </WorldShell>
  );
}
