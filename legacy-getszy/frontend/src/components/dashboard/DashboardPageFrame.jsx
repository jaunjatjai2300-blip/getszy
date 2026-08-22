import { Sparkles } from "lucide-react";

/**
 * Customer-facing page frame shared by the Founder OS product modules.
 * It keeps page hierarchy and context consistent without forcing each module
 * into an admin-style card grid.
 */
export default function DashboardPageFrame({
  eyebrow = "Founder OS",
  title,
  description,
  icon: Icon = Sparkles,
  actions,
  metrics = [],
  hint,
  children,
  className = "",
}) {
  return (
    <section className={`mx-auto w-full max-w-[1440px] space-y-6 md:space-y-8 ${className}`}>
      <header className="relative overflow-hidden rounded-2xl border px-5 py-5 md:px-7 md:py-6" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="absolute inset-y-0 right-0 hidden w-2/5 bg-gradient-to-l from-[var(--gs-teal)]/10 to-transparent md:block" aria-hidden="true" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 max-w-3xl">
            <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--gs-teal)]">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--gs-teal)]/10"><Icon className="h-3.5 w-3.5" /></span>
              {eyebrow}
            </div>
            <h1 className="font-display text-2xl leading-tight text-[var(--gs-ink)] md:text-3xl">{title}</h1>
            {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--gs-muted)] md:text-[15px]">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2 lg:justify-end">{actions}</div>}
        </div>
        {(metrics.length > 0 || hint) && (
          <div className="relative mt-5 flex flex-col gap-3 border-t pt-4 md:flex-row md:items-center md:justify-between" style={{ borderColor: "var(--gs-border)" }}>
            {metrics.length > 0 && (
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                {metrics.map((metric) => (
                  <div key={metric.label} className="flex items-baseline gap-1.5">
                    <span className="text-lg font-semibold text-[var(--gs-ink)]">{metric.value}</span>
                    <span className="text-xs text-[var(--gs-muted)]">{metric.label}</span>
                  </div>
                ))}
              </div>
            )}
            {hint && <p className="max-w-xl text-xs leading-5 text-[var(--gs-muted)]"><span className="font-medium text-[var(--gs-ink)]">Next:</span> {hint}</p>}
          </div>
        )}
      </header>
      {children}
    </section>
  );
}
