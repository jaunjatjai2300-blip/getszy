/**
 * Responsive image sourcing.
 *
 * Every product image in the catalog is currently pinned at w=800, while the
 * worlds ask for full-bleed heroes and large vitrines — so large slots render a
 * source 2-4x smaller than the space they fill, which is the single biggest
 * reason the pages read soft.
 *
 * This does NOT invent imagery. It requests the SAME real photograph at widths
 * appropriate to the slot, using the source CDN's own resize parameter.
 *
 * Safety rule: only URLs we can positively identify as resizable are rewritten.
 * Anything else (a future CDN, a self-hosted file) is returned untouched with no
 * srcset, so we can never emit a URL that 404s.
 */

/** Widths offered per slot shape. Ordered ascending; the browser picks. */
export const WIDTH_SETS = {
  // Small grid cards: 2-up on mobile, 3-4 up on desktop.
  card: [320, 480, 640, 800],
  // Square/portrait product crops shown large (vitrines, ritual steps).
  showcase: [480, 720, 960, 1280],
  // Half-viewport or full-bleed editorial imagery.
  hero: [640, 960, 1280, 1600, 1920],
};

/**
 * `sizes` must describe the slot's real rendered width, otherwise the browser
 * picks the wrong candidate. These mirror the actual grid rules in each world.
 */
export const SIZES = {
  card: "(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw",
  showcase: "(max-width: 768px) 100vw, 58vw",
  hero: "(max-width: 1024px) 100vw, 50vw",
  full: "100vw",
};

/** True when we know how to ask this host for a different width. */
function resizableWidthParam(url) {
  if (typeof url !== "string" || !url) return null;
  // Unsplash honours ?w= and returns a genuinely resized render of the same photo.
  if (url.includes("images.unsplash.com") && /[?&]w=\d+/.test(url)) return "w";
  return null;
}

/**
 * Build a srcset for an existing image URL.
 * @returns {string|undefined} undefined when the URL is not known-resizable,
 *          so the caller simply omits the attribute.
 */
export function buildSrcSet(url, set = "card") {
  const param = resizableWidthParam(url);
  if (!param) return undefined;
  const widths = WIDTH_SETS[set] || WIDTH_SETS.card;
  try {
    return widths
      .map((w) => `${url.replace(new RegExp(`([?&]${param}=)\\d+`), `$1${w}`)} ${w}w`)
      .join(", ");
  } catch {
    return undefined;
  }
}

/**
 * Everything an <img> needs for one slot. Spread directly onto the element:
 *   <img {...imageProps(url, "hero")} alt={name} />
 *
 * `src` is upgraded to the largest offered width so browsers that ignore srcset
 * (and the current 800px-pinned URLs) still get an adequate source rather than
 * the small default.
 */
export function imageProps(url, set = "card", sizesKey) {
  if (!url) return { src: undefined };
  const param = resizableWidthParam(url);
  const widths = WIDTH_SETS[set] || WIDTH_SETS.card;
  const largest = widths[widths.length - 1];
  const src = param
    ? url.replace(new RegExp(`([?&]${param}=)\\d+`), `$1${largest}`)
    : url;
  return {
    src,
    srcSet: buildSrcSet(url, set),
    sizes: SIZES[sizesKey || set] || SIZES.card,
  };
}
