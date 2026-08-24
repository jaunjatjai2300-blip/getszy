/**
 * FashionWorld — "Luxury Fashion Editorial".
 *
 * Reference implementation for the visual-world architecture. It owns ONLY
 * visual composition; every product, price and cart action comes from the
 * shared commerce engine (src/commerce/) and is identical in every other world.
 *
 * Composition rules specific to Fashion:
 *   - photography dominates; glass is used sparingly (one chip, one CTA surface)
 *   - no generic marketplace grid at low catalog size
 *   - motion is editorial: slow reveals and a gentle hero parallax, nothing showy
 *
 * Honesty rules enforced here:
 *   - sections appear only when real data supports them (see `tier`)
 *   - a product is never repeated to fill a slot
 *   - no invented bestseller / rating / review / recommendation content
 */
import { useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import { fmtINR } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { tierAllows } from "@/commerce/productModel";
import WorldShell from "./WorldShell";
import { imageProps } from "@/commerce/responsiveImage";

const reveal = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] } },
};
const stagger = { visible: { transition: { staggerChildren: 0.12 } } };

/* ── Editorial product card — magazine-like, image-led ────────────────────── */
function EditorialCard({ product, priority = false, ratio = "aspect-[3/4]" }) {
  const { user } = useAuth();
  const { add } = useCart();
  const navigate = useNavigate();
  const img = product.assets.primary;

  const onAdd = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) { navigate("/login"); return; }
    try { await add(product.id, 1); toast.success("Added to bag", { description: product.name }); }
    catch { toast.error("Could not add to bag"); }
  };

  return (
    <Link to={`/product/${product.id}`} className="group block" data-testid={`fashion-card-${product.id}`}>
      <div className={`relative overflow-hidden ${ratio}`} style={{ background: "var(--w-champagne)" }}>
        {img ? (
          <img
            {...imageProps(img, "showcase")}
            alt={product.name}
            loading={priority ? "eager" : "lazy"}
            className="h-full w-full object-cover transition-transform duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-[1.04]"
          />
        ) : (
          /* No photograph yet. An intentional typographic plate reads as editorial
             restraint; a repeated stock image would read as broken. */
          <div className="flex h-full w-full items-end p-6">
            <span className="font-display text-2xl" style={{ color: "var(--w-deep)" }}>{product.name}</span>
          </div>
        )}
      </div>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-display text-lg leading-snug" style={{ color: "var(--w-ink)" }}>{product.name}</h3>
          <p className="mt-1 text-sm" style={{ color: "var(--w-muted)" }}>{fmtINR(product.price)}</p>
        </div>
        {/* L3 solid: a conversion control is never glass and never blurred. */}
        <button
          onClick={onAdd}
          aria-label={`Add ${product.name} to bag`}
          data-testid={`fashion-add-${product.id}`}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-white transition-colors"
          style={{ background: "var(--w-accent)" }}
        >
          <ShoppingBag className="h-4 w-4" />
        </button>
      </div>
    </Link>
  );
}

