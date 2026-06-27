import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Clock, BookOpen, CheckCircle2, PlayCircle, Award, Sparkles, ArrowRight, Lock } from "lucide-react";import { toast } from "sonner";

const LEVEL_COLOR = { Beginner: "bg-emerald-100 text-emerald-800", Intermediate: "bg-amber-100 text-amber-800", Advanced: "bg-rose-100 text-rose-800" };

export default function CourseDetail() {
  const { slug } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [enrolled, setEnrolled] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/courses/${slug}`).then(({ data }) => setCourse(data)).catch(() => setCourse(false));
    if (user) api.get("/me/enrollments").then(({ data }) => setEnrolled(data.some((e) => e.course_slug === slug))).catch(() => {});
  }, [slug, user]);

  if (course === null) return <div className="py-20 text-center">Loading…</div>;
  if (!course) return <div className="py-20 text-center">Course not found</div>;

  const enroll = async () => {
    if (!user) { navigate("/login"); return; }
    setBusy(true);
    try { await api.post(`/courses/${slug}/enroll`); setEnrolled(true); toast.success(`Enrolled in ${course.title}!`); navigate(`/academy/${slug}/learn`); }
    catch (e) {
      if (e?.response?.status === 402) { toast.error("This is a Pro course"); navigate("/pricing"); }
      else toast.error("Failed to enroll");
    }
    finally { setBusy(false); }
  };

  const isPremium = course.level === "Advanced" || course.is_premium;

  return (
    <div data-testid="course-detail-page">
      <section className="gs-ai-glow">
        <div className="gs-container py-12 lg:py-16 grid md:grid-cols-[1fr_400px] gap-10 items-start">
          <div>
            <Badge className={`${LEVEL_COLOR[course.level]} hover:opacity-100 mb-3`}>{course.level}</Badge>
            <h1 className="font-display text-3xl sm:text-5xl leading-[1.05] tracking-tight mb-3">{course.title}</h1>
            <p className="text-lg text-[var(--gs-muted)] mb-5">{course.subtitle}</p>
            <p className="text-[var(--gs-ink)]/80 mb-6">{course.description}</p>
            <div className="flex flex-wrap gap-4 text-sm text-[var(--gs-muted)]">
              <span className="flex items-center gap-1"><Clock className="h-4 w-4"/>{course.duration_hours} hours</span>
              <span className="flex items-center gap-1"><BookOpen className="h-4 w-4"/>{course.total_lessons} lessons</span>
              <span className="flex items-center gap-1"><Sparkles className="h-4 w-4 text-[var(--gs-teal)]"/>AI Tutor included</span>
            </div>
          </div>
          <div className="gs-card overflow-hidden md:sticky md:top-24">
            <img src={course.thumbnail} alt="" className="w-full aspect-video object-cover"/>
            <div className="p-5">
              <div className="font-display text-2xl mb-1">{isPremium ? "Pro" : "Free"}</div>
              <p className="text-xs text-[var(--gs-muted)] mb-4">{isPremium ? "Available with Pro subscription" : "No subscription needed"}</p>
              {enrolled ? (
                <Button onClick={() => navigate(`/academy/${slug}/learn`)} className="w-full h-12 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90" data-testid="course-continue-button">Continue learning <ArrowRight className="h-4 w-4 ml-2"/></Button>
              ) : isPremium ? (
                <Button onClick={() => navigate("/pricing")} className="w-full h-12 bg-[var(--gs-ink)] hover:bg-black text-white" data-testid="course-upgrade-button"><Lock className="h-4 w-4 mr-2"/>Upgrade to Pro</Button>
              ) : (
                <Button onClick={enroll} disabled={busy} className="w-full h-12 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="course-enroll-button">{busy ? "Enrolling…" : "Enroll for free"}</Button>
              )}
              <ul className="mt-4 space-y-2 text-sm text-[var(--gs-muted)]">
                <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)]"/>Lifetime access</li>
                <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)]"/>Personal AI Tutor</li>
                <li className="flex items-center gap-2"><Award className="h-4 w-4 text-[var(--gs-teal)]"/>Free certificate</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="gs-container py-10 grid md:grid-cols-[1fr_400px] gap-10">
        <div>
          {course.outcomes?.length > 0 && (
            <div className="gs-card p-6 mb-6">
              <h2 className="font-display text-2xl mb-4">What you'll learn</h2>
              <ul className="grid sm:grid-cols-2 gap-3">{course.outcomes.map((o, i) => (<li key={i} className="flex items-start gap-2 text-sm"><CheckCircle2 className="h-4 w-4 text-[var(--gs-teal)] mt-0.5 flex-shrink-0"/>{o}</li>))}</ul>
            </div>
          )}
          <h2 className="font-display text-2xl mb-4">Curriculum</h2>
          <div className="space-y-3" data-testid="course-curriculum">
            {course.modules?.map((m) => (
              <div key={m.id} className="gs-card overflow-hidden">
                <div className="p-4 border-b font-semibold" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>{m.title}</div>
                <div className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {m.lessons.map((l, idx) => (
                    <div key={l.id} className="p-4 flex items-center gap-3 text-sm">
                      <span className="text-[var(--gs-muted)] text-xs w-6">{idx + 1}.</span>
                      {enrolled ? <PlayCircle className="h-4 w-4 text-[var(--gs-teal)]"/> : <Lock className="h-4 w-4 text-[var(--gs-muted)]"/>}
                      <div className="flex-1"><div className="font-medium">{l.title}</div><div className="text-xs text-[var(--gs-muted)]">{l.duration_min} min</div></div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <aside>
          {course.prerequisites?.length > 0 && (
            <div className="gs-card p-5">
              <h3 className="font-semibold mb-2">Prerequisites</h3>
              <ul className="text-sm text-[var(--gs-muted)] space-y-1">{course.prerequisites.map((p, i) => <li key={i}>• {p}</li>)}</ul>
            </div>
          )}
        </aside>
      </section>
    </div>
  );
}
