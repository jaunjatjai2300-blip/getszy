import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { GraduationCap, Award, FileQuestion, Plus, Loader2, Trash2, CheckCircle } from "lucide-react";
import { toast } from "sonner";

export default function QuizCerts() {
  const [quizzes, setQuizzes] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateQuiz, setShowCreateQuiz] = useState(false);
  const [quizForm, setQuizForm] = useState({ course_id: "", questions: [{ q: "", options: ["", "", "", ""], correct: 0 }], passing_score: 70 });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [qRes, cRes] = await Promise.allSettled([
        api.get("/extras/quiz/list"),
        api.get("/extras/certificates/list"),
      ]);
      if (qRes.status === "fulfilled") setQuizzes(qRes.value.data?.quizzes || []);
      if (cRes.status === "fulfilled") setCertificates(cRes.value.data?.certificates || []);
    } finally { setLoading(false); }
  };

  const createQuiz = async () => {
    if (!quizForm.course_id.trim()) return toast.error("Enter course ID");
    try {
      await api.post("/extras/quiz/create", {
        course_id: quizForm.course_id,
        questions: quizForm.questions.map(q => ({
          question: q.q,
          options: q.options,
          correct: q.correct,
        })),
        passing_score: quizForm.passing_score,
      });
      toast.success("Quiz created!");
      setShowCreateQuiz(false);
      setQuizForm({ course_id: "", questions: [{ q: "", options: ["", "", "", ""], correct: 0 }], passing_score: 70 });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create quiz");
    }
  };

  const addQuestion = () => {
    setQuizForm(f => ({
      ...f,
      questions: [...f.questions, { q: "", options: ["", "", "", ""], correct: 0 }]
    }));
  };

  const updateQuestion = (idx, field, val) => {
    setQuizForm(f => {
      const q = [...f.questions];
      q[idx] = { ...q[idx], [field]: val };
      return { ...f, questions: q };
    });
  };

  const updateOption = (qIdx, oIdx, val) => {
    setQuizForm(f => {
      const q = [...f.questions];
      const opts = [...q[qIdx].options];
      opts[oIdx] = val;
      q[qIdx] = { ...q[qIdx], options: opts };
      return { ...f, questions: q };
    });
  };

  return (
    <div className="space-y-6" data-testid="quiz-certs-page">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-indigo-100 grid place-items-center">
          <GraduationCap className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-2xl font-display">Quizzes & Certificates</h1>
          <p className="text-xs text-[var(--gs-muted)]">Create quizzes, issue certificates on completion</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <FileQuestion className="h-6 w-6 text-indigo-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{quizzes.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Quizzes</p>
        </Card>
        <Card className="p-4 text-center">
          <Award className="h-6 w-6 text-amber-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{certificates.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Certificates Issued</p>
        </Card>
        <Card className="p-4 text-center">
          <CheckCircle className="h-6 w-6 text-green-600 mx-auto mb-1" />
          <div className="text-2xl font-display">—</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Pass Rate</p>
        </Card>
      </div>

      <Tabs defaultValue="quizzes">
        <TabsList>
          <TabsTrigger value="quizzes"><FileQuestion className="h-4 w-4 mr-1" /> Quizzes</TabsTrigger>
          <TabsTrigger value="certificates"><Award className="h-4 w-4 mr-1" /> Certificates</TabsTrigger>
        </TabsList>

        <TabsContent value="quizzes" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowCreateQuiz(!showCreateQuiz)} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              <Plus className="h-4 w-4 mr-1" /> Create Quiz
            </Button>
          </div>

          {showCreateQuiz && (
            <Card className="p-5 space-y-4">
              <h3 className="font-display">New Quiz</h3>
              <div className="space-y-2">
                <label className="text-xs text-[var(--gs-muted)]">Course ID</label>
                <Input value={quizForm.course_id} onChange={e => setQuizForm(f => ({ ...f, course_id: e.target.value }))} placeholder="Enter course ID" />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-[var(--gs-muted)]">Passing Score (%)</label>
                <Input type="number" value={quizForm.passing_score} onChange={e => setQuizForm(f => ({ ...f, passing_score: +e.target.value }))} />
              </div>

              {quizForm.questions.map((q, qi) => (
                <Card key={qi} className="p-4 space-y-3 bg-[var(--gs-surface-2)]">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-[var(--gs-muted)]">Question {qi + 1}</span>
                    <span className="text-[10px] text-[var(--gs-muted)]">Correct answer index: {q.correct}</span>
                  </div>
                  <Input value={q.q} onChange={e => updateQuestion(qi, 'q', e.target.value)} placeholder="Enter question" />
                  <div className="grid grid-cols-2 gap-2">
                    {q.options.map((opt, oi) => (
                      <div key={oi} className="flex items-center gap-2">
                        <input type="radio" name={`correct-${qi}`} checked={q.correct === oi} onChange={() => updateQuestion(qi, 'correct', oi)} />
                        <Input value={opt} onChange={e => updateOption(qi, oi, e.target.value)} placeholder={`Option ${oi + 1}`} />
                      </div>
                    ))}
                  </div>
                </Card>
              ))}

              <div className="flex gap-2">
                <Button variant="outline" onClick={addQuestion}>Add Question</Button>
                <Button onClick={createQuiz} className="bg-[var(--gs-teal)]">Create Quiz</Button>
              </div>
            </Card>
          )}

          {quizzes.length > 0 && (
            <div className="space-y-2">
              {quizzes.map(q => (
                <Card key={q.id} className="p-3 flex items-center gap-3">
                  <FileQuestion className="h-5 w-5 text-indigo-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{q.course_id}</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">{q.questions?.length || 0} questions • Pass: {q.passing_score}%</p>
                  </div>
                  <Badge variant="outline">{q.id?.slice(0, 8)}</Badge>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="certificates">
          {certificates.length > 0 ? (
            <div className="space-y-2">
              {certificates.map(c => (
                <Card key={c.id} className="p-3 flex items-center gap-3">
                  <Award className="h-5 w-5 text-amber-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Certificate</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">Course: {c.course_id} • Score: {c.score}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-[var(--gs-muted)]">{c.issued_at?.slice(0, 10)}</p>
                    <Badge variant="outline" className="text-[10px]">Verify: {c.verify_hash}</Badge>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No certificates issued yet</Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
