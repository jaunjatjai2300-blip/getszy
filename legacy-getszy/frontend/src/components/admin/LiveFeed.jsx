import { useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

const ICONS = {
  order_created: "🛒",
  refund_issued: "💸",
  user_signup: "👤",
  failed_login: "⚠️",
  ip_blocked: "🚫",
  low_stock: "📦",
};
const LABELS = {
  order_created: "New order",
  refund_issued: "Refund issued",
  user_signup: "New signup",
  failed_login: "Failed login",
  ip_blocked: "IP blocked",
  low_stock: "Low stock",
};

export default function LiveFeed({ max = 14, height = "h-64" }) {
  const [events, setEvents] = useState([]);
  const [live, setLive] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let closed = false;
    let retry = null;
    const token = localStorage.getItem("gs_token");
    if (!token) return;

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/ws/admin-live?token=${encodeURIComponent(token)}`;

    function connect() {
      if (closed) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setLive(true);
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          setEvents((prev) => [msg, ...prev].slice(0, max));
        } catch (_) {
          /* ignore malformed */
        }
      };
      ws.onclose = () => {
        setLive(false);
        if (!closed) retry = setTimeout(connect, 2500);
      };
      ws.onerror = () => ws.close();
    }
    connect();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      if (wsRef.current) wsRef.current.close();
    };
  }, [max]);

  return (
    <div className="rounded-2xl border border-[var(--gs-border)] bg-[var(--gs-surface)] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="h-4 w-4 text-[var(--gs-teal)]" />
        <h3 className="text-sm font-semibold">Live Ops Feed</h3>
        <span
          className={`ml-auto flex items-center gap-1 text-[10px] ${
            live ? "text-emerald-500" : "text-[var(--gs-muted)]"
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${live ? "bg-emerald-500 animate-pulse" : "bg-gray-400"}`}
          />
          {live ? "Live" : "Offline"}
        </span>
      </div>
      <div className={`${height} overflow-y-auto space-y-2`}>
        {events.length === 0 && (
          <div className="text-xs text-[var(--gs-muted)] py-10 text-center">
            Waiting for live events…
          </div>
        )}
        {events.map((ev, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-xs rounded-lg bg-[var(--gs-surface-2)] p-2"
          >
            <span className="text-sm leading-none">{ICONS[ev.type] || "•"}</span>
            <div className="flex-1 min-w-0">
              <div className="font-medium">{LABELS[ev.type] || ev.type}</div>
              <div className="text-[var(--gs-muted)] truncate">
                {ev.payload ? JSON.stringify(ev.payload) : ""}
              </div>
            </div>
            <span className="text-[10px] text-[var(--gs-muted)] flex-shrink-0">
              {ev.ts ? new Date(ev.ts).toLocaleTimeString() : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
