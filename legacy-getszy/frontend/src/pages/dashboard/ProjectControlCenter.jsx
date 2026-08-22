import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, CircleDashed, ClipboardCheck,
  Eye, FileCheck2, FileText, History, Laptop, Loader2, Plus, RotateCcw, Save, ShieldCheck, Smartphone, Tablet,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

const STATUS_STYLE = {
  done: "bg-emerald-100 text-emerald-800",
  current: "bg-sky-100 text-sky-800",
  blocked: "bg-rose-100 text-rose-800",
  not_started: "bg-slate-100 text-slate-700",
};

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function previewFallbackControls(project) {
  const quality = project?.quality_report || {};
  return {
    previewOnly: true,
    state: {
      quality: {
        status: quality.status || "not_run",
        score: quality.score,
        required_checks_passed: quality.required_checks_passed,
        required_checks_total: quality.required_checks_total,
      },
      evidence: { total: 0, approved: 0, needs_confirmation: 0, blocked: 0, expired: 0, has_blockers: false, has_pending: false },
      eligible_for_customer_review: false,
      current_step: "controls",
      steps: [
        { key: "founder_brief", label: "Founder brief", status: project?.brief ? "done" : "not_started", detail: project?.brief ? "Saved project brief available" : "No saved structured brief available" },
        { key: "build", label: "Build", status: project?.html_content ? "done" : "not_started", detail: project?.html_content ? "Private output exists" : "No private output exists" },
        { key: "quality", label: "Quality gate", status: quality.status === "ready_for_human_review" ? "done" : "not_started", detail: quality.status ? String(quality.status).replaceAll("_", " ") : "Quality details are not available" },
        { key: "controls", label: "Project controls", status: "current", detail: "This preview is read-only; evidence, versions and approvals need the approved backend release" },
      ],
    },
    evidence_items: [],
    versions: [],
    release_reviews: [],
  };
}

