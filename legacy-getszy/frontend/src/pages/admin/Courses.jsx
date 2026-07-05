import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Pencil, Trash2, BookOpen, PlusCircle } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";

const EMPTY_C = { title: "", subtitle: "", description: "", level: "Beginner", duration_hours: 2, thumbnail: "", outcomes: [], prerequisites: [], is_featured: false };
const EMPTY_L = { course_slug: "", module_id: "", title: "", description: "", video_url: "", duration_min: 10, order: 1 };

export default function AdminCourses() {
  const [courses, setCourses] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [openC, setOpenC] = useState(false);
  const [editingC, setEditingC] = useState(null);
  const [formC, setFormC] = useState(EMPTY_C);
  const [outcomesText, setOutcomesText] = useState("");
  const [openL, setOpenL] = useState(false);
  const [formL, setFormL] = useState(EMPTY_L);
  const [details, setDetails] = useState({});

  const load = async () => { const { data } = await api.get("/admin/courses"); setCourses(data); };
  useEffect(() => { load(); }, []);

  const loadDetail = async (slug) => {
    const { data } = await api.get(`/courses/${slug}`);
    setDetails((d) => ({ ...d, [slug]: data }));
  };

  const toggle = (slug) => {
    if (expanded === slug) setExpanded(null);
    else { setExpanded(slug); if (!details[slug]) loadDetail(slug); }
  };

  const startCreateC = () => { setEditingC(null); setFormC(EMPTY_C); setOutcomesText(""); setOpenC(true); };
  const startEditC = (c) => { setEditingC(c); setFormC({ ...c }); setOutcomesText((c.outcomes || []).join("\n")); setOpenC(true); };

  const saveC = async () => {
    const payload = { ...formC, duration_hours: Number(formC.duration_hours || 0), outcomes: outcomesText.split("\n").map((s) => s.trim()).filter(Boolean) };
    try {
      if (editingC) { await api.put(`/admin/courses/${editingC.slug}`, payload); toast.success("Course updated"); }
      else { await api.post("/admin/courses", payload); toast.success("Course added"); }
      setOpenC(false); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const delC = async (c) => { if (!window.confirm(`Delete ${c.title}?`)) return; await api.delete(`/admin/courses/${c.slug}`); toast.success("Deleted"); await load(); };

  const startCreateL = (course) => {
    const moduleId = details[course.slug]?.modules?.[0]?.id || "";
    setFormL({ ...EMPTY_L, course_slug: course.slug, module_id: moduleId, order: (details[course.slug]?.modules?.[0]?.lessons?.length || 0) + 1 });
    setOpenL(true);
  };

  const saveL = async () => {
    try {
      await api.post("/admin/lessons", { ...formL, duration_min: Number(formL.duration_min), order: Number(formL.order) });
      toast.success("Lesson added");
      setOpenL(false); await loadDetail(formL.course_slug);
    } catch { toast.error("Failed"); }
  };

  const delL = async (slug, lid) => { if (!window.confirm("Delete this lesson?")) return; await api.delete(`/admin/lessons/${lid}`); await loadDetail(slug); };

  return (
    <div data-testid="admin-courses-page">
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="font-display text-3xl">Courses</h1><p className="text-sm text-[var(--gs-muted)]">{courses.length} courses</p></div>
        <Button onClick={startCreateC} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-add-course-button"><Plus className="h-4 w-4 mr-2"/>Add course</Button>
      </div>
      <div className="space-y-3">
        {courses.map((c) => (
          <div key={c.slug} className="gs-card overflow-hidden">
            <div className="p-4 flex items-center gap-4">
              <img src={c.thumbnail} alt="" className="h-16 w-24 rounded-lg object-cover" style={{ background: "var(--gs-surface-2)" }}/>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap"><div className="font-semibold">{c.title}</div><Badge variant="outline">{c.level}</Badge>{c.is_featured && <Badge className="bg-[var(--gs-champagne)] text-[var(--gs-ink)] hover:opacity-100">Featured</Badge>}</div>
                <div className="text-xs text-[var(--gs-muted)]">{c.subtitle}</div>
                <div className="text-xs text-[var(--gs-muted)] mt-1">{c.duration_hours}h · {c.enrollments_count || 0} enrolled</div>
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" onClick={() => toggle(c.slug)} data-testid={`admin-course-toggle-${c.slug}`}><BookOpen className="h-4 w-4"/></Button>
                <Button variant="ghost" size="icon" onClick={() => startEditC(c)}><Pencil className="h-4 w-4"/></Button>
                <Button variant="ghost" size="icon" onClick={() => delC(c)}><Trash2 className="h-4 w-4 text-rose-500"/></Button>
              </div>
            </div>
            {expanded === c.slug && details[c.slug] && (
              <div className="border-t p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>
                <div className="flex justify-between items-center mb-3"><div className="font-semibold text-sm">Lessons</div><Button size="sm" variant="outline" onClick={() => startCreateL(c)} data-testid={`admin-add-lesson-${c.slug}`}><PlusCircle className="h-3.5 w-3.5 mr-1"/>Add lesson</Button></div>
                <div className="space-y-1">{(details[c.slug].modules || []).flatMap((m) => m.lessons).map((l, i) => (
                  <div key={l.id} className="flex items-center gap-3 text-sm p-2 rounded bg-white"><span className="text-xs text-[var(--gs-muted)] w-6">{i + 1}.</span><span className="flex-1">{l.title}</span><span className="text-xs text-[var(--gs-muted)]">{l.duration_min} min</span><Button size="icon" variant="ghost" onClick={() => delL(c.slug, l.id)}><Trash2 className="h-3.5 w-3.5 text-rose-500"/></Button></div>
                ))}</div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Course dialog */}
      <Dialog open={openC} onOpenChange={setOpenC}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editingC ? "Edit course" : "Add course"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Title" value={formC.title} onChange={(e) => setFormC({ ...formC, title: e.target.value })} data-testid="admin-course-title-input"/>
            <Input placeholder="Subtitle" value={formC.subtitle} onChange={(e) => setFormC({ ...formC, subtitle: e.target.value })}/>
            <Textarea placeholder="Description" value={formC.description} onChange={(e) => setFormC({ ...formC, description: e.target.value })}/>
            <div className="grid grid-cols-2 gap-2">
              <Select value={formC.level} onValueChange={(v) => setFormC({ ...formC, level: v })}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="Beginner">Beginner</SelectItem><SelectItem value="Intermediate">Intermediate</SelectItem><SelectItem value="Advanced">Advanced</SelectItem></SelectContent></Select>
              <Input type="number" step="0.5" placeholder="Duration (hours)" value={formC.duration_hours} onChange={(e) => setFormC({ ...formC, duration_hours: e.target.value })}/>
            </div>
            <Input placeholder="Thumbnail URL" value={formC.thumbnail} onChange={(e) => setFormC({ ...formC, thumbnail: e.target.value })}/>
            <Textarea placeholder="Outcomes (one per line)" value={outcomesText} onChange={(e) => setOutcomesText(e.target.value)} rows={4}/>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={formC.is_featured} onChange={(e) => setFormC({ ...formC, is_featured: e.target.checked })}/>Featured</label>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpenC(false)}>Cancel</Button><Button onClick={saveC} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-course-save-button">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Lesson dialog */}
      <Dialog open={openL} onOpenChange={setOpenL}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add lesson</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Lesson title" value={formL.title} onChange={(e) => setFormL({ ...formL, title: e.target.value })}/>
            <Textarea placeholder="Description" value={formL.description} onChange={(e) => setFormL({ ...formL, description: e.target.value })}/>
            <Input placeholder="YouTube embed URL (e.g. https://www.youtube.com/embed/XXXX)" value={formL.video_url} onChange={(e) => setFormL({ ...formL, video_url: e.target.value })}/>
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" placeholder="Duration min" value={formL.duration_min} onChange={(e) => setFormL({ ...formL, duration_min: e.target.value })}/>
              <Input type="number" placeholder="Order" value={formL.order} onChange={(e) => setFormL({ ...formL, order: e.target.value })}/>
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpenL(false)}>Cancel</Button><Button onClick={saveL} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
