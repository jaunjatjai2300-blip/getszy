import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CourseCard } from "@/components/CourseCard";
import { Sparkles, Users, Award, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const LEVELS = ["All", "Beginner", "Intermediate", "Advanced"];

export default function Academy() {
  const [courses, setCourses] = useState([]);
  const [level, setLevel] = useState("All");

  useEffect(() => { api.get("/courses").then(({ data }) => setCourses(data)); }, []);
  const filtered = level === "All" ? courses : courses.filter((c) => c.level === level);

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden" data-testid="academy-hero">
        <div className="absolute inset-0 gs-ai-glow pointer-events-none"/>
        <div className="gs-container relative py-16 lg:py-24 text-center">
          <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-teal)] mb-4 flex items-center justify-center gap-2"><Sparkles className="h-3.5 w-3.5"/>AI Learning Academy</div>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight max-w-3xl mx-auto">Become <span className="text-[var(--gs-teal)]">AI Independent</span>.<br/>From basics to brilliance.</h1>
          <p className="mt-6 text-base sm:text-lg text-[var(--gs-muted)] max-w-2xl mx-auto">Designed for women who want to learn AI in plain language and build real income. Free for now — with a personal AI Tutor.</p>
          <div className="mt-8 flex flex-wrap gap-6 justify-center text-sm text-[var(--gs-muted)]">
            <span className="flex items-center gap-2"><Users className="h-4 w-4 text-[var(--gs-teal)]"/>Women-first</span>
            <span className="flex items-center gap-2"><Brain className="h-4 w-4 text-[var(--gs-teal)]"/>AI Tutor included</span>
            <span className="flex items-center gap-2"><Award className="h-4 w-4 text-[var(--gs-teal)]"/>Free certificate</span>
          </div>
        </div>
      </section>

      <section className="gs-container pb-16">
        <div className="flex items-center gap-2 mb-6 overflow-x-auto">
          {LEVELS.map((l) => (
            <button key={l} onClick={() => setLevel(l)} data-testid={`academy-filter-${l.toLowerCase()}`} className={`px-4 py-2 rounded-full text-sm border whitespace-nowrap ${level === l ? "bg-[var(--gs-ink)] text-white border-[var(--gs-ink)]" : "bg-white border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}>{l}</button>
          ))}
        </div>
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-[var(--gs-muted)]">No courses found.</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="academy-course-grid">
            {filtered.map((c) => <CourseCard key={c.slug} course={c}/>)}
          </div>
        )}
      </section>
    </div>
  );
}
