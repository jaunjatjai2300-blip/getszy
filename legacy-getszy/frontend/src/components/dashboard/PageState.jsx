import { Loader2, Inbox, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

// Shared, consistent state surfaces used across all dashboard tabs so loading,
// empty and error states look the same everywhere (and errors offer a retry).
export default function PageState({
  kind = "loading",
  title,
  message,
  onRetry,
  icon: Icon,
  actionLabel = "Try again",
  compact = false,
  className = "",
}) {
  const pad = compact ? "py-8" : "py-16";
  if (kind === "loading") {
    return (
      <div className={`flex flex-col items-center justify-center gap-3 ${pad} text-center ${className}`}>
        <Loader2 className="h-7 w-7 animate-spin text-[var(--gs-teal)]" />
        <p className="text-sm text-[var(--gs-muted)]">{title || "Loading…"}</p>
      </div>
    );
  }

  if (kind === "empty") {
    const EmptyIcon = Icon || Inbox;
    return (
      <div className={`flex flex-col items-center justify-center gap-3 ${pad} text-center ${className}`}>
        <div className="rounded-2xl p-4 bg-[var(--gs-surface-2)]">
          <EmptyIcon className="h-7 w-7 text-[var(--gs-muted)]" />
        </div>
        <div>
          <p className="font-medium text-[var(--gs-ink)]">{title || "Nothing here yet"}</p>
          {message && <p className="text-sm text-[var(--gs-muted)] mt-1 max-w-sm">{message}</p>}
        </div>
      </div>
    );
  }

  // error
  const ErrIcon = Icon || AlertTriangle;
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${pad} text-center ${className}`}>
      <div className="rounded-2xl p-4 bg-rose-50">
        <ErrIcon className="h-7 w-7 text-rose-500" />
      </div>
      <div>
        <p className="font-medium text-[var(--gs-ink)]">{title || "Something went wrong"}</p>
        {message && <p className="text-sm text-[var(--gs-muted)] mt-1 max-w-sm break-words">{message}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} data-testid="page-retry" className="mt-1">
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> {actionLabel}
        </Button>
      )}
    </div>
  );
}
