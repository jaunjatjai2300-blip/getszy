/**
 * NeoOrb — Neo, the Getszy assistant, rendered as a living object rather than
 * a chat avatar.
 *
 * The visual is a stack of translucent layers, not a picture of a face:
 *   halo  -> soft outer light bloom
 *   rings -> three dashed circles turning at different speeds/directions
 *   core  -> a glass sphere with an inner glow and one specular highlight
 *   dust  -> small particles orbiting the core
 *
 * Performance contract (matches AmbientBackground / primitives.jsx):
 *   - transform and opacity ONLY. Nothing here animates backdrop-filter,
 *     width/height, border-radius or box-shadow — those force layout or paint
 *     on every frame. Blur and glow are set once, statically, in index.css.
 *   - prefers-reduced-motion -> no motion at all; the orb still reads its state
 *     through colour and particle placement.
 *   - data-fx="reduced"      -> ambient layers (halo drift, ring spin, orbiting
 *     particles) stop; only the core breath remains.
 *   - self-contained: every layer lives inside `size`, and the root clips, so
 *     the orb can never push page width.
 *
 * No WebGL, no canvas, no new dependencies — CSS + framer-motion + inline SVG.
 */
import { useEffect, useId, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

/* ── State vocabulary ──────────────────────────────────────────────────────
   Each state gets a colour pair and a motion character. Error is warm amber
   on purpose: Neo flags a problem, it does not sound an alarm. */
const PALETTES = {
  // Thinking deliberately keeps the idle colour: the state reads through
  // motion (particles gathering, faster breath), not through a colour change.
  // A warm accent here turned the iris pink, which read as a warning.
  idle: { tint: "#2F7E7A", accent: "#F3E2C7" }, // teal + champagne
  thinking: { tint: "#2F7E7A", accent: "#F3E2C7" },
  success: { tint: "#2F7E7A", accent: "#F3E2C7" },
  error: { tint: "#D8A657", accent: "#F3E2C7" }, // soft amber, never red
};

const LABELS = {
  idle: "Neo, the Getszy assistant, is waiting",
  thinking: "Neo, the Getszy assistant, is thinking",
  success: "Neo, the Getszy assistant, has finished",
  error: "Neo, the Getszy assistant, needs your attention",
};

/* Deterministic orbit seeds — no randomness, so the orb looks identical across
   renders and never re-shuffles when React re-mounts it. */
const PARTICLES = [
  { angle: 0, dir: 1, speed: 1.0, radius: 1.0, dot: 1.0, delay: 0 },
  { angle: 52, dir: -1, speed: 1.32, radius: 0.84, dot: 0.68, delay: 0.35 },
  { angle: 104, dir: 1, speed: 0.82, radius: 1.06, dot: 0.82, delay: 0.7 },
  { angle: 157, dir: 1, speed: 1.14, radius: 0.92, dot: 0.55, delay: 1.05 },
  { angle: 205, dir: -1, speed: 0.94, radius: 1.02, dot: 0.9, delay: 0.2 },
  { angle: 258, dir: 1, speed: 1.44, radius: 0.78, dot: 0.6, delay: 0.85 },
  { angle: 310, dir: -1, speed: 0.88, radius: 0.96, dot: 0.75, delay: 0.5 },
];

/** #rgb / #rrggbb -> rgba(). Anything else is returned untouched. */
function withAlpha(color, alpha) {
  if (typeof color !== "string") return color;
  const hex = color.trim();
  if (!/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(hex)) return hex;
  const full =
    hex.length === 4
      ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
      : hex;
  const n = parseInt(full.slice(1), 16);
  /* eslint-disable no-bitwise */
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  /* eslint-enable no-bitwise */
}

/**
 * Tracks the global performance switch set by lib/experience.js. Observed
 * rather than read once, so toggling the experience level updates live.
 */
function useFxReduced() {
  const [fxReduced, setFxReduced] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    const read = () => setFxReduced(root.getAttribute("data-fx") === "reduced");
    read();
    const observer = new MutationObserver(read);
    observer.observe(root, { attributes: true, attributeFilter: ["data-fx"] });
    return () => observer.disconnect();
  }, []);

  return fxReduced;
}

/** Core breath: the one motion that survives data-fx="reduced". */
function coreMotion(state) {
  switch (state) {
    case "thinking":
      return { scale: [1, 1.03, 1], duration: 1.5, repeat: Infinity, ease: "easeInOut" };
    case "success":
      // One-shot luminous expansion, then it settles back down.
      return {
        scale: [1, 1.17, 0.99, 1.02, 1],
        duration: 1.15,
        repeat: 0,
        ease: [0.22, 1, 0.36, 1],
      };
    case "error":
      return { scale: [1, 1.06, 1], duration: 2.4, repeat: Infinity, ease: "easeInOut" };
    default:
      // Idle: a slow ~4s breath. This is the resting personality.
      return { scale: [1, 1.045, 1], duration: 4, repeat: Infinity, ease: "easeInOut" };
  }
}

