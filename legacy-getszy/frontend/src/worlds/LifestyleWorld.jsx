/**
 * LifestyleWorld — "Modern Lifestyle Editorial" (home-decor).
 *
 * Composition idea: home objects are bought for a ROOM, not for a shelf. So the
 * page alternates full-bleed in-context bands where the product photograph is
 * the environment and the copy sits over it — rather than Fashion's card pair,
 * Jewellery's isolated vitrines or Beauty's ritual row.
 *
 * Warm, spacious, unhurried. Glass is minimal; the photograph does the work.
 */
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem } from "@/experience/primitives";
import { imageProps } from "@/commerce/responsiveImage";

function ContextBand({ product, index }) {
  const addToBag = useCartAction();
  const img = product.assets.primary;
  const flip = index % 2 === 1;

  return (
    <Reveal className="gs-section !py-0" data-testid={`lifestyle-band-${product.id}`}>
      <div className={`grid items-stretch gap-0 lg:grid-cols-2 ${flip ? "lg:[direction:rtl]" : ""}`}>
        <RevealItem className="relative min-h-[320px] overflow-hidden lg:min-h-[560px] lg:[direction:ltr]">
          {img ? (
            <img
              {...imageProps(img, "hero")}
              alt={product.name}
              loading={index === 0 ? "eager" : "lazy"}
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : (
            <div className="absolute inset-0" style={{ background: "var(--w-champagne)" }} />
          )}
        </RevealItem>

        <RevealItem className="flex items-center px-6 py-16 sm:px-12 lg:px-20 lg:[direction:ltr]">
          <div className="max-w-md">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--w-accent)" }}>
              In your space
            </p>
            <h2 className="font-display mt-5 text-3xl leading-tight sm:text-[42px]" style={{ color: "var(--w-ink)" }}>
              {product.name}
            </h2>
            {product.description && (
              <p className="mt-5 text-lg leading-relaxed" style={{ color: "var(--w-muted)" }}>
                {product.description}
              </p>
            )}
            <p className="font-display mt-7 text-2xl" style={{ color: "var(--w-ink)" }}>{fmtINR(product.price)}</p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <AddToBag product={product} onAdd={addToBag(product)} testId={`lifestyle-add-${product.id}`} />
              <Link
                to={`/product/${product.id}`}
                className="text-sm font-semibold underline-offset-4 hover:underline"
                style={{ color: "var(--w-muted)" }}
              >
                Details
              </Link>
            </div>
          </div>
        </RevealItem>
      </div>
    </Reveal>
  );
}

export default function LifestyleWorld({ catalog, config }) {
  const { products, category } = catalog;

  return (
    <WorldShell config={config}>
      <section className="relative overflow-hidden" data-testid="lifestyle-hero">
        <div className="gs-container py-24 sm:py-32">
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1 }}
            className="text-[11px] font-semibold uppercase tracking-[0.28em]"
            style={{ color: "var(--w-accent)" }}
          >
            {category ? category.name : "Home"}
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mt-6 max-w-4xl gs-display"
            style={{ color: "var(--w-ink)" }}
          >
            The room remembers<br />what you chose.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.1, delay: 0.35 }}
            className="mt-8 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Objects that earn their corner — made to be used, not arranged and forgotten."}
          </motion.p>
        </div>
      </section>

      {products.map((p, i) => <ContextBand key={p.id} product={p} index={i} />)}

      <section className="gs-container py-24 text-center" data-testid="lifestyle-cta">
        <h2 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--w-ink)" }}>
          Building the room slowly?
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-lg" style={{ color: "var(--w-muted)" }}>
          So are we. New pieces are added only when they are worth adding.
        </p>
        <Link
          to="/shop"
          className="mt-9 inline-flex min-h-[44px] items-center gap-2 rounded-full px-8 text-sm font-semibold text-white transition-colors"
          style={{ background: "var(--w-accent)" }}
        >
          Explore the shop <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </WorldShell>
  );
}
