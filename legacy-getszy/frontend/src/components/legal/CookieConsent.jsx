import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X, Cookie } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const accepted = localStorage.getItem("getszy.cookie.consent.v1");
    if (!accepted) {
      const t = setTimeout(() => setVisible(true), 1500);
      return () => clearTimeout(t);
    }
  }, []);

  const accept = (choice) => {
    localStorage.setItem("getszy.cookie.consent.v1", JSON.stringify({ choice, at: new Date().toISOString() }));
    setVisible(false);
  };

  if (!visible) return null;
  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-md z-50" data-testid="cookie-consent" role="dialog" aria-live="polite" aria-label="Cookie consent">
      <div className="gs-card p-4 shadow-xl border-2 border-[var(--gs-teal)]/20">
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-lg grid place-items-center bg-[var(--gs-teal)]/15 shrink-0">
            <Cookie className="h-4 w-4 text-[var(--gs-teal)]" aria-hidden="true"/>
          </div>
          <div className="flex-1">
            <div className="font-semibold text-sm mb-1">Cookies & privacy</div>
            <p className="text-xs text-[var(--gs-muted)] mb-3">
              Hum sirf essential cookies use karte hain — login, preferences aur security ke liye. No ad tracking.
              {" "}<Link to="/privacy" className="text-[var(--gs-teal)] underline">Learn more</Link>
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => accept("all")} className="bg-[var(--gs-teal)] h-8 text-xs" data-testid="cookie-accept-all">Accept all</Button>
              <Button size="sm" variant="outline" onClick={() => accept("essential")} className="h-8 text-xs" data-testid="cookie-accept-essential">Essential only</Button>
            </div>
          </div>
          <button onClick={() => accept("dismissed")} className="text-[var(--gs-muted)] hover:text-[var(--gs-ink)] p-1" aria-label="Dismiss" data-testid="cookie-dismiss">
            <X className="h-4 w-4"/>
          </button>
        </div>
      </div>
    </div>
  );
}
