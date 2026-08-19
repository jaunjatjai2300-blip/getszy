// Lightweight in-flight request activity tracker.
// Lets the dashboard chrome show a top progress bar on every API call without
// coupling each page to it.
let count = 0;
const listeners = new Set();

function emit() {
  for (const cb of listeners) {
    try { cb(count); } catch { /* ignore listener errors */ }
  }
}

export function onActivity(cb) {
  listeners.add(cb);
  cb(count);
  return () => listeners.delete(cb);
}

export function _activityInc() { count += 1; emit(); }
export function _activityDec() { count = Math.max(0, count - 1); emit(); }
