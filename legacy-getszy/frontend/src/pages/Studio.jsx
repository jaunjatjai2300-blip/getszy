import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Sparkles, Clock, Coffee, Mic2, Wand2, Loader2, CheckCircle2, ChevronRight, Youtube, Instagram, Facebook } from "lucide-react";

const HOURS = [
  { time: "6 AM",  task: "Trending research",          done: true },
  { time: "8 AM",  task: "Script writing",             done: true },
  { time: "10 AM", task: "Voice-over & B-roll",        done: true },
  { time: "12 PM", task: "Video editing & captions",   done: true },
  { time: "2 PM",  task: "Thumbnail A/B testing",      done: true },
  { time: "4 PM",  task: "Multi-platform publishing",  done: true },
  { time: "6 PM",  task: "Comments & DM replies",      done: true },
  { time: "8 PM",  task: "Analytics & tomorrow\u2019s plan", done: true },
];

export default function Studio() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const join = async (e) => {
    e?.preventDefault();
    if (!email || !email.includes("@")) return;
    setBusy(true);
    try {
      await api.post("/waitlist", { email, interest: "reels_studio" });
      setDone(true);
    } catch { setDone(true); /* even on duplicate, show success */ }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen" style={{ background: "radial-gradient(circle at 20% 0%, var(--gs-teal-soft) 0%, #F7F5F2 45%)" }} data-testid="reels-studio-page">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
        {/* HERO */}
        <div className="text-center">
          <Badge className="mb-5 text-sm px-3 py-1.5" style={{ background: "var(--gs-teal)", color: "white" }} data-testid="reels-studio-badge">
            <Sparkles className="h-3.5 w-3.5 inline mr-1"/>Coming Soon
          </Badge>

          <h1 className="font-display text-5xl sm:text-7xl leading-tight" data-testid="reels-studio-title">
            Getszy <span style={{ color: "var(--gs-teal)" }}>Reels Studio</span>
          </h1>

          <p className="mt-5 text-lg sm:text-xl text-[var(--gs-muted)] max-w-2xl mx-auto">
            Your whole creator day <span className="font-semibold text-[var(--gs-ink)]">done in minutes</span>.
            <br className="hidden sm:block"/>One AI co-creator for YouTubers, Reel creators, Influencers &amp; Bloggers.
          </p>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-2 text-sm text-[var(--gs-muted)]">
            <span className="flex items-center gap-1"><Youtube className="h-4 w-4"/>YouTubers</span>
            <span>·</span>
            <span className="flex items-center gap-1"><Instagram className="h-4 w-4"/>Instagram</span>
            <span>·</span>
            <span className="flex items-center gap-1"><Facebook className="h-4 w-4"/>Facebook</span>
            <span>·</span>
            <span className="flex items-center gap-1"><Mic2 className="h-4 w-4"/>Podcasters</span>
            <span>·</span>
            <span>Bloggers</span>
          </div>

          {/* Waitlist */}
          {!done ? (
            <form onSubmit={join} className="mt-9 max-w-md mx-auto flex gap-2" data-testid="waitlist-form">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="apna email do, founder access milega" className="h-12 text-base" required data-testid="waitlist-email-input"/>
              <Button type="submit" disabled={busy} className="h-12 px-5 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 gap-2" data-testid="waitlist-submit-button">
                {busy ? <Loader2 className="h-4 w-4 animate-spin"/> : <ChevronRight className="h-4 w-4"/>}
                Join waitlist
              </Button>
            </form>
          ) : (
            <div className="mt-9 max-w-md mx-auto px-4 py-3 rounded-xl text-sm flex items-center justify-center gap-2" style={{ background: "var(--gs-teal-soft)", color: "var(--gs-teal)" }} data-testid="waitlist-success">
              <CheckCircle2 className="h-5 w-5"/>Thanks! Aapko launch se pehle pata chal jayega.
            </div>
          )}
          <p className="mt-3 text-xs text-[var(--gs-muted)]">Founder waitlist · early access · no spam, promise</p>
        </div>

        {/* DAY-LONG WORK STRIP */}
        <section className="mt-20 sm:mt-28">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs uppercase tracking-wider" style={{ background: "var(--gs-surface-2)", color: "var(--gs-muted)" }}>
              <Clock className="h-3.5 w-3.5"/>A creator&apos;s whole day
            </div>
            <h2 className="font-display text-3xl sm:text-5xl mt-4">14 hours of work.<br/>Done while you sip chai.</h2>
            <p className="text-[var(--gs-muted)] mt-3 max-w-xl mx-auto">From the morning&apos;s research to night&apos;s analytics — every repetitive task you do, our AI agents handle in the background.</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {HOURS.map((h, i) => (
              <div key={i} className="gs-card p-4 relative" data-testid={`day-step-${i}`}>
                <div className="flex items-center gap-2 text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider">
                  <Clock className="h-3 w-3"/>{h.time}
                </div>
                <div className="mt-2 font-display text-lg">{h.task}</div>
                <CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)] absolute top-3 right-3"/>
              </div>
            ))}
          </div>
        </section>

        {/* WHY BLOCK (no features list, just feel) */}
        <section className="mt-20 sm:mt-28 text-center">
          <Coffee className="h-10 w-10 mx-auto text-[var(--gs-teal)] mb-3"/>
          <h2 className="font-display text-3xl sm:text-4xl">Built in India.<br/>For Indian creators.</h2>
          <p className="mt-4 text-[var(--gs-muted)] max-w-2xl mx-auto">
            Hindi-first. Hinglish-friendly. UPI-priced. No $99/month bills, no foreign cards, no learning curve.
            <br/>Just — <span className="italic font-semibold text-[var(--gs-ink)]">tell it what you want</span> — your AI co-creator does the rest.
          </p>
        </section>

        {/* FOUNDER NOTE */}
        <section className="mt-20 sm:mt-24 max-w-2xl mx-auto">
          <div className="gs-card p-6 sm:p-8">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-full grid place-items-center flex-shrink-0" style={{ background: "var(--gs-teal)", color: "white" }}>
                <Wand2 className="h-5 w-5"/>
              </div>
              <div className="text-sm leading-relaxed text-[var(--gs-muted)]">
                <p>Hum jaante hain creator banna kitna thakane wala kaam hai. Research, scripting, recording, editing, posting, replies—din khatam ho jaata hai, content aur grow nahi hota.</p>
                <p className="mt-3">Getszy Reels Studio is being built so you can finally focus on the part you love. Hum baaki sab sambhalenge.</p>
                <p className="mt-4 font-semibold text-[var(--gs-ink)]">— Team Getszy</p>
              </div>
            </div>
          </div>
        </section>

        {/* SECONDARY CTA */}
        <section className="mt-16 text-center">
          <p className="text-sm text-[var(--gs-muted)]">Meanwhile, explore what we&apos;ve already built →</p>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <Link to="/academy" className="px-4 py-2 rounded-full border text-sm hover:bg-white" style={{ borderColor: "var(--gs-border)" }} data-testid="reels-studio-academy-link">AI Academy</Link>
            <Link to="/studio/media" className="px-4 py-2 rounded-full border text-sm hover:bg-white" style={{ borderColor: "var(--gs-border)" }} data-testid="reels-studio-media-link">Media Studio</Link>
            <Link to="/shop" className="px-4 py-2 rounded-full border text-sm hover:bg-white" style={{ borderColor: "var(--gs-border)" }} data-testid="reels-studio-shop-link">Shop</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
