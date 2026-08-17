import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Gift, Copy, Check, Users, Coins, Link2, Sparkles } from "lucide-react";

export default function Referrals() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!user) return;
    let active = true;
    api.get("/auth/referrals")
      .then((r) => { if (active) setData(r.data); })
      .catch(() => { if (active) setErr("Could not load your referral dashboard."); });
    return () => { active = false; };
  }, [user]);

  async function copy() {
    if (!data?.referral_link) return;
    try { await navigator.clipboard.writeText(data.referral_link); setCopied(true); setTimeout(() => setCopied(false), 1800); }
    catch { setCopied(false); }
  }

  if (authLoading) return <div className="min-h-screen flex items-center justify-center text-[var(--gs-muted)]">Loading…</div>;
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center max-w-md gs-card p-8">
          <Gift className="h-10 w-10 mx-auto mb-3 text-[var(--gs-teal)]" />
          <h1 className="font-display text-2xl mb-2">Refer & Earn</h1>
          <p className="text-sm text-[var(--gs-muted)] mb-4">Login to get your referral link and start earning credits for every friend who joins getszy.</p>
          <a href="/login" className="inline-block px-4 py-2 rounded-lg bg-[var(--gs-teal)] text-white text-sm font-medium">Login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--gs-bg, #f8fafc)" }}>
      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="flex items-center gap-3 mb-1">
          <Gift className="h-7 w-7 text-[var(--gs-teal)]" />
          <h1 className="font-display text-3xl">Refer & Earn</h1>
        </div>
        <p className="text-sm text-[var(--gs-muted)] mb-6">Share your link. Every friend who joins credits <b>+50</b> to your account — real rewards, no cap.</p>

        {err && <div className="gs-card p-4 text-rose-600 text-sm mb-4">{err}</div>}

        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <div className="gs-card p-5">
            <div className="flex items-center gap-2 text-[var(--gs-muted)] text-sm mb-1"><Users className="h-4 w-4" /> Friends joined</div>
            <div className="text-3xl font-display">{data?.total_referred ?? "—"}</div>
          </div>
          <div className="gs-card p-5">
            <div className="flex items-center gap-2 text-[var(--gs-muted)] text-sm mb-1"><Coins className="h-4 w-4" /> Credits earned</div>
            <div className="text-3xl font-display">{data?.rewards_earned ?? "—"}</div>
          </div>
          <div className="gs-card p-5">
            <div className="flex items-center gap-2 text-[var(--gs-muted)] text-sm mb-1"><Sparkles className="h-4 w-4" /> Your code</div>
            <div className="text-2xl font-display font-mono">{data?.referral_code ?? "—"}</div>
          </div>
        </div>

        <div className="gs-card p-5 mb-6">
          <div className="flex items-center gap-2 mb-2"><Link2 className="h-4 w-4 text-[var(--gs-teal)]" /><span className="text-sm font-semibold">Your referral link</span></div>
          <div className="flex gap-2">
            <input readOnly value={data?.referral_link || ""} className="flex-1 px-3 py-2 rounded-lg border text-sm bg-[var(--gs-surface)]" style={{ borderColor: "var(--gs-border)" }} data-testid="referral-link-input" />
            <button onClick={copy} className="px-4 py-2 rounded-lg bg-[var(--gs-teal)] text-white text-sm font-medium flex items-center gap-1" data-testid="referral-copy-button">
              {copied ? <><Check className="h-4 w-4" /> Copied</> : <><Copy className="h-4 w-4" /> Copy</>}
            </button>
          </div>
        </div>

        <div className="gs-card p-5 mb-6">
          <h2 className="font-display text-lg mb-3">Recent referrals</h2>
          {!data?.referred?.length ? (
            <p className="text-sm text-[var(--gs-muted)]">No referrals yet — share your link to start earning.</p>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {data.referred.map((r, i) => (
                <div key={i} className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <div className="text-xs text-[var(--gs-muted)]">{r.email}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-[var(--gs-teal)]">+{r.reward_credits} credits</div>
                    <div className="text-xs text-[var(--gs-muted)] capitalize">{r.status}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="gs-card p-5">
          <h2 className="font-display text-lg mb-3">How it works</h2>
          <ol className="space-y-2 text-sm text-[var(--gs-ink)]">
            <li>1. Copy your unique referral link above.</li>
            <li>2. Share it with friends on WhatsApp, Instagram, or anywhere.</li>
            <li>3. When they sign up using your link, you instantly get <b>+50 credits</b>.</li>
            <li>4. Use credits across getszy — courses, AI tools, and more.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
