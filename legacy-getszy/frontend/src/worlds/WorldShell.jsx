/**
 * WorldShell — the only thing every visual world shares structurally.
 *
 * It scopes the world's palette to CSS custom properties and mounts the ambient
 * background for that world's mood. Everything else — composition, spacing,
 * typography, product presentation — is the world's own business.
 *
 * Worlds read the palette through `--w-*` so their markup never hardcodes a hex.
 */
import AmbientBackground from "@/experience/AmbientBackground";

export default function WorldShell({ config, children, ambient = true, className = "" }) {
  const p = config.palette;
  return (
    <div
      data-world={config.id}
      className={`relative ${className}`}
      style={{
        "--w-bg": p.bg,
        "--w-surface": p.surface,
        "--w-ink": p.ink,
        "--w-muted": p.muted,
        "--w-accent": p.accent,
        "--w-deep": p.deep,
        "--w-champagne": p.champagne,
        background: p.bg,
        color: p.ink,
      }}
    >
      {ambient && <AmbientBackground palette={p} mood={config.motion} />}
      <div className="relative">{children}</div>
    </div>
  );
}

/**
 * Shared add-to-bag control.
 *
 * Level 3 by the glass rules: solid, never blurred, always legible. Every world
 * styles it with its own accent, but none of them may turn it into glass.
 */
export function AddToBag({ product, onAdd, label = "Add to bag", compact = false, testId }) {
  if (compact) {
    return (
      <button
        onClick={onAdd}
        aria-label={`${label}: ${product.name}`}
        data-testid={testId}
        className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-white transition-colors"
        style={{ background: "var(--w-accent)" }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
          <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
          <path d="M3 6h18M16 10a4 4 0 0 1-8 0" />
        </svg>
      </button>
    );
  }
  return (
    <button
      onClick={onAdd}
      data-testid={testId}
      className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-full px-7 text-sm font-semibold text-white transition-colors"
      style={{ background: "var(--w-accent)" }}
    >
      {label}
    </button>
  );
}
