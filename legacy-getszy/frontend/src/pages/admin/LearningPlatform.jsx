import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  BookOpen, GraduationCap, Award, FileText, Users, BarChart3,
  Trophy, ChevronDown, ChevronRight, Plus, RefreshCw, Play,
  CheckCircle2, Clock, Star, Edit2, Eye, Download, Search,
  Target, TrendingUp, Zap, Check, X, HelpCircle, Circle
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";

export default function LearningPlatform() {
  const [tab, setTab] = useState("courses");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [courses, setCourses] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [learningPaths, setLearningPaths] = useState([]);
  const [progress, setProgress] = useState(null);

  const [expandedCourse, setExpandedCourse] = useState(null);
  const [modules, setModules] = useState([]);
  const [quizBuilder, setQuizBuilder] = useState(null);
  const [newQuestion, setNewQuestion] = useState({ text: "", type: "mcq", options: ["", ""], answer: "" });

  const load = async () => {
    setError(false);
    try {
      const [c, cert, a, lb, lp, p] = await Promise.all([
        api.get("/admin/learning-platform/courses").catch(() => ({ data: { items: [] } })),
        api.get("/admin/learning-platform/certificates").catch(() => ({ data: { items: [] } })),
        api.get("/admin/learning-platform/assignments").catch(() => ({ data: { items: [] } })),
        api.get("/admin/learning-platform/leaderboard").catch(() => ({ data: { items: [] } })),
        api.get("/admin/learning-platform/learning-paths").catch(() => ({ data: { items: [] } })),
        api.get("/admin/learning-platform/progress").catch(() => ({ data: null })),
      ]);
      setCourses(c.data?.items || []);
      setCertificates(cert.data?.items || []);
      setAssignments(a.data?.items || []);
      setLeaderboard(lb.data?.items || []);
      setLearningPaths(lp.data?.items || []);
      setProgress(p.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const loadModules = async (courseId) => {
    try {
      const r = await api.get(`/admin/learning-platform/courses/${courseId}/modules`);
      setModules(r.data?.items || []);
      setExpandedCourse(courseId);
    } catch { /* silent */ }
  };

  const loadQuiz = async (moduleId) => {
    try {
      const r = await api.get(`/admin/learning-platform/modules/${moduleId}/quiz`);
      setQuizBuilder(r.data);
      setTab("quiz-builder");
    } catch { /* silent */ }
  };

  const addQuestion = async () => {
    if (!quizBuilder || !newQuestion.text.trim()) return;
    try {
      const r = await api.post(`/admin/learning-platform/quizzes/${quizBuilder.id}/questions`, newQuestion);
      setQuizBuilder(prev => ({
        ...prev,
        questions: [...(prev.questions || []), r.data?.item].filter(Boolean),
      }));
      setNewQuestion({ text: "", type: "mcq", options: ["", ""], answer: "" });
    } catch { /* silent */ }
  };

  const gradeSubmission = async (assignmentId, studentId, score, feedback) => {
    try {
      await api.post(`/admin/learning-platform/assignments/${assignmentId}/grade`, { student_id: studentId, score, feedback });
      await load();
    } catch { /* silent */ }
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Learning Platform</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Courses, quizzes, certificates, assignments & progress</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      {/* Progress Summary */}
      {progress && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Learners", value: progress.total_learners, icon: Users },
            { label: "Avg Completion", value: `${progress.avg_completion || 0}%`, icon: Target },
            { label: "Avg Time", value: `${progress.avg_time_spent || 0}h`, icon: Clock },
            { label: "Certificates", value: progress.certificates_issued, icon: Award },
          ].map(s => (
            <Card key={s.label} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{s.label}</span>
                <s.icon className="h-4 w-4 text-[var(--gs-teal)]"/>
              </div>
              <div className="text-xl font-display">{s.value ?? "—"}</div>
            </Card>
          ))}
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="courses"><BookOpen className="h-3 w-3 mr-1 inline"/>Courses</TabsTrigger>
          <TabsTrigger value="certificates"><Award className="h-3 w-3 mr-1 inline"/>Certificates</TabsTrigger>
          <TabsTrigger value="assignments"><FileText className="h-3 w-3 mr-1 inline"/>Assignments</TabsTrigger>
          <TabsTrigger value="leaderboard"><Trophy className="h-3 w-3 mr-1 inline"/>Leaderboard</TabsTrigger>
          <TabsTrigger value="paths"><Target className="h-3 w-3 mr-1 inline"/>Paths</TabsTrigger>
          {quizBuilder && <TabsTrigger value="quiz-builder"><HelpCircle className="h-3 w-3 mr-1 inline"/>Quiz Builder</TabsTrigger>}
        </TabsList>

        {/* Courses */}
        <TabsContent value="courses" className="mt-4 space-y-3">
          {courses.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi courses nahi
            </div>
          ) : (
            courses.map((course, i) => (
              <Card key={course.id || i} className="p-4">
                <div className="flex items-center gap-3 cursor-pointer" onClick={() => loadModules(course.id)}>
                  <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                    <BookOpen className="h-5 w-5 text-[var(--gs-teal)]"/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{course.title}</span>
                      <Badge variant="outline" className="text-[10px]">{course.module_count || 0} modules</Badge>
                      <Badge variant="outline" className="text-[10px]">{course.enrolled || 0} enrolled</Badge>
                    </div>
                    <div className="text-[11px] text-[var(--gs-muted)]">{course.description}</div>
                  </div>
                  {expandedCourse === course.id ? <ChevronDown className="h-4 w-4 text-[var(--gs-muted)]"/> : <ChevronRight className="h-4 w-4 text-[var(--gs-muted)]"/>}
                </div>

                {expandedCourse === course.id && modules.length > 0 && (
                  <div className="mt-3 ml-13 space-y-1.5">
                    {modules.map((mod, mi) => (
                      <div key={mod.id || mi} className="flex items-center gap-3 p-2.5 rounded-lg bg-[var(--gs-surface-2)]">
                        <span className="text-xs text-[var(--gs-muted)] w-6">{mi + 1}.</span>
                        <div className="flex-1">
                          <div className="text-xs font-semibold">{mod.title}</div>
                          <div className="text-[10px] text-[var(--gs-muted)]">{mod.type} · {mod.duration || "—"}</div>
                        </div>
                        <Button variant="ghost" size="sm" className="h-6 text-[10px]" onClick={() => loadQuiz(mod.id)}>
                          <HelpCircle className="h-3 w-3 mr-1"/>Quiz
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            ))
          )}
        </TabsContent>

        {/* Certificates */}
        <TabsContent value="certificates" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Award className="h-4 w-4 text-[var(--gs-teal)]"/>Issued Certificates
            </h3>
            {certificates.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi certificates nahi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Student</TableHead>
                      <TableHead>Course</TableHead>
                      <TableHead>Issued</TableHead>
                      <TableHead>Expiry</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {certificates.map((c, i) => (
                      <TableRow key={c.id || i}>
                        <TableCell className="text-xs font-semibold">{c.student_name}</TableCell>
                        <TableCell className="text-xs">{c.course_title}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{c.issued_at}</TableCell>
                        <TableCell className="text-xs text-[var(--gs-muted)]">{c.expires_at || "Never"}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" className="h-6 text-[10px]">
                            <Download className="h-3 w-3 mr-1"/>Download
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Assignments */}
        <TabsContent value="assignments" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <FileText className="h-4 w-4 text-[var(--gs-teal)]"/>Assignments
            </h3>
            {assignments.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi assignments nahi</div>
            ) : (
              <div className="space-y-3">
                {assignments.map((a, i) => (
                  <div key={a.id || i} className="p-3 rounded-xl border bg-white">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-sm font-semibold">{a.title}</span>
                        <span className="text-[11px] text-[var(--gs-muted)] ml-2">{a.course_title}</span>
                      </div>
                      <Badge variant="outline" className={`text-[10px] ${
                        a.submitted_count > 0 ? "text-amber-600" : "text-[var(--gs-muted)]"
                      }`}>{a.submitted_count || 0} submissions</Badge>
                    </div>
                    {a.submissions?.map((s, si) => (
                      <div key={si} className="flex items-center gap-3 p-2 rounded-lg bg-[var(--gs-surface-2)] mt-1.5">
                        <span className="text-xs font-semibold flex-1">{s.student_name}</span>
                        <span className="text-[10px] text-[var(--gs-muted)]">Score: {s.score ?? "—"}/{a.max_score || 100}</span>
                        <Badge variant="outline" className={`text-[10px] ${s.graded ? "text-emerald-600" : "text-amber-600"}`}>
                          {s.graded ? "Graded" : "Pending"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Leaderboard */}
        <TabsContent value="leaderboard" className="mt-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500"/>Leaderboard
            </h3>
            {leaderboard.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi data nahi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Rank</TableHead>
                      <TableHead>Learner</TableHead>
                      <TableHead>Courses Done</TableHead>
                      <TableHead>Hours</TableHead>
                      <TableHead>Points</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leaderboard.map((l, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <span className={`text-sm font-bold ${i === 0 ? "text-amber-500" : i === 1 ? "text-slate-400" : i === 2 ? "text-amber-700" : "text-[var(--gs-muted)]"}`}>
                            #{i + 1}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs font-semibold">{l.name || l.email}</TableCell>
                        <TableCell className="text-xs">{l.courses_completed || 0}</TableCell>
                        <TableCell className="text-xs">{l.hours_spent || 0}</TableCell>
                        <TableCell className="text-xs font-semibold text-[var(--gs-teal)]">{l.points || 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* Learning Paths */}
        <TabsContent value="paths" className="mt-4 space-y-3">
          {learningPaths.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Target className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi learning paths nahi
            </div>
          ) : (
            learningPaths.map((path, i) => (
              <Card key={path.id || i} className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-sm">{path.title}</h3>
                  <Badge variant="outline" className="text-[10px]">{path.courses?.length || 0} courses</Badge>
                </div>
                <div className="text-[11px] text-[var(--gs-muted)] mb-3">{path.description}</div>
                <div className="space-y-2">
                  {path.courses?.map((c, ci) => (
                    <div key={ci} className="flex items-center gap-2 text-xs">
                      <CheckCircle2 className={`h-3.5 w-3.5 ${c.completed ? "text-emerald-500" : "text-[var(--gs-muted)]"}`}/>
                      <span className={c.completed ? "line-through text-[var(--gs-muted)]" : ""}>{c.title}</span>
                      <span className="ml-auto text-[var(--gs-muted)]">{c.completion_pct || 0}%</span>
                    </div>
                  ))}
                </div>
                {path.enrolled_count != null && (
                  <div className="mt-3 text-[10px] text-[var(--gs-muted)]">
                    {path.enrolled_count} enrolled · {path.avg_completion || 0}% avg completion
                  </div>
                )}
              </Card>
            ))
          )}
        </TabsContent>

        {/* Quiz Builder */}
        {quizBuilder && (
          <TabsContent value="quiz-builder" className="mt-4">
            <Card className="p-5 max-w-2xl">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-[var(--gs-teal)]"/>Quiz Builder — {quizBuilder.title}
              </h3>

              {quizBuilder.questions?.map((q, qi) => (
                <div key={q.id || qi} className="p-3 rounded-lg bg-[var(--gs-surface-2)] mb-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="text-[9px]">{q.type}</Badge>
                    <span className="text-xs font-semibold">{q.text}</span>
                  </div>
                  {q.options && (
                    <div className="flex flex-wrap gap-2 mt-1">
                      {q.options.map((opt, oi) => (
                        <span key={oi} className={`text-[10px] px-2 py-0.5 rounded ${opt === q.answer ? "bg-emerald-100 text-emerald-700" : "bg-white"}`}>{opt}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              <div className="mt-4 pt-4 border-t" style={{ borderColor: "var(--gs-border)" }}>
                <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2">Add Question</div>
                <Input className="text-xs mb-2" placeholder="Question text" value={newQuestion.text} onChange={e => setNewQuestion(p => ({ ...p, text: e.target.value }))}/>
                <Select value={newQuestion.type} onValueChange={v => setNewQuestion(p => ({ ...p, type: v }))}>
                  <SelectTrigger className="w-40 h-8 text-xs mb-2"><SelectValue/></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mcq">Multiple Choice</SelectItem>
                    <SelectItem value="truefalse">True / False</SelectItem>
                    <SelectItem value="text">Text Answer</SelectItem>
                  </SelectContent>
                </Select>
                {newQuestion.type === "mcq" && (
                  <div className="space-y-1 mb-2">
                    {newQuestion.options.map((opt, oi) => (
                      <div key={oi} className="flex items-center gap-2">
                        <input type="radio" name="answer" checked={newQuestion.answer === opt}
                          onChange={() => setNewQuestion(p => ({ ...p, answer: opt }))} className="h-3 w-3"/>
                        <Input className="text-xs flex-1" placeholder={`Option ${oi + 1}`} value={opt}
                          onChange={e => {
                            const opts = [...newQuestion.options];
                            opts[oi] = e.target.value;
                            setNewQuestion(p => ({ ...p, options: opts }));
                          }}/>
                      </div>
                    ))}
                    <Button variant="ghost" size="sm" className="h-6 text-[10px]"
                      onClick={() => setNewQuestion(p => ({ ...p, options: [...p.options, ""] }))}>
                      <Plus className="h-3 w-3 mr-1"/>Add Option
                    </Button>
                  </div>
                )}
                <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={addQuestion}>
                  <Plus className="h-3 w-3 mr-1"/>Add Question
                </Button>
              </div>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