/** Halo bloom: opacity + scale only. */
function haloMotion(state) {
  switch (state) {
    case "thinking":
      return { opacity: [0.55, 0.9, 0.55], scale: [1, 1.06, 1], duration: 1.5, repeat: Infinity, ease: "easeInOut" };
    case "success":
      return { opacity: [0.6, 1, 0.66], scale: [1, 1.12, 1], duration: 1.15, repeat: 0, ease: [0.22, 1, 0.36, 1] };
    case "error":
      return { opacity: [0.42, 0.82, 0.42], scale: [1, 1.05, 1], duration: 2.4, repeat: Infinity, ease: "easeInOut" };
    default:
      return { opacity: [0.5, 0.76, 0.5], scale: [1, 1.05, 1], duration: 4, repeat: Infinity, ease: "easeInOut" };
  }
}

/**
 * Particle motion, expressed as a translateY along its own rotated axis.
 * `r` is the resting orbit radius in px; the keyframes push it in (gather) or
 * out (expand) without ever touching a layout property.
 */
function particleMotion(state, r) {
  switch (state) {
    case "thinking":
      // Gather hard toward the centre, then fall back out. Faster, tighter.
      return { y: [-r, -r * 0.24, -r], opacity: [0.5, 1, 0.5], scale: [1, 0.68, 1], duration: 1.5, repeat: Infinity, ease: "easeInOut" };
    case "success":
      return { y: [-r, -r * 1.2, -r], opacity: [0.7, 1, 0.78], scale: [1, 1.35, 1], duration: 1.15, repeat: 0, ease: [0.22, 1, 0.36, 1] };
    case "error":
      return { y: [-r, -r * 1.05, -r], opacity: [0.32, 0.7, 0.32], scale: [1, 1.08, 1], duration: 2.4, repeat: Infinity, ease: "easeInOut" };
    default:
      return { y: [-r, -r * 0.93, -r], opacity: [0.4, 0.82, 0.4], scale: [1, 1.14, 1], duration: 5.2, repeat: Infinity, ease: "easeInOut" };
  }
}

/** Base seconds for one full turn of the orbit, per state. */
const ORBIT_SECONDS = { idle: 26, thinking: 7, success: 18, error: 30 };

