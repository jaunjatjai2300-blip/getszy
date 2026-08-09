import { Wand2 } from "lucide-react";
import BuildStudio from "@/pages/admin/BuildStudio";

export default function DashboardBuild() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl flex items-center gap-2">
          <Wand2 className="h-7 w-7 text-[var(--gs-teal)]"/> Build Studio
        </h1>
        <p className="text-sm text-[var(--gs-muted)] mt-1">
          Build web apps, faceless channels, AI agents, mobile apps, and more — all with AI.
        </p>
      </div>
      <BuildStudio />
    </div>
  );
}
