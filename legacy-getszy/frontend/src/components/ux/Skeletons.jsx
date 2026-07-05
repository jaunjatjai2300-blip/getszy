import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";

export function CardSkeleton({ count = 3 }) {
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="card-skeleton">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="p-4 space-y-3">
          <Skeleton className="h-4 w-3/4"/>
          <Skeleton className="h-3 w-1/2"/>
          <Skeleton className="h-24 w-full"/>
        </Card>
      ))}
    </div>
  );
}

export function ListSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-2" data-testid="list-skeleton">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton className="h-9 w-9 rounded-xl"/>
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-3/4"/>
            <Skeleton className="h-2 w-1/2"/>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ChatSkeleton() {
  return (
    <div className="space-y-3" data-testid="chat-skeleton">
      <div className="flex justify-end"><Skeleton className="h-10 w-64 rounded-2xl"/></div>
      <div className="flex justify-start"><Skeleton className="h-16 w-80 rounded-2xl"/></div>
      <div className="flex justify-end"><Skeleton className="h-8 w-40 rounded-2xl"/></div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, subtitle, actionLabel, onAction, testid }) {
  return (
    <div className="text-center py-14 px-6" data-testid={testid || "empty-state"}>
      {Icon && (
        <div className="h-14 w-14 mx-auto rounded-2xl bg-[var(--gs-teal)]/10 grid place-items-center mb-4">
          <Icon className="h-7 w-7 text-[var(--gs-teal)]"/>
        </div>
      )}
      <div className="font-display text-xl">{title}</div>
      {subtitle && <div className="text-sm text-[var(--gs-muted)] mt-2 max-w-md mx-auto">{subtitle}</div>}
      {actionLabel && onAction && (
        <button onClick={onAction} className="mt-5 px-5 py-2.5 rounded-xl bg-[var(--gs-teal)] text-white text-sm font-semibold hover:opacity-90" data-testid="empty-state-cta">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
