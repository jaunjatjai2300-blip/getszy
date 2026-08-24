/**
 * KidsWorld — "Playful Premium".
 *
 * The brief is explicit about what this must NOT be: childish, cartoon-heavy or
 * rainbow-coloured. It has two audiences at once — a child who should find it
 * friendly and a parent who must find it trustworthy — so the playfulness lives
 * in SHAPE and MOTION (soft rounding, gentle float) while the palette, spacing
 * and typography stay as considered as the rest of Getszy.
 *
 * Composition idea: offset floating cards on a soft field, rather than a rigid
 * grid. Gentle, never bouncy.
 */
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem } from "@/experience/primitives";

function FloatingCard({ product, index }) {
  const addToBag = useCartAction();
  const reduced = useReducedMotion();
  const img = product.assets.primary;
  // Small vertical offsets so the set reads as floating rather than aligned.
  const offset = [0, 40, 16, 56][index % 4];

  return (
    <RevealItem className="w-full sm:w-[calc(50%-1.25rem)] lg:w-[calc(33.333%-1.5rem)]">
      <motion.div
        style={{ marginTop: offset }}
        animate={reduced ? undefined : { y: [0, -8, 0] }}
        transition={reduced ? undefined : { duration: 6 + index, repeat: Infinity, ease: "easeInOut" }}
      >
        <Link
          to={`/product/${product.id}`}
          className="group block overflow-hidden rounded-[32px]"
          style={{ background: "var(--w-surface)" }}
          data-testid={`kids-card-${product.id}`}
        >
          <div className="relative aspect-[4/5] overflow-hidden" style={{ background: "var(--w-champagne)" }}>
            {img ? (
              <img
                src={img}
                alt={product.name}
                loading={index === 0 ? "eager" : "lazy"}
                className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.05]"
              />
            ) : (
              <div className="grid h-full w-full place-items-center px-6 text-center">
                <span className="font-display text-xl" style={{ color: "var(--w-deep)" }}>{product.name}</span>
              </div>
            )}
          </div>
          <div className="p-6">
            <h3 className="font-display text-xl" style={{ color: "var(--w-ink)" }}>{product.name}</h3>
            <p className="mt-1 text-sm" style={{ color: "var(--w-muted)" }}>{fmtINR(product.price)}</p>
          </div>
        </Link>
        <div className="mt-4 px-2">
          <AddToBag product={product} onAdd={addToBag(product)} testId={`kids-add-${product.id}`} />
        </div>
      </motion.div>
    </RevealItem>
  );
}

export default function KidsWorld({ catalog, config }) {
  const { products, category } = catalog;

  return (
    <WorldShell config={config}>
      <section className="relative overflow-hidden" data-testid="kids-hero">
        <div className="gs-container py-20 text-center sm:py-28">
          <motion.span
            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7 }}
            className="inline-flex items-center rounded-full px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.22em]"
            style={{ background: "var(--w-champagne)", color: "var(--w-deep)" }}
          >
            {category ? category.name : "Kids"}
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mx-auto mt-7 max-w-3xl text-[40px] leading-[1.05] sm:text-6xl"
            style={{ color: "var(--w-ink)" }}
          >
            Things they will actually play with.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.3 }}
            className="mx-auto mt-6 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Chosen the way a parent chooses — safe, sturdy, and worth keeping after the first week."}
          </motion.p>
        </div>
      </section>

      {products.length > 0 && (
        <Reveal className="gs-container pb-10" data-testid="kids-collection">
          <div className="flex flex-wrap justify-center gap-8 lg:gap-10">
            {products.map((p, i) => <FloatingCard key={p.id} product={p} index={i} />)}
          </div>
        </Reveal>
      )}

      <section className="gs-container py-24 text-center" data-testid="kids-cta">
        <div className="mx-auto max-w-2xl rounded-[36px] p-10 sm:p-14" style={{ background: "var(--w-champagne)" }}>
          <h2 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--w-deep)" }}>
            Picked by people who tidy up afterwards.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-lg" style={{ color: "var(--w-muted)" }}>
            Every item here is one we would hand to our own kids.
          </p>
          <Link
            to="/shop"
            className="mt-8 inline-flex min-h-[44px] items-center gap-2 rounded-full px-8 text-sm font-semibold text-white transition-colors"
            style={{ background: "var(--w-accent)" }}
          >
            Explore the shop <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </WorldShell>
  );
}
