import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Live AI-health badge for the customer dashboard.
 *
 * Calls the cheap public surface `/builder/ai/status` so customers can see the
 * generator is online and running on free models — the "instant + errorless"
 * promise made visible. Degrades silently if the call fails.
 */
export default function AIStatusBadge({ className = "" }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .get("/builder/ai/status")
      .then((res) => {
        if (active) setStatus(res.data || null);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <span
        data-testid="ai-status-badge"
        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${className}`}
        style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)", color: "var(--gs-muted)" }}
      >
        <span className="h-2 w-2 rounded-full" style={{ background: "#b08" }} aria-hidden="true" />
        AI status unknown
      </span>
    );
  }

  const healthy = Boolean(status?.healthy);
  const free = status?.mode === "free";
  const dot = healthy ? "#1e8a5a" : "#c2410c";
  const label = healthy ? (free ? "AI online · free models" : "AI online") : "AI limited";

  return (
    <span
      data-testid="ai-status-badge"
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${className}`}
      style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)", color: "var(--gs-ink)" }}
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2" aria-hidden="true">
        {healthy && (
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
            style={{ background: dot }}
          />
        )}
        <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: dot }} />
      </span>
      {label}
    </span>
  );
}
