import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Globe } from "lucide-react";

const LANGS = [
  { code: "en", name: "English" },
  { code: "hi", name: "हिंदी" },
  { code: "hinglish", name: "Hinglish" },
  { code: "ta", name: "தமிழ்" },
  { code: "te", name: "తెలుగు" },
  { code: "bn", name: "বাংলা" },
  { code: "gu", name: "ગુજરાતી" },
  { code: "mr", name: "मराठी" },
];

export default function LanguageSwitcher() {
  const [lang, setLang] = useState(localStorage.getItem("gs_lang") || "en");
  const [sample, setSample] = useState(null);

  useEffect(() => {
    if (lang === "en") {
      setSample(null);
      return;
    }
    api.get(`/admin/i18n/keys?lang=${lang}`)
      .then(({ data }) => setSample(data.keys))
      .catch(() => setSample(null));
  }, [lang]);

  const change = (e) => {
    const v = e.target.value;
    setLang(v);
    localStorage.setItem("gs_lang", v);
    // Foundation step: reloading applies the chosen locale app-wide.
    if (v !== "en") window.location.reload();
  };

  return (
    <div className="px-3 py-2">
      <div className="flex items-center gap-2 text-xs text-[var(--gs-muted)]">
        <Globe className="h-3.5 w-3.5" />
        <select
          value={lang}
          onChange={change}
          data-testid="language-switcher"
          className="bg-[var(--gs-surface-2)] rounded px-2 py-1 text-xs outline-none"
        >
          {LANGS.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>
      </div>
      {sample && (
        <div className="mt-1 text-[10px] text-[var(--gs-muted)] truncate">
          {sample.dashboard} · {sample.orders} · {sample.products}
        </div>
      )}
    </div>
  );
}
