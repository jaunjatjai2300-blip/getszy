/* eslint-disable react/no-unescaped-entities */
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Volume2, FileText, LayoutGrid, Search, Image as ImageIcon, Zap } from "lucide-react";

// Meet Reva — the AI co-pilot hero. Reva's real portrait carries her golden halo
// and blush background; the UI sits in the empty space beside her. Level-1 voice:
// the browser's own speech engine, unlocked by a click (browsers block auto-audio).

const GREETING = "Hi, I'm Reva, your AI co-pilot for commerce, content and growth. Tell me what to build, and I'll help you do it ten times faster.";
const LINES = [
  "Tell me what to build, and I'll draft it in seconds.",
  "Product copy, social posts, SEO, images — I've got you.",
  "Say the word, and we'll grow your business together.",
];

const CARDS = [
  { icon: FileText, label: "Product Descriptions" },
  { icon: LayoutGrid, label: "Social Media Post" },
  { icon: Search, label: "SEO Title & Copy" },
  { icon: ImageIcon, label: "Generate AI Images" },
];

const REVA_IMG = `${process.env.PUBLIC_URL || ""}/reva.png`;

export default function MeetReva() {
  const navigate = useNavigate();
  const [line, setLine] = useState("");
  const [voiceOn, setVoiceOn] = useState(false);
  const synth = typeof window !== "undefined" ? window.speechSynthesis : null;

  // typed, rotating sub-line — Reva "thinking out loud"
  useEffect(() => {
    const reduce = typeof window !== "undefined"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setLine(LINES[0]); return undefined; }
    let stop = false, k = 0, i = 0, text = LINES[0];
    const type = () => {
      if (stop) return;
      i += 1; setLine(text.slice(0, i));
      if (i < text.length) setTimeout(type, 30 + Math.random() * 42);
      else setTimeout(() => { k = (k + 1) % LINES.length; text = LINES[k]; i = 0; type(); }, 2400);
    };
    type();
    return () => { stop = true; };
  }, []);

  const pickVoice = () => {
    if (!synth) return null;
    const v = synth.getVoices();
    return v.find((x) => /en-IN/i.test(x.lang))
      || v.find((x) => /female/i.test(x.name) && /^en/i.test(x.lang))
      || v.find((x) => /^en/i.test(x.lang)) || v[0] || null;
  };

  const hearReva = () => {
    if (!synth) return;
    if (voiceOn) { synth.cancel(); setVoiceOn(false); return; }
    setVoiceOn(true);
    const u = new SpeechSynthesisUtterance(GREETING);
    const vc = pickVoice(); if (vc) u.voice = vc;
    u.rate = 0.98; u.pitch = 1.03;
    u.onend = () => setVoiceOn(false);
    u.onerror = () => setVoiceOn(false);
    synth.speak(u);
  };

  const Wordmark = ({ className = "" }) => (
    <h2
      className={"font-display font-bold leading-[0.9] tracking-tight " + className}
      style={{ backgroundImage: "linear-gradient(92deg,#C96A85,#E7B268 50%,#C96A85)", WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}
    >
      REVA<span style={{ WebkitTextFillColor: "#E0A868", fontSize: "0.32em", verticalAlign: "top" }}>✦</span>
    </h2>
  );

  const Copy = ({ onImage }) => (
    <>
      <span className="inline-flex self-start items-center gap-2 rounded-full bg-white/85 border border-white/80 px-3.5 py-1.5 text-xs font-semibold text-[#A94E6B] shadow-[0_10px_22px_-12px_rgba(120,60,86,0.5)]">
        <Sparkles className="h-3.5 w-3.5" /> Your AI Co-Pilot
      </span>
      <p className="mt-4 text-[15px] font-medium text-[#6E5A67]">Meet</p>
      <Wordmark className={onImage ? "text-[52px] sm:text-7xl lg:text-[88px]" : "text-6xl sm:text-7xl"} />
      <p className="mt-3 font-display text-lg sm:text-2xl leading-snug text-[#402E3A] max-w-[20ch]">
        Your AI Co-Pilot for Commerce, Content &amp; Growth.
      </p>
      <p className="mt-3 text-[15px] text-[#6E5A67] max-w-[34ch] min-h-[1.5em]">
        {line}
        <span className="inline-block w-[2px] h-[1em] ml-0.5 align-[-2px] bg-[#C96A85] animate-pulse" />
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button onClick={() => navigate("/dashboard")} className="gs-btn-primary inline-flex items-center gap-2 rounded-full">
          Chat with Reva <ArrowRight className="h-4 w-4" />
        </button>
        {synth && (
          <button
            onClick={hearReva}
            aria-pressed={voiceOn}
            className={"inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold border transition-colors "
              + (voiceOn ? "bg-[#C96A85] text-white border-[#C96A85]" : "bg-white/80 text-[#A94E6B] border-[#E7C3CE] hover:bg-white")}
          >
            <Volume2 className="h-4 w-4" /> {voiceOn ? "Speaking…" : "Hear Reva"}
          </button>
        )}
      </div>
      <div className="mt-5 flex items-center gap-2 text-[13px] text-[#6E5A67]">
        <span className="text-[#E0A868] tracking-wider">★★★★★</span>
        <b className="text-[#402E3A]">4.9</b> · Trusted by <b className="text-[#402E3A]">12,000+</b> businesses
      </div>
    </>
  );

  const Cards = ({ className = "" }) => (
    <div className={"grid grid-cols-2 sm:grid-cols-4 gap-2.5 " + className}>
      {CARDS.map(({ icon: Icon, label }) => (
        <button
          key={label}
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-3 rounded-2xl border border-white/75 bg-white/60 backdrop-blur px-3 py-2.5 text-left shadow-[0_16px_30px_-22px_rgba(120,60,86,0.55)] hover:-translate-y-1 transition-transform"
        >
          <span className="grid place-items-center h-9 w-9 rounded-xl text-[#A94E6B]" style={{ background: "linear-gradient(180deg,#F6E1E8,#F0D2DD)" }}>
            <Icon className="h-4 w-4" />
          </span>
          <span className="text-[12.5px] font-semibold leading-tight text-[#402E3A]">{label}</span>
        </button>
      ))}
    </div>
  );

  return (
    <section className="gs-section">
      <div className="gs-container">
        {/* ── desktop: portrait fills, UI overlaid ── */}
        <div
          className="relative hidden lg:block overflow-hidden rounded-[30px] border border-white/70 shadow-[0_34px_62px_-34px_rgba(120,60,86,0.55)]"
          style={{ aspectRatio: "1186 / 718", background: "#F5E3E6" }}
        >
          <img src={REVA_IMG} alt="Reva, your AI co-pilot" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, rgba(250,236,238,0.94) 0%, rgba(250,236,238,0.7) 30%, rgba(250,236,238,0.15) 50%, transparent 62%)" }} />
          <div className="absolute top-[12%] right-[6%] z-10 inline-flex items-center gap-2 rounded-full bg-white/90 border border-white/80 px-3.5 py-2 text-xs font-semibold text-[#A94E6B] shadow-[0_14px_26px_-14px_rgba(120,60,86,0.55)]">
            <Zap className="h-3.5 w-3.5 text-[#C6883F]" /> 10× faster
          </div>
          <div className="absolute inset-0 z-10 flex flex-col justify-center px-14 max-w-[60%]">
            <Copy onImage />
          </div>
          <Cards className="absolute inset-x-0 bottom-0 z-10 p-3.5" />
          <div className="absolute inset-x-0 bottom-0 h-24 pointer-events-none" style={{ background: "linear-gradient(0deg, rgba(250,236,238,0.7), transparent)" }} />
        </div>

        {/* ── mobile / tablet: stacked ── */}
        <div className="lg:hidden overflow-hidden rounded-[26px] border border-white/70 shadow-[0_28px_50px_-30px_rgba(120,60,86,0.55)]" style={{ background: "linear-gradient(160deg,#FBEFF1,#F3DFE6)" }}>
          <div className="relative" style={{ background: "#F5E3E6" }}>
            <img src={REVA_IMG} alt="Reva, your AI co-pilot" className="w-full h-60 sm:h-80 object-cover" style={{ objectPosition: "72% 22%" }} />
            <div className="absolute top-3 right-3 inline-flex items-center gap-2 rounded-full bg-white/90 border border-white/80 px-3 py-1.5 text-xs font-semibold text-[#A94E6B]">
              <Zap className="h-3.5 w-3.5 text-[#C6883F]" /> 10× faster
            </div>
          </div>
          <div className="px-6 sm:px-8 py-7 flex flex-col">
            <Copy />
          </div>
          <Cards className="px-4 pb-5" />
        </div>
      </div>
    </section>
  );
}
