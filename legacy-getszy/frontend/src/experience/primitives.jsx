/**
 * Shared interaction primitives for the Living Glass World.
 *
 * Built once here, reused by every visual world. Each primitive degrades to a
 * plain element when motion is unwanted or the device is weak:
 *   - prefers-reduced-motion  -> no motion at all
 *   - data-fx="reduced"       -> no motion (set by lib/experience.js)
 *   - coarse pointer (touch)  -> no cursor-driven effects
 *
 * All motion is transform/opacity only. Nothing here animates backdrop-filter.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

/** True when we should run cursor-driven, non-essential motion. */
export function useFancyMotion() {
  const reduced = useReducedMotion();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    if (reduced) { setOk(false); return; }
    const finePointer = window.matchMedia("(pointer: fine)").matches;
    const fxReduced = document.documentElement.getAttribute("data-fx") === "reduced";
    setOk(finePointer && !fxReduced);
  }, [reduced]);

  return ok;
}

/**
 * Magnetic — a control that leans a few pixels toward the cursor.
 * Deliberately capped: the brief calls for 2-5px, not a springy toy.
 */
export function Magnetic({ children, strength = 4, className = "", as: Tag = "div", ...rest }) {
  const ref = useRef(null);
  const enabled = useFancyMotion();
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const onMove = useCallback((e) => {
    if (!enabled || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    setOffset({
      x: Math.max(-1, Math.min(1, dx)) * strength,
      y: Math.max(-1, Math.min(1, dy)) * strength,
    });
  }, [enabled, strength]);

  const reset = useCallback(() => setOffset({ x: 0, y: 0 }), []);

  const MotionTag = motion[Tag] || motion.div;
  return (
    <MotionTag
      ref={ref}
      className={className}
      onMouseMove={onMove}
      onMouseLeave={reset}
      animate={{ x: offset.x, y: offset.y }}
      transition={{ type: "spring", stiffness: 260, damping: 22, mass: 0.4 }}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}

/**
 * Tilt — 1-2 degrees maximum. Any more reads as a gimmick rather than depth.
 * Uses rotate transforms only, so it stays on the compositor thread.
 */
export function Tilt({ children, max = 1.5, className = "", ...rest }) {
  const ref = useRef(null);
  const enabled = useFancyMotion();
  const [t, setT] = useState({ rx: 0, ry: 0 });

  const onMove = useCallback((e) => {
    if (!enabled || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const py = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    setT({ rx: -py * max, ry: px * max });
  }, [enabled, max]);

  const reset = useCallback(() => setT({ rx: 0, ry: 0 }), []);

  return (
    <motion.div
      ref={ref}
      className={className}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ transformPerspective: 1200 }}
      animate={{ rotateX: t.rx, rotateY: t.ry }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** Standard editorial reveal. One vocabulary across every world. */
export const revealVariants = {
  hidden: { opacity: 0, y: 28 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] } },
};
export const staggerVariants = { visible: { transition: { staggerChildren: 0.1 } } };

/** Section wrapper that reveals once on scroll. */
export function Reveal({ children, className = "", as = "section", ...rest }) {
  const MotionTag = motion[as] || motion.section;
  return (
    <MotionTag
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      variants={staggerVariants}
      className={className}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}

/** Child of <Reveal>. */
export function RevealItem({ children, className = "", ...rest }) {
  return (
    <motion.div variants={revealVariants} className={className} {...rest}>
      {children}
    </motion.div>
  );
}
