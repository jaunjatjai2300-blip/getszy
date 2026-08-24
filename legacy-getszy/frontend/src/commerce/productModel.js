/**
 * Shared product model — the single normalized shape every visual world consumes.
 *
 * Its main job is ASSET HONESTY. The catalog today carries exactly one image per
 * product, but the design system needs to plan for hero / secondary / lifestyle /
 * video / 3D assets arriving later. So each slot is reported separately and is
 * `null` when the asset genuinely does not exist.
 *
 * Worlds must branch on those nulls and choose an intentional editorial layout.
 * They must NOT repeat `primary` into `secondary` to fill space — a page that
 * shows the same photograph twice reads as broken, not as luxury.
 */

/** Normalize one API product into the shape worlds render. */
export function toProductView(p) {
  if (!p) return null;
  const images = Array.isArray(p.images) ? p.images.filter(Boolean) : [];
  return {
    id: p.id,
    slug: p.slug,
    name: p.name,
    description: p.description || "",
    price: typeof p.price === "number" ? p.price : Number(p.price || 0),
    category: p.category,
    isDigital: !!p.is_digital,
    // Editorial flag from the catalog. Deliberately NOT surfaced as "Bestseller"
    // anywhere — we have no sales data, and inventing one is a fake claim.
    isFeatured: !!p.is_featured,
    inStock: typeof p.stock === "number" ? p.stock > 0 : true,
    assets: {
      primary: images[0] || null,
      secondary: images[1] || null,
      lifestyle: images[2] || null,
      video: p.video_url || null,
      model3d: p.model_3d_url || null,
    },
    assetCount: images.length,
  };
}

export function toProductViews(list) {
  return (Array.isArray(list) ? list : []).map(toProductView).filter(Boolean);
}

/**
 * How rich a category page is allowed to be, derived from real catalog size.
 *
 * Tiers come straight from the product rule: a category holding two products may
 * only tell an editorial story; collections and full discovery unlock as real
 * inventory arrives. This is the mechanism that stops a sparse category from
 * rendering empty "Best Sellers" and "You may also like" shelves.
 */
export function densityTier(count) {
  if (count >= 20) return "full";        // full editorial commerce
  if (count >= 10) return "collections"; // collections + richer grid
  if (count >= 5) return "discovery";    // richer discovery
  return "editorial";                    // 1-4: story-led, no grid padding
}

/** Convenience predicates so worlds read declaratively. */
export const tierAllows = {
  grid: (tier) => tier !== "editorial",
  collections: (tier) => tier === "collections" || tier === "full",
  filters: (tier) => tier === "full" || tier === "collections",
};
