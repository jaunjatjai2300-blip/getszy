/**
 * MagneticNav — the liquid pill that glides between navigation items.
 *
 * Wraps an existing <nav>'s children without changing their markup: it measures
 * whichever direct child is hovered and animates a single pill to that child's
 * box, so the highlight SLIDES from Shop to Build rather than jumping.
 *
 * Deliberately self-contained so the header can adopt it with a one-line change
 * and other work can touch Header.jsx without conflicting with this file.
 *
 * Degrades cleanly:
 *   - prefers-reduced-motion / data-fx="reduced" -> pill still appears, but snaps
 *   - touch (coarse pointer)                     -> pill never renders at all
 * Animates transform/opacity only; the pill is aria-hidden decoration.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useFancyMotion } from "./primitives";

export default function MagneticNav({ children, className = "" }) {
  const wrapRef = useRef(null);
  const fancy = useFancyMotion();
  const [pill, setPill] = useState(null);

  const onMove = useCallback((e) => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    // Find the direct child containing the pointer target.
    let node = e.target;
    while (node && node.parentElement !== wrap) node = node.parentElement;
    if (!node) return;
    const w = wrap.getBoundingClientRect();
    const r = node.getBoundingClientRect();
    if (r.width < 8) return;
    setPill({ x: r.left - w.left, width: r.width });
  }, []);

  const clear = useCallback(() => setPill(null), []);

  useEffect(() => { if (!fancy) setPill(null); }, [fancy]);

  return (
    <div ref={wrapRef} className={`relative ${className}`} onMouseMove={onMove} onMouseLeave={clear}>
      {fancy && pill && (
        <motion.span
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 -z-0 rounded-full"
          style={{
            height: 34,
            marginTop: -17,
            background: "var(--gs-surface-2)",
          }}
          initial={{ opacity: 0, x: pill.x, width: pill.width }}
          animate={{ opacity: 1, x: pill.x, width: pill.width }}
          exit={{ opacity: 0 }}
          transition={{ type: "spring", stiffness: 380, damping: 32, mass: 0.6 }}
        />
      )}
      {children}
    </div>
  );
}
