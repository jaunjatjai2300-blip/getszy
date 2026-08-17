import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";

/**
 * NeoPanel — drops an AI insight (with suggested actions) into any admin tab.
 * Backed by POST /admin/neo/insight. Degrades to a quiet state on error.
 */
export default function NeoPanel({ context = "orders", window = "24h", title = "Neo Insight" }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.post("/admin/neo/insight", { context, window })
      .then((r) => alive && setData(r.data))
      .catch(() => alive && setData(null))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [context, window]);

  return (
    <Card className="p-4 border border-[var(--gs-teal)]/30 bg-[var(--gs-teal)]/5">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Sparkles className="h-4 w-4 text-[var(--gs-teal)]" /> {title}
      </div>
      {loading ? (
        <div className="text-xs text-[var(--gs-muted)] mt-2">Neo soch raha hai…</div>
      ) : data ? (
        <div className="mt-2 space-y-2">
          <p className="text-sm">{data.insight}</p>
          {data.suggestions?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {data.suggestions.map((s, i) => (
                <span key={i} className="text-[11px] px-2 py-1 rounded-full bg-white border border-[var(--gs-border)]">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="text-xs text-[var(--gs-muted)] mt-2">Insight unavailable.</div>
      )}
    </Card>
  );
}