export default function ProjectControlCenter() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [controls, setControls] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [versionLabel, setVersionLabel] = useState("");
  const [evidenceItems, setEvidenceItems] = useState([]);
  const [evidenceConfirmed, setEvidenceConfirmed] = useState(false);
  const [previewDevice, setPreviewDevice] = useState("desktop");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const projectResponse = await api.get(`/builder/projects/${projectId}`);
      const controlsResponse = await api.get(`/builder/projects/${projectId}/controls`).catch((error) => {
        if (error?.response?.status === 404) return null;
        throw error;
      });
      const nextControls = controlsResponse?.data || previewFallbackControls(projectResponse.data);
      setProject(projectResponse.data);
      setControls(nextControls);
      setEvidenceItems(nextControls.evidence_items || []);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Could not load this project");
      setProject(null);
      setControls(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const quality = controls?.state?.quality;
  const summary = controls?.state?.evidence;
  const hasPrivateOutput = Boolean(project?.html_content);
  const previewUrl = `/api/builder/projects/${projectId}/preview`;
  const canSaveEvidence = useMemo(() => evidenceItems.every((item) => String(item.claim || "").trim() && String(item.source || "").trim()), [evidenceItems]);

  const saveEvidence = async () => {
    if (!canSaveEvidence) { toast.error("Each evidence item needs a claim and a source"); return; }
    setSaving(true);
    try {
      await api.put(`/builder/projects/${projectId}/evidence`, {
        items: evidenceItems.map((item) => ({
          id: item.id,
          claim: item.claim.trim(),
          source: item.source.trim(),
          status: item.status || "needs_confirmation",
          notes: item.notes || null,
        })),
      });
      toast.success("Evidence review saved");
      await load();
    } catch (error) {
      toast.error(error?.response?.status === 405 ? "Preview is read-only. Save evidence from the approved workspace after review." : (error?.response?.data?.detail || "Could not save evidence"));
    } finally {
      setSaving(false);
    }
  };

  const createVersion = async () => {
    setSaving(true);
    try {
      await api.post(`/builder/projects/${projectId}/versions`, { label: versionLabel || undefined });
      setVersionLabel("");
      toast.success("Named restore point created");
      await load();
    } catch (error) {
      toast.error(error?.response?.status === 405 ? "Preview is read-only. Versions cannot be changed here." : (error?.response?.data?.detail || "Could not create version"));
    } finally {
      setSaving(false);
    }
  };

  const restoreVersion = async (version) => {
    if (!window.confirm(`Restore “${version.label}”? Your current project will be replaced by that saved version.`)) return;
    setSaving(true);
    try {
      await api.post(`/builder/projects/${projectId}/versions/${version.id}/restore`);
      toast.success("Version restored");
      await load();
    } catch (error) {
      toast.error(error?.response?.status === 405 ? "Preview is read-only. Restore from the approved workspace after review." : (error?.response?.data?.detail || "Could not restore version"));
    } finally {
      setSaving(false);
    }
  };

  const requestReview = async () => {
    if (!evidenceConfirmed) { toast.error("Confirm that you reviewed the evidence before requesting customer review"); return; }
    setSaving(true);
    try {
      await api.post(`/builder/projects/${projectId}/release-review`, { confirm_evidence_review: true });
      toast.success("Project marked ready for customer review — it was not published");
      await load();
    } catch (error) {
      toast.error(error?.response?.status === 405 ? "Preview is read-only. Review status cannot be changed here." : (error?.response?.data?.detail || "Project is not ready for customer review"));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex min-h-[420px] items-center justify-center text-[var(--gs-muted)]"><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading project controls…</div>;
  if (!project || !controls) return <div className="mx-auto max-w-3xl rounded-3xl border bg-white p-8 text-center" style={{ borderColor: "var(--gs-border)" }}><h1 className="font-display text-2xl">Project unavailable</h1><p className="mt-2 text-sm text-[var(--gs-muted)]">This project may not belong to your account or may no longer exist.</p><Button onClick={() => navigate("/dashboard/my-getszy")} className="mt-5 bg-[#183c3c]">Back to My Getszy</Button></div>;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-8" data-testid="project-control-center">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button type="button" onClick={() => navigate("/dashboard/my-getszy")} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline"><ArrowLeft className="h-4 w-4" /> My Getszy</button>
        <Link to={`/dashboard/build?project=${encodeURIComponent(projectId)}`} className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--gs-teal)] hover:underline">Open private builder <ArrowRight className="h-4 w-4" /></Link>
      </div>

      <section className="rounded-3xl border bg-white p-6 sm:p-8" style={{ borderColor: "var(--gs-border)" }}>
        {controls.previewOnly && <div className="mb-5 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" /><p><strong>Read-only preview.</strong> You can inspect this project’s interface and available quality data here. Evidence saving, named versions, restores and review requests remain disabled until the corresponding backend release is approved and deployed.</p></div>}
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[.16em] text-[var(--gs-teal)]">Digital project control centre</div>
            <h1 className="mt-2 font-display text-3xl text-[var(--gs-ink)] sm:text-4xl">{project.name}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--gs-muted)]">{project.prompt}</p>
          </div>
          <div className="rounded-2xl bg-[#e9f5ef] px-4 py-3 text-sm text-[#24584e]">
            <div className="font-semibold">{controls.state.eligible_for_customer_review ? "Ready for customer review" : "Still in controlled review"}</div>
            <div className="mt-1 text-xs">This is not a production-ready or published status.</div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_.95fr]">
        <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><CircleDashed className="h-4 w-4" /> Mission map</div>
          <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Done, current, blocked and next.</h2>
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            {controls.state.steps.map((step) => (
              <div key={step.key} className="rounded-2xl border p-4" style={{ borderColor: step.key === controls.state.current_step ? "#183c3c" : "var(--gs-border)", background: step.key === controls.state.current_step ? "#f0f8f5" : "white" }}>
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold text-sm text-[var(--gs-ink)]">{step.label}</div>
                  <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${STATUS_STYLE[step.status] || STATUS_STYLE.not_started}`}>{step.status.replaceAll("_", " ")}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-[var(--gs-muted)]">{step.detail}</p>
              </div>
            ))}
          </div>
        </div>

        <aside className="rounded-3xl border bg-[#fffdf9] p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><ClipboardCheck className="h-4 w-4" /> Quality gate</div>
          <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Evidence, not a beauty score.</h2>
          <div className="mt-5 space-y-3">
            <div className="rounded-2xl border bg-white p-4" style={{ borderColor: "var(--gs-border)" }}><div className="text-xs text-[var(--gs-muted)]">Preflight status</div><div className="mt-1 font-semibold capitalize text-[var(--gs-ink)]">{String(quality.status || "not run").replaceAll("_", " ")}</div><div className="mt-1 text-xs text-[var(--gs-muted)]">Required checks: {quality.required_checks_passed ?? "—"} / {quality.required_checks_total ?? "—"}</div></div>
            <div className="rounded-2xl border bg-white p-4" style={{ borderColor: "var(--gs-border)" }}><div className="text-xs text-[var(--gs-muted)]">Evidence review</div><div className="mt-1 font-semibold text-[var(--gs-ink)]">{summary.approved} approved · {summary.needs_confirmation} needs confirmation</div><div className="mt-1 text-xs text-[var(--gs-muted)]">{summary.has_blockers ? "Blocked or expired evidence needs attention." : "No blocked or expired evidence recorded."}</div></div>
            <div className="rounded-2xl bg-[#183c3c] p-4 text-white"><div className="text-xs text-white/70">Release truth</div><div className="mt-1 font-semibold">No automatic publishing.</div><p className="mt-1 text-xs leading-5 text-white/75">A successful preflight only means the observable checks passed. A separate approval and release process is still required.</p></div>
          </div>
        </aside>
      </section>

      <section className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }} data-testid="customer-build-output">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><Eye className="h-4 w-4" /> What you can see and do now</div>
            <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Your work never disappears behind “building”.</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--gs-muted)]">This view uses the project and quality information that actually exists. It does not invent a progress percentage or claim that a draft is finished when it is not.</p>
          </div>
          <Link to={`/dashboard/build?project=${encodeURIComponent(projectId)}`} className="inline-flex items-center gap-1 rounded-xl border px-3 py-2 text-sm font-semibold text-[var(--gs-teal)] hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}>Open builder <ArrowRight className="h-4 w-4" /></Link>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}><div className="text-xs text-[var(--gs-muted)]">Your request</div><div className="mt-2 text-sm font-semibold text-[var(--gs-ink)]">{project.name}</div><p className="mt-2 line-clamp-3 text-xs leading-5 text-[var(--gs-muted)]">{project.prompt}</p></div>
          <div className="rounded-2xl border p-4" style={{ borderColor: hasPrivateOutput ? "#9ed2c3" : "var(--gs-border)", background: hasPrivateOutput ? "#f0f8f5" : "var(--gs-surface)" }}><div className="text-xs text-[var(--gs-muted)]">Build result</div><div className="mt-2 flex items-center gap-2 text-sm font-semibold text-[var(--gs-ink)]">{hasPrivateOutput ? <CheckCircle2 className="h-4 w-4 text-emerald-700" /> : <CircleDashed className="h-4 w-4 text-sky-700" />}{hasPrivateOutput ? "Private draft ready" : "No private draft yet"}</div><p className="mt-2 text-xs leading-5 text-[var(--gs-muted)]">{hasPrivateOutput ? "A completed draft is available below for your own review. It is not public or deployed." : "Complete the current build step first. Getszy will show the draft here only after the server has created it."}</p></div>
          <div className="rounded-2xl border p-4" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface)" }}><div className="text-xs text-[var(--gs-muted)]">Your next action</div><div className="mt-2 text-sm font-semibold text-[var(--gs-ink)]">{hasPrivateOutput ? "Review on each device" : "Complete the active mission step"}</div><p className="mt-2 text-xs leading-5 text-[var(--gs-muted)]">{hasPrivateOutput ? "Check brand accuracy, facts, pages, and the mobile layout before requesting review." : "Use the Mission map above to see what is current, blocked, done, and next."}</p></div>
        </div>

        {hasPrivateOutput ? (
          <div className="mt-5 overflow-hidden rounded-2xl border" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>
            <div className="flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between" style={{ borderColor: "var(--gs-border)", background: "white" }}>
              <div><div className="flex items-center gap-2"><span className="rounded-full bg-[#e7f4ef] px-2.5 py-1 text-[11px] font-bold text-[#216b59]">PRIVATE PREVIEW</span><span className="text-xs font-medium text-[var(--gs-muted)]">Not published</span></div><p className="mt-1 text-xs text-[var(--gs-muted)]">This is the actual finished draft for this project—not a sample image.</p></div>
              <div className="flex flex-wrap items-center gap-1.5">
                {[["desktop", "Desktop", Laptop], ["tablet", "Tablet", Tablet], ["mobile", "Mobile", Smartphone]].map(([id, label, DeviceIcon]) => <Button key={id} type="button" size="sm" variant={previewDevice === id ? "default" : "outline"} onClick={() => setPreviewDevice(id)} className={previewDevice === id ? "bg-[#183c3c] text-white hover:bg-[#102f2f]" : ""}><DeviceIcon className="mr-1.5 h-3.5 w-3.5" />{label}</Button>)}
                <a href={previewUrl} target="_blank" rel="noreferrer" className="inline-flex h-8 items-center gap-1 rounded-md border px-2 text-xs font-semibold text-[var(--gs-teal)] hover:bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}><ArrowRight className="h-3.5 w-3.5" />Open</a>
              </div>
            </div>
            <div className="overflow-auto p-4"><div className={`mx-auto overflow-hidden rounded-xl border bg-white ${previewDevice === "mobile" ? "h-[680px] max-w-[390px]" : previewDevice === "tablet" ? "h-[620px] max-w-[768px]" : "h-[560px] w-full"}`} style={{ borderColor: "var(--gs-border)" }}><iframe src={previewUrl} className="h-full w-full" title={`Private preview of ${project.name}`} data-testid="customer-project-preview" /></div></div>
            <div className="flex items-center gap-2 border-t px-4 py-3 text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)", background: "white" }}><ShieldCheck className="h-4 w-4 text-emerald-700" />Private preview only. Review is required before any customer-approved release; previewing never publishes.</div>
          </div>
        ) : (
          <div className="mt-5 rounded-2xl border border-dashed p-5 text-sm text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>There is no private draft to preview yet. When a build completes, the finished work, device preview controls, quality status, and review next step will appear here.</div>
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
        <div className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><ShieldCheck className="h-4 w-4" /> Evidence & claims vault</div><h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Only reviewed facts can support public claims.</h2><p className="mt-2 text-sm leading-6 text-[var(--gs-muted)]">Record the source and your review state. This is a customer control; it does not replace legal or product verification.</p></div><Button type="button" variant="outline" onClick={() => setEvidenceItems((items) => [...items, { id: crypto.randomUUID(), claim: "", source: "", status: "needs_confirmation", notes: "" }])}><Plus className="mr-2 h-4 w-4" /> Add evidence</Button></div>
          <div className="mt-5 space-y-3">
            {evidenceItems.length === 0 ? <div className="rounded-2xl border border-dashed p-5 text-sm text-[var(--gs-muted)]">No evidence has been recorded for this project. Add a factual claim only when you can name its source.</div> : evidenceItems.map((item, index) => (
              <div key={item.id || index} className="rounded-2xl border p-4" style={{ borderColor: "var(--gs-border)" }}>
                <div className="grid gap-3 md:grid-cols-[1.15fr_1fr_170px_auto] md:items-end">
                  <label className="block text-xs font-semibold text-[var(--gs-muted)]">Claim<input value={item.claim || ""} onChange={(event) => setEvidenceItems((items) => items.map((value, itemIndex) => itemIndex === index ? { ...value, claim: event.target.value } : value))} placeholder="e.g. Starting at ₹999" className="mt-1.5 w-full rounded-lg border px-3 py-2 text-sm text-[var(--gs-ink)]" style={{ borderColor: "var(--gs-border)" }} /></label>
                  <label className="block text-xs font-semibold text-[var(--gs-muted)]">Source<input value={item.source || ""} onChange={(event) => setEvidenceItems((items) => items.map((value, itemIndex) => itemIndex === index ? { ...value, source: event.target.value } : value))} placeholder="Catalog, policy or approved record" className="mt-1.5 w-full rounded-lg border px-3 py-2 text-sm text-[var(--gs-ink)]" style={{ borderColor: "var(--gs-border)" }} /></label>
                  <label className="block text-xs font-semibold text-[var(--gs-muted)]">Review state<select value={item.status || "needs_confirmation"} onChange={(event) => setEvidenceItems((items) => items.map((value, itemIndex) => itemIndex === index ? { ...value, status: event.target.value } : value))} className="mt-1.5 w-full rounded-lg border bg-white px-3 py-2 text-sm text-[var(--gs-ink)]" style={{ borderColor: "var(--gs-border)" }}><option value="needs_confirmation">Needs confirmation</option><option value="approved">Approved</option><option value="blocked">Blocked</option><option value="expired">Expired</option></select></label>
                  <button type="button" onClick={() => setEvidenceItems((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="rounded-lg px-2 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50">Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-end"><Button type="button" disabled={saving || !canSaveEvidence} onClick={saveEvidence} className="bg-[#183c3c] hover:bg-[#102f2f]"><Save className="mr-2 h-4 w-4" /> Save evidence review</Button></div>
        </div>

        <aside className="space-y-4">
          <section className="rounded-3xl border bg-white p-5 sm:p-6" style={{ borderColor: "var(--gs-border)" }}>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[var(--gs-teal)]"><History className="h-4 w-4" /> Time machine</div>
            <h2 className="mt-2 font-display text-2xl text-[var(--gs-ink)]">Named restore points.</h2>
            <div className="mt-4 flex gap-2"><input value={versionLabel} onChange={(event) => setVersionLabel(event.target.value)} placeholder="e.g. Approved hero copy" className="min-w-0 flex-1 rounded-xl border px-3 py-2 text-sm" style={{ borderColor: "var(--gs-border)" }} /><Button type="button" disabled={saving} onClick={createVersion} variant="outline">Save</Button></div>
            <div className="mt-4 space-y-2">{controls.versions.length === 0 ? <p className="rounded-xl bg-[var(--gs-surface-2)] p-3 text-sm text-[var(--gs-muted)]">No named restore point yet.</p> : controls.versions.map((version) => <div key={version.id} className="flex items-center gap-3 rounded-xl border p-3" style={{ borderColor: "var(--gs-border)" }}><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{version.label}</div><div className="mt-1 text-xs text-[var(--gs-muted)]">{formatDate(version.created_at)}</div></div><button type="button" disabled={saving} onClick={() => restoreVersion(version)} className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--gs-teal)] hover:underline"><RotateCcw className="h-3.5 w-3.5" /> Restore</button></div>)}</div>
          </section>

          <section className="rounded-3xl border bg-[#e9f5ef] p-5 sm:p-6" style={{ borderColor: "#b8dace" }}>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-[#216b59]"><FileCheck2 className="h-4 w-4" /> Customer review</div>
            <h2 className="mt-2 font-display text-2xl text-[#183c3c]">Ask for review only when evidence is ready.</h2>
            <label className="mt-4 flex gap-2 text-sm leading-5 text-[#24584e]"><input type="checkbox" checked={evidenceConfirmed} onChange={(event) => setEvidenceConfirmed(event.target.checked)} className="mt-1 h-4 w-4" /> I reviewed the evidence and understand this does not publish the project.</label>
            <Button type="button" disabled={saving || !controls.state.eligible_for_customer_review || !evidenceConfirmed} onClick={requestReview} className="mt-4 w-full bg-[#183c3c] hover:bg-[#102f2f]">Request customer review</Button>
            {!controls.state.eligible_for_customer_review && <p className="mt-3 text-xs leading-5 text-[#39685f]">Complete the Founder Brief, resolve evidence blockers and pass the observable quality checks first.</p>}
          </section>
        </aside>
      </section>
    </div>
  );
}
