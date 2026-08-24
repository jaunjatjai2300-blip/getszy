/**
 * AmbientBackground — the "living" layer behind a visual world.
 *
 * One component, per-world character. A world passes its palette and a mood;
 * the drifting light and soft blobs take their colour from that, so Fashion and
 * DigitalWorld feel like different environments without duplicating any code.
 *
 * Performance contract:
 *   - transform/opacity animation only (compositor thread)
 *   - purely decorative: aria-hidden, pointer-events none
 *   - disabled entirely under prefers-reduced-motion and data-fx="reduced"
 *     (see the guardrail rules in index.css)
 *   - never applies backdrop-filter; it sits BEHIND glass, it is not glass
 */

const MOODS = {
  // Warm, slow, editorial. Physical commerce.
  editorial: { blobs: 2, opacity: 0.55, speed: 34 },
  // Cinematic and still — jewellery wants stillness, not movement.
  cinematic: { blobs: 1, opacity: 0.4, speed: 46 },
  // Soft flowing gradients for beauty.
  liquid: { blobs: 3, opacity: 0.5, speed: 28 },
  // Gentle ambience for lifestyle/home.
  ambient: { blobs: 2, opacity: 0.45, speed: 38 },
  // Controlled, technical, minimal drift.
  precise: { blobs: 1, opacity: 0.3, speed: 42 },
  // Playful float, still restrained.
  playful: { blobs: 3, opacity: 0.55, speed: 24 },
  // Luminous, futuristic. Digital products.
  interface: { blobs: 3, opacity: 0.5, speed: 30 },
  calm: { blobs: 1, opacity: 0.35, speed: 40 },
};

export default function AmbientBackground({ palette, mood = "calm", className = "" }) {
  const cfg = MOODS[mood] || MOODS.calm;
  const tints = [palette.champagne, palette.accent, palette.deep];

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      {Array.from({ length: cfg.blobs }).map((_, i) => (
        <div
          key={i}
          className="gs-ambient-blob"
          style={{
            background: `radial-gradient(closest-side, ${tints[i % tints.length]}, transparent 72%)`,
            opacity: cfg.opacity,
            animationDuration: `${cfg.speed + i * 6}s`,
            animationDelay: `${i * -7}s`,
            // Spread the blobs so they do not stack in one corner.
            left: `${[8, 62, 34][i % 3]}%`,
            top: `${[10, 44, 68][i % 3]}%`,
            width: `${[52, 44, 38][i % 3]}%`,
            height: `${[52, 44, 38][i % 3]}%`,
          }}
        />
      ))}
    </div>
  );
}
