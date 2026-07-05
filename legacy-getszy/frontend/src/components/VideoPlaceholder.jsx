import { Play, Lock, Sparkles, Clock } from "lucide-react";

export function VideoPlaceholder({ title, duration, isPremium = false, locked = false }) {
  return (
    <div className="relative w-full h-full grid place-items-center overflow-hidden" style={{ background: "linear-gradient(135deg, #2F7E7A 0%, #1B1A18 60%, #A86B5B 100%)" }} data-testid="video-placeholder">
      {/* subtle pattern */}
      <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.3) 1px, transparent 1px), radial-gradient(circle at 60% 70%, rgba(255,255,255,0.2) 1px, transparent 1px)", backgroundSize: "40px 40px" }}/>
      <div className="absolute top-4 left-4 text-white/80 text-xs uppercase tracking-[0.2em] flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5"/>Getszy AI Academy
      </div>
      <div className="absolute top-4 right-4 text-white/70 text-xs flex items-center gap-1">
        <Clock className="h-3 w-3"/>{duration || 10} min
      </div>
      <div className="relative text-center text-white px-6 max-w-md">
        <div className="h-16 w-16 mx-auto rounded-full grid place-items-center bg-white/15 backdrop-blur-sm mb-4 ring-1 ring-white/20">
          {locked ? <Lock className="h-7 w-7"/> : <Play className="h-7 w-7"/>}
        </div>
        <div className="font-display text-2xl sm:text-3xl mb-2 leading-tight">{title}</div>
        <div className="text-white/70 text-sm">{locked ? "Upgrade to Pro to unlock" : "🎬 Branded video coming soon"}</div>
        {isPremium && <div className="mt-3 inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white/15 text-xs"><Sparkles className="h-3 w-3"/>Premium content</div>}
      </div>
      <div className="absolute bottom-4 right-4 text-white/30 font-display text-xl select-none">getszy</div>
    </div>
  );
}