/* ── Hero ─────────────────────────────────────────────────────────────────── */
function EditorialHero({ category, lead }) {
  const ref = useRef(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  // Gentle parallax only. Transform-only so it stays on the compositor thread.
  const y = useTransform(scrollYProgress, [0, 1], ["0%", reduced ? "0%" : "12%"]);

  const img = lead && lead.assets ? lead.assets.primary : null;

  return (
    <section ref={ref} className="relative overflow-hidden" data-testid="fashion-hero">
      <div className="grid items-stretch gap-0 lg:grid-cols-12">
        <div className="flex items-center px-6 py-16 sm:px-10 lg:col-span-6 lg:px-16 lg:py-28">
          <motion.div initial="hidden" animate="visible" variants={stagger}>
            {/* The single piece of glass in this hero — Fashion is photography-led. */}
            <motion.span
              variants={reveal}
              className="gs-glass-2 inline-flex items-center gap-2 !rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em]"
              style={{ color: "var(--w-accent)" }}
            >
              {category ? category.name : "Fashion"}
            </motion.span>
            <motion.h1
              variants={reveal}
              className="font-display mt-6 gs-display"
              style={{ color: "var(--w-ink)" }}
            >
              Dress the life
              <br />
              you are building.
            </motion.h1>
            <motion.p variants={reveal} className="mt-6 max-w-md text-lg" style={{ color: "var(--w-muted)" }}>
              {category && category.description
                ? category.description
                : "Pieces chosen for how they live on you — considered cuts, honest fabric, and nothing that shouts."}
            </motion.p>
          </motion.div>
        </div>

        <div
          className="relative min-h-[380px] overflow-hidden lg:col-span-6 lg:min-h-[640px]"
          style={{ background: "var(--w-champagne)" }}
        >
          {img && (
            <motion.img {...imageProps(img, "hero")} alt="" style={{ y }} className="absolute inset-0 h-[112%] w-full object-cover" />
          )}
        </div>
      </div>
    </section>
  );
}

/* ── Asymmetric pair — the composition that replaces a grid at low volume ─── */
function AsymmetricPair({ products }) {
  if (products.length < 2) return null;
  const a = products[0];
  const b = products[1];
  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      variants={stagger}
      className="gs-container gs-section"
      data-testid="fashion-asymmetric"
    >
      <div className="grid gap-8 sm:gap-12 md:grid-cols-12 md:items-end">
        <motion.div variants={reveal} className="md:col-span-7">
          <EditorialCard product={a} priority ratio="aspect-[4/5]" />
        </motion.div>
        <motion.div variants={reveal} className="md:col-span-5 md:pb-16">
          <EditorialCard product={b} ratio="aspect-[3/4]" />
        </motion.div>
      </div>
    </motion.section>
  );
}

/* ── Category story — carries the page when the catalog is small ─────────── */
function CategoryStory() {
  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      variants={stagger}
      className="gs-container gs-section !pt-0"
      data-testid="fashion-story"
    >
      <div className="grid gap-10 md:grid-cols-12">
        <motion.div variants={reveal} className="md:col-span-5">
          <h2 className="font-display text-3xl sm:text-4xl" style={{ color: "var(--w-ink)" }}>
            Fewer things, chosen well.
          </h2>
        </motion.div>
        <motion.div
          variants={reveal}
          className="space-y-5 text-lg md:col-span-6 md:col-start-7"
          style={{ color: "var(--w-muted)" }}
        >
          <p>Every piece here is bought the way you would buy for yourself — held, checked, and kept only if it earns its place.</p>
          <p>We would rather show you two pieces worth owning than fifty you will scroll past.</p>
        </motion.div>
      </div>
    </motion.section>
  );
}

/* ── Grid — unlocks only when real inventory justifies it ────────────────── */
function EditorialGrid({ products }) {
  if (!products.length) return null;
  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      variants={stagger}
      className="gs-container gs-section !pt-0"
      data-testid="fashion-grid"
    >
      <div className="grid grid-cols-2 gap-x-5 gap-y-12 lg:grid-cols-3">
        {products.map((p) => (
          <motion.div key={p.id} variants={reveal}>
            <EditorialCard product={p} />
          </motion.div>
        ))}
      </div>
    </motion.section>
  );
}

/* ── Closing CTA ─────────────────────────────────────────────────────────── */
function ExploreCta() {
  return (
    <section className="gs-container pb-20" data-testid="fashion-cta">
      <div className="gs-glass-1 flex flex-col items-start gap-6 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-12">
        <div>
          <h2 className="font-display text-2xl sm:text-3xl" style={{ color: "var(--w-ink)" }}>
            Looking for something else?
          </h2>
          <p className="mt-2" style={{ color: "var(--w-muted)" }}>
            See everything currently in the Getszy edit.
          </p>
        </div>
        <Link
          to="/shop"
          className="inline-flex shrink-0 items-center gap-2 rounded-full px-7 py-3 text-sm font-semibold text-white transition-colors"
          style={{ background: "var(--w-accent)" }}
        >
          Explore the shop <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

/* ── World ───────────────────────────────────────────────────────────────── */
export default function FashionWorld({ catalog, config }) {
  const { products, category, tier } = catalog;
  const showGrid = tierAllows.grid(tier);
  // At editorial density the pair IS the presentation, so the grid must not
  // repeat those same products underneath it.
  const gridProducts = showGrid ? products.slice(2) : [];

  return (
    <WorldShell config={config}>
      <EditorialHero category={category} lead={products[0]} />
      <AsymmetricPair products={products} />
      <CategoryStory />
      {showGrid && <EditorialGrid products={gridProducts} />}
      <ExploreCta />
    </WorldShell>
  );
}
