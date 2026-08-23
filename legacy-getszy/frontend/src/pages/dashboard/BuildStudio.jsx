import { Eye, ShieldCheck, Wand2 } from "lucide-react";
import BuildStudio from "@/pages/admin/BuildStudio";
import DashboardPageFrame from "@/components/dashboard/DashboardPageFrame";

export default function DashboardBuild() {
  return (
    <DashboardPageFrame
      eyebrow="Build"
      title="Turn a business idea into a working product"
      description="Create web apps, creator systems, AI agents, and starter products in one guided workspace. Every web build stays private until you review its preview."
      icon={Wand2}
      metrics={[
        { label: "private drafts", value: "100%" },
        { label: "review before publish", value: "Always" },
      ]}
      hint="Start with a category, describe the outcome you want, then open the private preview before downloading or publishing anything."
      actions={
        <div className="inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)", background: "var(--gs-surface-2)" }}>
          <Eye className="h-4 w-4 text-[var(--gs-teal)]" /> Preview first
          <span className="h-3 w-px bg-[var(--gs-border)]" />
          <ShieldCheck className="h-4 w-4 text-emerald-600" /> Private drafts
        </div>
      }
    >
      <BuildStudio embedded />
    </DashboardPageFrame>
  );
}
