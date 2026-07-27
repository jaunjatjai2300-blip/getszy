import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function SectionHeader({ title, subtitle, icon: Icon, onRefresh, loading, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal-soft)] grid place-items-center">
            <Icon className="h-5 w-5 text-[var(--gs-teal)]"/>
          </div>
        )}
        <div>
          <h1 className="font-display text-2xl md:text-3xl">{title}</h1>
          {subtitle && <p className="text-sm text-[var(--gs-muted)] mt-0.5">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {children}
        {onRefresh && (
          <Button variant="outline" size="sm" className="h-8" onClick={onRefresh}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`}/>
          </Button>
        )}
      </div>
    </div>
  );
}
