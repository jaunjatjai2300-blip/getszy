/**
 * Experience level — controls how much of the "Living Glass World" actually runs.
 *
 * Design rule: heavy effects are a progressive enhancement, never a requirement.
 * A mid-range Android on a slow connection should get the same layout, colours
 * and copy — just without blur and ambient animation.
 *
 * Levels:
 *   "full"     — all glass, ambient light, liquid motion
 *   "reduced"  — no backdrop-blur, no ambient animation (sets data-fx="reduced")
 *
 * Resolution order: explicit user choice > device/network signals > "full".
 */

const STORAGE_KEY = "gs_experience";
export const EXPERIENCE_LEVELS = ["full", "reduced"];

/** Heuristic for a device that will struggle with backdrop-filter. */
function deviceLooksLowEnd() {
  if (typeof navigator === "undefined") return false;

  // Data Saver on — respect it, effects are pure decoration.
  if (navigator.connection?.saveData) return true;

  // Very slow effective connection.
  const et = navigator.connection?.effectiveType;
  if (et === "slow-2g" || et === "2g") return true;

  // deviceMemory is in GB and only exposed by Chromium; <= 4 is the common
  // budget-Android bracket where backdrop-filter starts dropping frames.
  if (typeof navigator.deviceMemory === "number" && navigator.deviceMemory <= 4) return true;

  // Low core count is another budget-device signal.
  if (typeof navigator.hardwareConcurrency === "number" && navigator.hardwareConcurrency <= 4) return true;

  return false;
}

/** The user's saved choice, if they made one. */
export function getStoredExperience() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return EXPERIENCE_LEVELS.includes(v) ? v : null;
  } catch {
    return null;
  }
}

/** What we should actually run right now. */
export function resolveExperience() {
  return getStoredExperience() || (deviceLooksLowEnd() ? "reduced" : "full");
}

/** Apply a level to the document. Pass null to clear an override and re-detect. */
export function applyExperience(level) {
  const resolved = EXPERIENCE_LEVELS.includes(level) ? level : resolveExperience();
  try {
    if (EXPERIENCE_LEVELS.includes(level)) localStorage.setItem(STORAGE_KEY, level);
  } catch {
    /* storage unavailable (private mode) — still apply for this session */
  }
  if (typeof document !== "undefined") {
    // Only "reduced" needs an attribute; "full" is the CSS default.
    if (resolved === "reduced") document.documentElement.setAttribute("data-fx", "reduced");
    else document.documentElement.removeAttribute("data-fx");
  }
  return resolved;
}

/** Call once at startup. */
export function initExperience() {
  return applyExperience(getStoredExperience());
}
