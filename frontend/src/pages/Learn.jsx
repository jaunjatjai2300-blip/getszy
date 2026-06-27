import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CheckCircle2, Circle, ArrowLeft, Sparkles, Send, Loader2, Award, PlayCircle, BookOpen } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { Progress } from "@/components/ui/progress";

export default function Learn() {
  const { slug } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [active, setActive] = useState(null);
  const [tutorMsgs, setTutorMsgs] = useState([]);
  const [tutorInput, setTutorInput] = useState("");
  const [tutorBusy, setTutorBusy] = useState(false);
  const [showCert, setShowCert] = useState(false);
  const [cert, setCert] = useState(null);
  const tutorEnd = useRef(null);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
  }, [user, loading, navigate]);

  useEffect(() => {
    if (!user) return;
    api.get(`/courses/${slug}/learn`).then(({ data }) => {
      setData(data);
      const allLessons = (data.course.modules || []).flatMap((m) => m.lessons);
      const firstIncomplete = allLessons.find((l) => !data.enrollment.completed_lessons?.includes(l.id)) || allLessons[0];
      setActive(firstIncomplete);
    }).catch(() => { toast.error("Not enrolled or course not found"); navigate(`/academy/${slug}`); });
  }, [slug, user, navigate]);

  useEffect(() => { tutorEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [tutorMsgs, tutorBusy]);

  if (!data || !active) return <div className="py-20 text-center">Loading course…</div>;

  const allLessons = (data.course.modules || []).flatMap((m) => m.lessons);
  const completed = new Set(data.enrollment.completed_lessons || []);
  const progress = (completed.size / allLessons.length) * 100;

  const markComplete = async () => {
    try {
      const { data: res } = await api.post(`/lessons/${active.id}/complete`);
      setData({ ...data, enrollment: { ...data.enrollment, completed_lessons: res.completed_lessons, progress: res.progress } });
      toast.success("Lesson marked complete!");
      // auto-advance
      const idx = allLessons.findIndex((l) => l.id === active.id);
      if (idx + 1 < allLessons.length) setActive(allLessons[idx + 1]);
      else if (res.progress >= 1.0) { toast.success("🎉 Course completed! Certificate ready."); openCert(); }
    } catch (e) { toast.error("Failed to mark complete"); }
  };

  const openCert = async () => {
    try { const { data } = await api.get(`/me/courses/${slug}/certificate`); setCert(data); setShowCert(true); }
    catch { toast.error("Complete all lessons first"); }
  };

  const sendTutor = async (text) => {
    if (!text.trim() || tutorBusy) return;
    setTutorInput("");
    setTutorMsgs((m) => [...m, { role: "user", text, id: Math.random().toString() }]);
    setTutorBusy(true);
    try {
      const { data } = await api.post(`/courses/${slug}/tutor`, { message: text, lesson_id: active.id });
      setTutorMsgs((m) => [...m, { role: "assistant", text: data.reply, id: Math.random().toString() }]);
    } catch { toast.error("Tutor offline"); }
    finally { setTutorBusy(false); }
  };

  return (
    <div className="grid lg:grid-cols-[280px_1fr_360px] min-h-screen" data-testid="learn-page">
      {/* Left: lesson list */}
      <aside className="border-r overflow-y-auto" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <Link to={`/academy/${slug}`} className="text-xs text-[var(--gs-muted)] flex items-center gap-1 hover:text-[var(--gs-ink)] mb-2"><ArrowLeft className="h-3 w-3"/>Back to course</Link>
          <div className="font-display text-lg leading-tight">{data.course.title}</div>
          <div className="mt-3"><Progress value={progress} className="h-2"/></div>
          <div className="text-xs text-[var(--gs-muted)] mt-1">{completed.size} / {allLessons.length} complete</div>
          {progress >= 100 && (<Button onClick={openCert} className="w-full mt-3 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" size="sm" data-testid="learn-view-cert-button"><Award className="h-3.5 w-3.5 mr-1"/>View certificate</Button>)}
        </div>
        <div className="p-2" data-testid="learn-lesson-list">
          {data.course.modules.map((m) => (
            <div key={m.id} className="mb-3">
              <div className="text-xs uppercase tracking-wider text-[var(--gs-muted)] px-3 py-2">{m.title}</div>
              {m.lessons.map((l, idx) => {
                const isComplete = completed.has(l.id);
                const isActive = l.id === active.id;
                return (
                  <button key={l.id} onClick={() => setActive(l)} data-testid={`learn-lesson-${l.id}`} className={`w-full text-left flex items-start gap-2 px-3 py-2 rounded-lg text-sm ${isActive ? "bg-[var(--gs-surface-2)] font-semibold" : "hover:bg-[var(--gs-surface-2)]"}`}>
                    {isComplete ? <CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)] mt-0.5 flex-shrink-0"/> : <Circle className="h-4 w-4 text-[var(--gs-muted)] mt-0.5 flex-shrink-0"/>}
                    <span className="flex-1"><span className="text-xs text-[var(--gs-muted)] mr-1">{idx + 1}.</span>{l.title}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      {/* Center: player */}
      <main className="overflow-y-auto">
        <div className="max-w-3xl mx-auto p-4 sm:p-8">
          <div className="aspect-video rounded-2xl overflow-hidden bg-black mb-4" data-testid="learn-video-player">
            {active.video_url ? (
              <iframe src={active.video_url} title={active.title} className="w-full h-full" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen/>
            ) : (
              <div className="w-full h-full grid place-items-center text-white">
                <div className="text-center"><PlayCircle className="h-16 w-16 mx-auto mb-2 opacity-50"/><p>Video coming soon</p></div>
              </div>
            )}
          </div>
          <h1 className="font-display text-2xl sm:text-3xl mb-2">{active.title}</h1>
          <div className="flex items-center gap-3 text-sm text-[var(--gs-muted)] mb-4"><span className="flex items-center gap-1"><BookOpen className="h-3.5 w-3.5"/>{active.duration_min} min</span></div>
          <p className="text-[var(--gs-ink)]/80 mb-6">{active.description}</p>
          <Button onClick={markComplete} disabled={completed.has(active.id)} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 h-11" data-testid="learn-mark-complete-button">
            {completed.has(active.id) ? (<><CheckCircle2 className="h-4 w-4 mr-2"/>Completed</>) : "Mark as complete"}
          </Button>
        </div>
      </main>

      {/* Right: AI Tutor */}
      <aside className="hidden lg:flex flex-col border-l h-screen sticky top-0" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }} data-testid="learn-tutor-panel">
        <div className="p-4 border-b flex items-center gap-3" style={{ borderColor: "var(--gs-border)" }}>
          <div className="h-9 w-9 rounded-xl grid place-items-center" style={{ background: "var(--gs-teal-soft)" }}><Sparkles className="h-5 w-5 text-[var(--gs-teal)]"/></div>
          <div><div className="font-semibold text-sm">AI Tutor</div><div className="text-xs text-[var(--gs-muted)]">Ask anything about this course</div></div>
        </div>
        <div className="flex-1 overflow-auto p-3 space-y-3">
          {tutorMsgs.length === 0 && (
            <div className="text-xs text-[var(--gs-muted)] p-3 rounded-lg" style={{ background: "var(--gs-teal-soft)" }}>Hi {user.name}! 👋 I can explain concepts, give examples, or quiz you. Try: <em>"Explain {active.title} simply"</em></div>
          )}
          <AnimatePresence>
            {tutorMsgs.map((m) => (
              <motion.div key={m.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[88%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${m.role === "user" ? "bg-white border" : ""}`} style={{ borderColor: m.role === "user" ? "var(--gs-border)" : undefined, background: m.role === "user" ? "#fff" : "var(--gs-teal-soft)" }}>{m.text}</div>
              </motion.div>
            ))}
          </AnimatePresence>
          {tutorBusy && (<div className="flex justify-start"><div className="px-3 py-2 rounded-2xl flex items-center gap-2 text-sm" style={{ background: "var(--gs-teal-soft)" }}><Loader2 className="h-3.5 w-3.5 animate-spin"/>Thinking…</div></div>)}
          <div ref={tutorEnd}/>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); sendTutor(tutorInput); }} className="p-3 border-t flex gap-2" style={{ borderColor: "var(--gs-border)" }}>
          <Textarea rows={1} value={tutorInput} onChange={(e) => setTutorInput(e.target.value)} placeholder="Ask your tutor…" className="resize-none min-h-[40px] max-h-24 text-sm" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendTutor(tutorInput); } }} data-testid="learn-tutor-input"/>
          <Button type="submit" disabled={tutorBusy || !tutorInput.trim()} className="h-10 w-10 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="learn-tutor-send-button">{tutorBusy ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>}</Button>
        </form>
      </aside>

      {/* Certificate modal */}
      {showCert && cert && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.6)" }} onClick={() => setShowCert(false)} data-testid="learn-cert-modal">
          <div className="bg-white rounded-2xl p-8 max-w-xl w-full text-center" onClick={(e) => e.stopPropagation()}>
            <Award className="h-14 w-14 mx-auto text-[var(--gs-primary)] mb-3"/>
            <div className="text-xs uppercase tracking-[0.2em] text-[var(--gs-muted)]">Certificate of Completion</div>
            <div className="font-display text-3xl mt-2">{cert.student_name}</div>
            <div className="text-sm text-[var(--gs-muted)] mt-2">has successfully completed</div>
            <div className="font-display text-xl mt-1">{cert.course_title}</div>
            <div className="text-xs text-[var(--gs-muted)] mt-1">{cert.course_level} Level</div>
            <div className="mt-6 flex justify-between text-xs text-[var(--gs-muted)] border-t pt-4" style={{ borderColor: "var(--gs-border)" }}>
              <div><div>Issued</div><div className="font-semibold text-[var(--gs-ink)]">{cert.completed_at ? new Date(cert.completed_at).toLocaleDateString() : "—"}</div></div>
              <div><div>Certificate ID</div><div className="font-mono text-[var(--gs-ink)]">{cert.certificate_id}</div></div>
              <div><div>Instructor</div><div className="font-semibold text-[var(--gs-ink)]">{cert.instructor}</div></div>
            </div>
            <Button onClick={() => setShowCert(false)} className="mt-6 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Close</Button>
          </div>
        </div>
      )}
    </div>
  );
}
