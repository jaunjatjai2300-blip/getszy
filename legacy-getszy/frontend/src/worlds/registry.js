/**
 * Category → visual world registry. Single source of truth for the mapping.
 *
 * Every slug here was verified against the LIVE catalog (/api/categories) before
 * being added. Do not add a world for a category that does not exist in
 * production data.
 *
 * Deliberately absent: `accessories`. It is specified in the design brief but is
 * NOT in the live catalog, so exposing it would invent a category. If the
 * business adds it later, add the real category first, then a world here.
 *
 * Worlds own visual composition only. All commerce behaviour lives in
 * `src/commerce/` and is identical across worlds.
 */

export const WORLDS = {
  fashion: {
    id: "fashion",
    world: "FashionWorld",
    identity: "Luxury Fashion Editorial",
    palette: { bg: "#FBF7F2", surface: "#FFFDFB", ink: "#2B2320", muted: "#6B625B",
               accent: "#C58B7A", deep: "#3E2C26", champagne: "#F3E2C7" },
    motion: "editorial",        // slow fabric-like drift, horizontal reveals
    photography: "full-bleed",  // imagery dominates the composition
    cardVariant: "editorial",   // minimal, magazine-like
    glass: "minimal",           // photography over glass
    implemented: true,
  },

  jewellery: {
    id: "jewellery",
    world: "JewelleryWorld",
    identity: "Quiet Luxury",
    palette: { bg: "#14100E", surface: "#1C1714", ink: "#F5EFE8", muted: "#B9AC9E",
               accent: "#C9A96B", deep: "#0B0908", champagne: "#E8D9BE" },
    motion: "cinematic",        // slow rotation, light sweep, macro zoom
    photography: "macro",       // large product photography, heavy negative space
    cardVariant: "displayCase",
    glass: "displayCase",       // glass as a vitrine metaphor, used selectively
    implemented: false,
  },

  beauty: {
    id: "beauty",
    world: "BeautyWorld",
    identity: "Soft Beauty / Ritual",
    palette: { bg: "#FCF8F6", surface: "#FFFFFF", ink: "#2E2529", muted: "#6E6167",
               accent: "#C99BA4", deep: "#5A4148", champagne: "#F6E7DE" },
    motion: "liquid",           // soft flowing gradients, gentle glow
    photography: "texture",     // macro texture matters more than 3D
    cardVariant: "ritual",
    glass: "soft",
    implemented: false,
  },

  "home-decor": {
    id: "home-decor",
    world: "LifestyleWorld",
    identity: "Modern Lifestyle Editorial",
    palette: { bg: "#FAF6F0", surface: "#FFFDFA", ink: "#2A2521", muted: "#6B6259",
               accent: "#B08968", deep: "#4A3F35", champagne: "#EFE1CE" },
    motion: "ambient",          // slow ambient drift, subtle object parallax
    photography: "in-context",  // product-in-context over isolated packshots
    cardVariant: "editorial",
    glass: "minimal",
    implemented: false,
  },

  gadgets: {
    id: "gadgets",
    world: "TechLifestyleWorld",
    identity: "Premium Physical Technology",
    // Explicitly NOT DigitalWorld: these are physical shipped goods. The page
    // must read as premium consumer tech, never as a SaaS dashboard.
    palette: { bg: "#F7F7F8", surface: "#FFFFFF", ink: "#1A1C1F", muted: "#5E636B",
               accent: "#3E7C81", deep: "#24272C", champagne: "#E6EAF0" },
    motion: "precise",          // controlled technical motion, subtle 3D
    photography: "product-hero",
    cardVariant: "technical",
    glass: "restrained",
    implemented: false,
  },

  kids: {
    id: "kids",
    world: "KidsWorld",
    identity: "Playful Premium",
    // Playful, not childish. No rainbow palettes, no cartoon density.
    // Must read as trustworthy to a parent and friendly to a child.
    palette: { bg: "#FFFBF4", surface: "#FFFFFF", ink: "#332B26", muted: "#6F645C",
               accent: "#E8A87C", deep: "#4E4038", champagne: "#FCEBD6" },
    motion: "playful",          // gentle floating, restrained
    photography: "product-hero",
    cardVariant: "rounded",
    glass: "soft",
    implemented: false,
  },

  "digital-products": {
    id: "digital-products",
    world: "DigitalWorld",
    identity: "Living Software",
    // The only world where glass is the dominant language. Conversion actions
    // still stay solid (see the L3 rule in index.css).
    palette: { bg: "#0C0F14", surface: "#141922", ink: "#EAF0F7", muted: "#93A0B4",
               accent: "#4FD1C5", deep: "#070A0E", champagne: "#B8C6DA" },
    motion: "interface",        // floating panels, live UI animation, data motion
    photography: "interface",   // show the actual product experience
    cardVariant: "demo",
    glass: "dominant",
    implemented: false,
  },
};

/** Rendered when a category has no world yet, or is unknown. Never 404s. */
export const DEFAULT_WORLD = {
  id: "default",
  world: "DefaultWorld",
  identity: "Getszy",
  palette: { bg: "#FBF7F2", surface: "#FFFDFB", ink: "#1B1A18", muted: "#5F5951",
             accent: "#C58B7A", deep: "#3E2C26", champagne: "#F3E2C7" },
  motion: "calm",
  photography: "standard",
  cardVariant: "standard",
  glass: "minimal",
  implemented: true,
};

export function worldFor(slug) {
  return WORLDS[slug] || DEFAULT_WORLD;
}

/** Categories that have a bespoke world actually built (not just configured). */
export function implementedWorlds() {
  return Object.values(WORLDS).filter((w) => w.implemented).map((w) => w.id);
}
