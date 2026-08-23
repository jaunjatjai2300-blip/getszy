import { Loader2, CheckCircle2, AlertTriangle } from "lucide-react";

const DEFAULT_COPY = {
  PENDING: {
    title: "Request accepted safely.",
    detail: "You can leave or refresh; this request stays authoritative.",
  },
  RUNNING: {
    title: (noun) => `Composing your private ${noun}…`,
    detail: (noun) => `We are applying your brief through the managed quality ladder. No second charge is possible — this view will show a real finished ${noun} or a clear refunded failure.`,
  },
  SUCCEEDED: {
    title: (noun) => `Private ${noun} ready.`,
    detail: (noun) => `Your managed ${noun} is complete and private. Review it before downloading or publishing.`,
  },
  REJECTED_NO_CHARGE: {
    title: "More credits are required. No credits were charged.",
    detail: "Top up your prepaid credits, then start a new request.",
  },
  FAILED_REFUNDED: {
    title: "Your request could not be completed. Credits were returned.",
    detail: "You can start a new request when ready.",
  },
};

const TONE = {
  idle: "text-[var(--gs-teal)]",
  busy: "text-sky-700",
  ok: "text-emerald-700",
  warn: "text-amber-700",
};

function StatusBody({ tone, icon, title, detail }) {
  return (
    <div className="flex items-start gap-2" aria-live="polite">
      <span className={`mt-0.5 h-4 w-4 shrink-0 ${TONE[tone]}`}>{icon}</span>
      <div>
        <strong className="block text-sm">{title}</strong>
        {detail ? <p className="mt-1 text-xs leading-5 text-[var(--gs-muted)]">{detail}</p> : null}
      </div>
    </div>
  );
}

/**
 * Shared customer operation status card.
 * Renders the authoritative operation state: Accepted → Working → Ready / Refunded / Need credits.
 * The component must pass the real operation object; never a guessed status.
 */
export function OperationStatusCard({
  operation,
  noun = "draft",
  idleTitle = "Professional composition, then private review.",
  idleDetail = "A unique draft is generated from your brief, checked for objective quality failures, and kept private until you inspect and approve it.",
}) {
  if (!operation) {
    return (
      <StatusBody
        tone="idle"
        icon={<CheckCircle2 className="h-4 w-4" />}
        title={idleTitle}
        detail={idleDetail}
      />
    );
  }

  const state = DEFAULT_COPY[operation.status];
  if (!state) {
    return (
      <StatusBody
        tone="idle"
        icon={<CheckCircle2 className="h-4 w-4" />}
        title={idleTitle}
        detail={idleDetail}
      />
    );
  }

  const isBusy = operation.status === "PENDING" || operation.status === "RUNNING";
  const isOk = operation.status === "SUCCEEDED";
  const tone = isOk ? "ok" : isBusy ? "busy" : "warn";
  const icon = isBusy
    ? <Loader2 className="h-4 w-4 animate-spin" />
    : isOk
      ? <CheckCircle2 className="h-4 w-4" />
      : <AlertTriangle className="h-4 w-4" />;

  const title = typeof state.title === "function" ? state.title(noun) : state.title;
  const detail = typeof state.detail === "function" ? state.detail(noun) : state.detail;

  return <StatusBody tone={tone} icon={icon} title={title} detail={detail} />;
}

export default OperationStatusCard;
