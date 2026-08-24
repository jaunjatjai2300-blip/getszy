/**
 * BeautyWorld — "Soft Beauty / Ritual".
 *
 * Composition idea, distinct from the other worlds: beauty is bought as a
 * ROUTINE, not as isolated objects. So products are presented as an ordered
 * ritual — numbered steps flowing left to right — instead of Fashion's
 * asymmetric editorial or Jewellery's solitary vertical bands.
 *
 * Texture and macro imagery carry the page; glass is soft and low-contrast so
 * it reads as atmosphere rather than as panels.
 */
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import { tierAllows } from "@/commerce/productModel";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem } from "@/experience/primitives";
import { imageProps } from "@/commerce/responsiveImage";

function RitualStep({ product, index, total }) {
  const addToBag = useCartAction();
  const img = product.assets.primary;

  return (
    <RevealItem className="relative flex-1">
      {/* The connective thread that makes a set of products read as a sequence. */}
      {index < total - 1 && (
        <div
          className="absolute right-0 top-[86px] hidden h-px w-1/2 translate-x-1/2 md:block"
          style={{ background: `linear-gradient(90deg, var(--w-accent), transparent)` }}
          aria-hidden="true"
        />
      )}
      <div className="flex flex-col items-center text-center">
        <span
          className="grid h-9 w-9 place-items-center rounded-full text-xs font-semibold"
          style={{ background: "var(--w-accent)", color: "#fff" }}
        >
          {index + 1}
        </span>
        <Link to={`/product/${product.id}`} className="group mt-7 block w-full" data-testid={`beauty-step-${product.id}`}>
          <div className="relative mx-auto aspect-square w-full max-w-[260px] overflow-hidden rounded-full">
            {img ? (
              <img
                {...imageProps(img, "showcase")}
                alt={product.name}
                loading={index === 0 ? "eager" : "lazy"}
                className="h-full w-full object-cover transition-transform duration-[1100ms] ease-out group-hover:scale-[1.06]"
              />
            ) : (
              <div className="grid h-full w-full place-items-center px-6" style={{ background: "var(--w-champagne)" }}>
                <span className="font-display text-lg" style={{ color: "var(--w-deep)" }}>{product.name}</span>
              </div>
            )}
          </div>
          <h3 className="font-display mt-6 text-xl" style={{ color: "var(--w-ink)" }}>{product.name}</h3>
          <p className="mt-2 text-sm" style={{ color: "var(--w-muted)" }}>{fmtINR(product.price)}</p>
        </Link>
        <div className="mt-5">
          <AddToBag product={product} onAdd={addToBag(product)} testId={`beauty-add-${product.id}`} />
        </div>
      </div>
    </RevealItem>
  );
}

export default function BeautyWorld({ catalog, config }) {
  const { products, category, tier } = catalog;

  return (
    <WorldShell config={config}>
      <section className="relative overflow-hidden" data-testid="beauty-hero">
        <div className="gs-container py-20 text-center sm:py-28">
          <motion.span
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9 }}
            className="gs-glass-2 inline-flex items-center gap-2 !rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em]"
            style={{ color: "var(--w-accent)" }}
          >
            <Sparkles className="h-3.5 w-3.5" />
            {category ? category.name : "Beauty"}
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mx-auto mt-7 max-w-3xl gs-display"
            style={{ color: "var(--w-ink)" }}
          >
            A routine that feels like a pause.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.1, delay: 0.35 }}
            className="mx-auto mt-6 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Honest formulas and small rituals — the ten minutes of the day that belong only to you."}
          </motion.p>
        </div>
      </section>

      {/* The ritual. Renders however many real products exist — no padding,
          no repetition, no invented steps. */}
      {products.length > 0 && (
        <Reveal className="gs-container pb-8" data-testid="beauty-ritual">
          <div className="flex flex-col gap-16 md:flex-row md:items-start md:gap-8">
            {products.map((p, i) => (
              <RitualStep key={p.id} product={p} index={i} total={products.length} />
            ))}
          </div>
        </Reveal>
      )}

      <Reveal className="gs-container gs-section" data-testid="beauty-story">
        <div className="gs-glass-2 mx-auto max-w-3xl p-10 text-center sm:p-14">
          <RevealItem>
            <h2 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--w-ink)" }}>
              Nothing here promises a different face.
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}>
              We list what is in the bottle and what it is for. If a claim cannot be
              backed, we leave it out.
            </p>
          </RevealItem>
        </div>
      </Reveal>

      <section className="gs-container pb-24 text-center" data-testid="beauty-cta">
        <Link
          to="/shop"
          className="inline-flex min-h-[44px] items-center gap-2 rounded-full px-8 text-sm font-semibold text-white transition-colors"
          style={{ background: "var(--w-accent)" }}
        >
          Explore all beauty <ArrowRight className="h-4 w-4" />
        </Link>
        {tierAllows.collections(tier) && (
          <p className="mt-5 text-sm" style={{ color: "var(--w-muted)" }}>{products.length} products</p>
        )}
      </section>
    </WorldShell>
  );
}