export default function NeoOrb({ state = "idle", size = 96, className = "", tint }) {
  // useId returns punctuation (":r0:" / "_r_0_" depending on React version);
  // strip it so the value is a legal SVG id and safe inside url(#...).
  const uid = `neo${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const prefersReduced = useReducedMotion();
  const fxReduced = useFxReduced();

  const safeState = PALETTES[state] ? state : "idle";
  const palette = PALETTES[safeState];
  const tintColor = tint || palette.tint;
  const accentColor = palette.accent;

  // prefers-reduced-motion stops everything. data-fx="reduced" stops the
  // ambient layers (halo, rings, orbiting dust) but keeps the core breath.
  const noMotion = Boolean(prefersReduced);
  const noAmbient = noMotion || fxReduced;

  const px = Number(size) || 96;
  const orbitRadius = px * 0.36; // resting orbit, comfortably inside the box
  const dotBase = Math.max(2, px * 0.045);
  const orbitBase = ORBIT_SECONDS[safeState];

  const core = coreMotion(safeState);
  const halo = haloMotion(safeState);

  // Custom properties consumed by the .gs-neo-* rules in index.css, so the
  // gradients stay in CSS and only the colour travels through JS.
  const vars = {
    width: px,
    height: px,
    "--gs-neo-tint": tintColor,
    "--gs-neo-accent": accentColor,
    "--gs-neo-tint-25": withAlpha(tintColor, 0.25),
    "--gs-neo-tint-45": withAlpha(tintColor, 0.45),
    "--gs-neo-tint-70": withAlpha(tintColor, 0.7),
    "--gs-neo-accent-35": withAlpha(accentColor, 0.35),
    "--gs-neo-accent-60": withAlpha(accentColor, 0.6),
    "--gs-neo-dot": Math.round(dotBase * 100) / 100 + "px",
  };

  const rings = [
    { inset: "6%", r: 46, dash: "44 26", width: 1.1, dur: 1.0, dir: 1, start: 0, opacity: 0.55 },
    { inset: "17%", r: 44, dash: "18 34", width: 1.6, dur: 0.62, dir: -1, start: 40, opacity: 0.7 },
    { inset: "29%", r: 42, dash: "8 20", width: 1.4, dur: 0.44, dir: 1, start: 110, opacity: 0.5 },
  ];

  return (
    <div
      role="img"
      aria-label={LABELS[safeState]}
      data-state={safeState}
      className={["gs-neo", className].filter(Boolean).join(" ")}
      style={vars}
    >
      {/* Outer bloom. Blur lives in CSS and is never animated. */}
      <motion.span
        key={`halo-${safeState}`}
        aria-hidden="true"
        className="gs-neo-halo"
        initial={{ opacity: halo.opacity[0], scale: 1 }}
        animate={noAmbient ? { opacity: halo.opacity[0], scale: 1 } : { opacity: halo.opacity, scale: halo.scale }}
        transition={noAmbient ? { duration: 0 } : { duration: halo.duration, repeat: halo.repeat, ease: halo.ease }}
      />

      {/* Ring stack. Each ring is its own rotating wrapper — rotating a div is
          cheaper and far more predictable than rotating an SVG <g>. */}
      {rings.map((ring, i) => {
        const duration = orbitBase * ring.dur;
        const spin = noAmbient
          ? { style: { inset: ring.inset, transform: `rotate(${ring.start}deg)` } }
          : {
              style: { inset: ring.inset },
              initial: { rotate: ring.start },
              animate: { rotate: ring.start + 360 * ring.dir },
              transition: { duration, repeat: Infinity, ease: "linear" },
            };

        return (
          <motion.span key={`ring-${i}`} aria-hidden="true" className="gs-neo-ring" {...spin}>
            <svg viewBox="0 0 100 100" focusable="false" aria-hidden="true">
              <defs>
                <linearGradient id={`${uid}-ring-${i}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor={tintColor} stopOpacity="0.05" />
                  <stop offset="45%" stopColor={tintColor} stopOpacity="0.95" />
                  <stop offset="100%" stopColor={accentColor} stopOpacity="0.15" />
                </linearGradient>
              </defs>
              <circle
                cx="50"
                cy="50"
                r={ring.r}
                fill="none"
                stroke={`url(#${uid}-ring-${i})`}
                strokeWidth={ring.width}
                strokeLinecap="round"
                strokeDasharray={ring.dash}
                opacity={ring.opacity}
              />
            </svg>
          </motion.span>
        );
      })}

      {/* Orbiting dust. The wrapper spins; the dot slides along that axis, so
          "gather toward centre" is a translate, not a resize. */}
      {PARTICLES.map((p, i) => {
        const r = orbitRadius * p.radius;
        const dust = particleMotion(safeState, r);
        const duration = (orbitBase / p.speed) * 1.0;

        const spin = noAmbient
          ? { style: { transform: `rotate(${p.angle}deg)` } }
          : {
              initial: { rotate: p.angle },
              animate: { rotate: p.angle + 360 * p.dir },
              transition: { duration, repeat: Infinity, ease: "linear" },
            };

        // When motion is off the dots still communicate state: thinking pulls
        // them in, success pushes them out, so a still frame is readable.
        const restY = noAmbient ? -r * (safeState === "thinking" ? 0.34 : safeState === "success" ? 1.12 : 1) : -r;

        return (
          <motion.span key={`orbit-${safeState}-${i}`} aria-hidden="true" className="gs-neo-orbit" {...spin}>
            <motion.span
              className="gs-neo-particle"
              /* Centred with margins, not transform: framer owns `transform`
                 on this element and would overwrite a translate(-50%, -50%). */
              style={{
                width: dotBase * p.dot * 1.6,
                height: dotBase * p.dot * 1.6,
                marginLeft: (-dotBase * p.dot * 1.6) / 2,
                marginTop: (-dotBase * p.dot * 1.6) / 2,
              }}
              initial={{ y: restY, opacity: dust.opacity[0], scale: 1 }}
              animate={
                noAmbient
                  ? { y: restY, opacity: dust.opacity[1], scale: 1 }
                  : { y: dust.y, opacity: dust.opacity, scale: dust.scale }
              }
              transition={
                noAmbient
                  ? { duration: 0 }
                  : { duration: dust.duration, repeat: dust.repeat, ease: dust.ease, delay: p.delay }
              }
            />
          </motion.span>
        );
      })}

      {/* The core: glass sphere + inner glow + one specular highlight. */}
      <motion.span
        key={`core-${safeState}`}
        aria-hidden="true"
        className="gs-neo-core"
        initial={{ scale: 1 }}
        animate={noMotion ? { scale: 1 } : { scale: core.scale }}
        transition={noMotion ? { duration: 0 } : { duration: core.duration, repeat: core.repeat, ease: core.ease }}
      >
        <span className="gs-neo-sheen" aria-hidden="true" />
        <span className="gs-neo-rim" aria-hidden="true" />
      </motion.span>

      {/* Iris — a small bright centre so the orb has a focal point. */}
      <motion.span
        key={`iris-${safeState}`}
        aria-hidden="true"
        className="gs-neo-iris"
        initial={{ scale: 1, opacity: 0.85 }}
        animate={
          noMotion
            ? { scale: 1, opacity: 0.85 }
            : safeState === "thinking"
              ? { scale: [1, 1.28, 1], opacity: [0.8, 1, 0.8] }
              : safeState === "success"
                ? { scale: [1, 1.5, 1], opacity: [0.85, 1, 0.9] }
                : { scale: [1, 1.1, 1], opacity: [0.75, 0.95, 0.75] }
        }
        transition={
          noMotion
            ? { duration: 0 }
            : {
                duration: core.duration,
                repeat: safeState === "success" ? 0 : Infinity,
                ease: "easeInOut",
              }
        }
      />
    </div>
  );
}
