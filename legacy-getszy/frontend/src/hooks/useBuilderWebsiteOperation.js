import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const TERMINAL = ["SUCCEEDED", "FAILED_REFUNDED", "REJECTED_NO_CHARGE"];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Shared lifecycle for the managed Builder (website / landing page) operation.
 *
 * One browser-generated Idempotency-Key maps to one authoritative operation.
 * Retry/refresh reattaches to the same operation; it never creates a new charge.
 * The component must render the authoritative operation state, never an assumption.
 */
export function useBuilderWebsiteOperation({ storageKey = "getszy_builder_operation", onSucceeded, noun = "draft" } = {}) {
  const [operation, setOperation] = useState(null);
  const [busy, setBusy] = useState(false);
  const pollCancelledRef = useRef(false);

  const persist = useCallback((key, op) => {
    sessionStorage.setItem(storageKey, JSON.stringify({ idempotencyKey: key, operation: op }));
  }, [storageKey]);

  const finish = useCallback(async (op) => {
      if (op.status === "SUCCEEDED" && op.resource_id) {
      try {
        const pr = await api.get(`/builder/projects/${op.resource_id}`);
        try { await onSucceeded?.(pr.data, op); } catch { /* component wiring must not block clearing */ }
        sessionStorage.removeItem(storageKey);
        toast.success(`Private ${noun} ready`);
      } catch {
        toast.error(`Your ${noun} is ready but could not be loaded for preview — open it from My Getszy.`);
      }
    } else if (op.status === "REJECTED_NO_CHARGE") {
      toast.error("More credits are required. No credits were charged.");
    } else if (op.status === "FAILED_REFUNDED") {
      toast.error("Your request could not be completed. Credits were returned.");
    }
    setBusy(false);
  }, [onSucceeded, storageKey, noun]);

  const poll = useCallback(async (key, opId) => {
    let op = null;
    while (opId && !pollCancelledRef.current) {
      await sleep(2500);
      let current;
      try {
        const r = await api.get(`/builder/operations/${opId}`);
        current = r.data?.operation || r.data;
      } catch {
        toast.error("Could not read build status. Refresh to reconnect to your request.");
        setBusy(false);
        return;
      }
      setOperation(current);
      persist(key, current);
      if (TERMINAL.includes(current.status)) { op = current; break; }
    }
    if (op) await finish(op);
  }, [finish, persist]);

  const start = useCallback(async (body) => {
    setBusy(true);
    const key = (globalThis.crypto && crypto.randomUUID)
      ? crypto.randomUUID()
      : `op-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const optimistic = { operation_id: null, status: "PENDING", credit_state: "NOT_DEBITED", resource_id: null };
    setOperation(optimistic);
    persist(key, optimistic);
    try {
      const r = await api.post("/builder/projects", body, { headers: { "Idempotency-Key": key } });
      const op = r.data?.operation || r.data;
      setOperation(op);
      persist(key, op);
      if (op.operation_id && !TERMINAL.includes(op.status)) {
        await poll(key, op.operation_id);
      } else if (TERMINAL.includes(op.status)) {
        await finish(op);
      } else {
        toast.error("Build started but no operation id was returned.");
        setBusy(false);
      }
    } catch (e) {
      sessionStorage.removeItem(storageKey);
      setOperation(null);
      setBusy(false);
      throw e;
    }
  }, [poll, finish, persist, storageKey]);

  const recover = useCallback(() => {
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) return;
    let stored;
    try { stored = JSON.parse(raw); } catch { sessionStorage.removeItem(storageKey); return; }
    const op = stored?.operation;
    const key = stored?.idempotencyKey;
    if (!op || !op.operation_id) return;
    setOperation(op);
    if (TERMINAL.includes(op.status)) {
      if (op.status === "SUCCEEDED" && op.resource_id) finish(op);
      else setBusy(false);
      return;
    }
    setBusy(true);
    poll(key, op.operation_id);
  }, [poll, finish, storageKey]);

  const reset = useCallback(() => {
    sessionStorage.removeItem(storageKey);
    setOperation(null);
    setBusy(false);
  }, [storageKey]);

  useEffect(() => () => { pollCancelledRef.current = true; }, []);

  return { operation, busy, start, recover, reset };
}
