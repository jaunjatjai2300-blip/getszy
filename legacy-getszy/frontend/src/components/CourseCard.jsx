import { Link } from "react-router-dom";
import { Clock, BookOpen, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const LEVEL_COLOR = { Beginner: "bg-emerald-100 text-emerald-800", Intermediate: "bg-amber-100 text-amber-800", Advanced: "bg-rose-100 text-rose-800" };

export function CourseCard({ course }) {
  return (
    <Link to={`/academy/${course.slug}`} className="group block gs-card gs-card-hover overflow-hidden" data-testid={`course-card-${course.slug}`}>
      <div className="relative aspect-[16/9] overflow-hidden" style={{ background: "var(--gs-surface-2)" }}>
        <img src={course.thumbnail} alt={course.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy"/>
        <Badge className={`absolute top-3 left-3 ${LEVEL_COLOR[course.level] || ""} hover:opacity-100`}>{course.level}</Badge>
        {course.is_featured && <Badge className="absolute top-3 right-3 bg-white text-[var(--gs-ink)] hover:bg-white"><Sparkles className="h-3 w-3 mr-1"/>Featured</Badge>}
      </div>
      <div className="p-5">
        <h3 className="font-display text-lg leading-tight mb-1">{course.title}</h3>
        <p className="text-sm text-[var(--gs-muted)] line-clamp-2 mb-3">{course.subtitle || course.description}</p>
        <div className="flex items-center gap-4 text-xs text-[var(--gs-muted)]">
          <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5"/>{course.duration_hours}h</span>
          <span className="flex items-center gap-1"><BookOpen className="h-3.5 w-3.5"/>{course.enrollments_count || 0} learners</span>
        </div>
      </div>
    </Link>
  );
}
