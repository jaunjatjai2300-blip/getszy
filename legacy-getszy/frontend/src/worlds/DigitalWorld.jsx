/**
 * DigitalWorld — "Living Software".
 *
 * The one world where glass is the dominant language and the environment is
 * dark and luminous. Fundamentally different from physical commerce: no
 * editorial photography, no product-in-a-room; instead floating panels, depth,
 * and interface-like surfaces.
 *
 * HONESTY NOTE: the brief asks for "live product demonstrations". The digital
 * catalog today is downloadable goods (an eBook, template packs) — not
 * interactive software — so this world does NOT simulate a fake app UI for
 * them. It presents what each product genuinely is, and points at Getszy's real
 * working tools where those exist. A fabricated demo would be exactly the kind
 * of invented functionality the catalog rule forbids.
 *
 * Conversion controls stay solid (L3) even here, per the glass rules.
 */
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Download, Sparkles } from "lucide-react";
import { fmtINR } from "@/lib/api";
import { useCartAction } from "@/commerce/useCartAction";
import WorldShell, { AddToBag } from "./WorldShell";
import { Reveal, RevealItem, Tilt } from "@/experience/primitives";

function FloatingPanel({ product, index }) {
  const addToBag = useCartAction();
  const reduced = useReducedMotion();
  const img = product.assets.primary;

  return (
    <RevealItem className="w-full lg:w-[calc(50%-1.5rem)]">
      <motion.div
        animate={reduced ? undefined : { y: [0, -10, 0] }}
        transition={reduced ? undefined : { duration: 7 + index * 1.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <Tilt max={1.5}>
          <div className="gs-glass-1 overflow-hidden p-6 sm:p-8" data-testid={`digital-panel-${product.id}`}>
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em]" style={{ color: "var(--w-accent)" }}>
              <Sparkles className="h-3.5 w-3.5" />
              Digital
            </div>

            <div className="relative mt-6 aspect-[16/10] overflow-hidden rounded-xl" style={{ background: "var(--w-deep)" }}>
              {img ? (
                <img src={img} alt={product.name} loading={index === 0 ? "eager" : "lazy"} className="h-full w-full object-cover opacity-90" />
              ) : (
                <div className="grid h-full w-full place-items-center">
                  <span className="font-display text-xl" style={{ color: "var(--w-muted)" }}>{product.name}</span>
                </div>
              )}
            </div>

            <h3 className="font-display mt-7 text-2xl" style={{ color: "var(--w-ink)" }}>{product.name}</h3>
            {product.description && (
              <p className="mt-3 text-base leading-relaxed" style={{ color: "var(--w-muted)" }}>{product.description}</p>
            )}

            <div className="mt-7 flex flex-wrap items-center justify-between gap-4">
              <span className="font-display text-2xl" style={{ color: "var(--w-ink)" }}>{fmtINR(product.price)}</span>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: "var(--w-muted)" }}>
                  <Download className="h-3.5 w-3.5" /> Instant access
                </span>
                <AddToBag product={product} onAdd={addToBag(product)} compact testId={`digital-add-${product.id}`} />
              </div>
            </div>
          </div>
        </Tilt>
      </motion.div>
    </RevealItem>
  );
}

export default function DigitalWorld({ catalog, config }) {
  const { products, category } = catalog;

  return (
    <WorldShell config={config}>
      <section className="relative overflow-hidden" data-testid="digital-hero">
        <div className="gs-container flex min-h-[70vh] flex-col justify-center py-24">
          <motion.span
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9 }}
            className="gs-glass-2 inline-flex w-fit items-center gap-2 !rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em]"
            style={{ color: "var(--w-accent)" }}
          >
            {category ? category.name : "Digital"}
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="font-display mt-8 max-w-4xl text-[42px] leading-[1.02] sm:text-6xl lg:text-[72px]"
            style={{ color: "var(--w-ink)" }}
          >
            Tools that do the<br />work with you.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.1, delay: 0.35 }}
            className="mt-8 max-w-xl text-lg" style={{ color: "var(--w-muted)" }}
          >
            {category && category.description
              ? category.description
              : "Downloadable guides and templates you can open today — and Getszy's live tools when you want the work done with you."}
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.1, delay: 0.55 }}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            {/* Real destination: the build studio genuinely exists behind auth. */}
            <Link
              to="/dashboard/build"
              className="inline-flex min-h-[44px] items-center gap-2 rounded-full px-7 text-sm font-semibold text-white transition-colors"
              style={{ background: "var(--w-accent)", color: "#06231F" }}
            >
              Open the studio <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/pricing"
              className="inline-flex min-h-[44px] items-center gap-2 text-sm font-semibold underline-offset-4 hover:underline"
              style={{ color: "var(--w-muted)" }}
            >
              See what credits cost
            </Link>
          </motion.div>
        </div>
      </section>

      {products.length > 0 && (
        <Reveal className="gs-container pb-16" data-testid="digital-panels">
          <div className="flex flex-wrap gap-8 lg:gap-12">
            {products.map((p, i) => <FloatingPanel key={p.id} product={p} index={i} />)}
          </div>
        </Reveal>
      )}

      <Reveal className="gs-container pb-28" data-testid="digital-cta">
        <div className="gs-glass-1 flex flex-col items-start gap-6 p-10 sm:flex-row sm:items-center sm:justify-between sm:p-14">
          <div>
            <h2 className="font-display text-2xl sm:text-3xl" style={{ color: "var(--w-ink)" }}>
              Rather have it built for you?
            </h2>
            <p className="mt-2" style={{ color: "var(--w-muted)" }}>
              Describe what you need and Neo takes the first pass.
            </p>
          </div>
          <Link
            to="/dashboard"
            className="inline-flex min-h-[44px] shrink-0 items-center gap-2 rounded-full px-7 text-sm font-semibold transition-colors"
            style={{ background: "var(--w-accent)", color: "#06231F" }}
          >
            Talk to Neo <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Reveal>
    </WorldShell>
  );
}
