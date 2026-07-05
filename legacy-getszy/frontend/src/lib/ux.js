import { toast } from "sonner";

/** Undoable delete pattern.
 *  Shows a 5-second toast with Undo button. Only calls the actual delete
 *  if the user does NOT click Undo within the timeout.
 *
 *  Usage:
 *    undoableDelete({
 *      itemLabel: "chat",
 *      onOptimisticRemove: () => setItems(list.filter(...)),
 *      onCommit: async () => await api.delete(...),
 *      onRestore: () => setItems(originalList),
 *    });
 */
export function undoableDelete({ itemLabel = "item", onOptimisticRemove, onCommit, onRestore, timeoutMs = 5000 }) {
  let committed = false;
  let undone = false;
  onOptimisticRemove?.();
  const toastId = toast(
    `${itemLabel.charAt(0).toUpperCase() + itemLabel.slice(1)} deleted`,
    {
      description: "Undo within 5 seconds.",
      duration: timeoutMs,
      action: {
        label: "Undo",
        onClick: () => { undone = true; onRestore?.(); toast.dismiss(toastId); },
      },
    }
  );
  setTimeout(async () => {
    if (undone || committed) return;
    committed = true;
    try { await onCommit?.(); }
    catch (e) {
      onRestore?.();
      toast.error(`Could not delete ${itemLabel}. Restored.`);
    }
  }, timeoutMs + 50);
}

/** Standard error toast with retry action. */
export function errorWithRetry(message, retryFn, opts = {}) {
  return toast.error(message, {
    description: opts.description,
    duration: opts.duration ?? 8000,
    action: retryFn ? { label: "Retry", onClick: retryFn } : undefined,
  });
}

/** Success toast with an optional "View" action. */
export function successWithView(message, onView) {
  return toast.success(message, {
    duration: 4000,
    action: onView ? { label: "View", onClick: onView } : undefined,
  });
}
