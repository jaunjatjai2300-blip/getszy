import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Returns a signed, token-gated builder preview URL for a project, or null while
 * loading / on error. Never returns the raw (token-less) path, which must 401.
 */
export function useBuilderPreviewToken(previewId, { backend = "" } = {}) {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!previewId) { setPreviewUrl(null); setError(false); return; }
    let cancelled = false;
    setPreviewUrl(null);
    setError(false);
    api.get(`/builder/projects/${previewId}/preview-token`)
      .then((r) => {
        if (cancelled) return;
        const token = r.data?.token;
        if (token) setPreviewUrl(`${backend}/api/builder/projects/${previewId}/preview?token=${encodeURIComponent(token)}`);
        else setError(true);
      })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [previewId, backend]);

  return { previewUrl, error };
}
