import { Badge } from "@/components/ui/badge";

const VARIANTS = {
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  error: 'bg-rose-50 text-rose-700 border-rose-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  neutral: 'bg-gray-50 text-gray-600 border-gray-200',
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  inactive: 'bg-gray-50 text-gray-500 border-gray-200',
  processing: 'bg-blue-50 text-blue-700 border-blue-200',
  shipped: 'bg-violet-50 text-violet-700 border-violet-200',
  delivered: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  cancelled: 'bg-rose-50 text-rose-700 border-rose-200',
  refunded: 'bg-orange-50 text-orange-700 border-orange-200',
};

const DOT_COLORS = {
  success: 'bg-emerald-500', warning: 'bg-amber-500', error: 'bg-rose-500',
  info: 'bg-blue-500', neutral: 'bg-gray-400', pending: 'bg-yellow-500',
  active: 'bg-emerald-500', inactive: 'bg-gray-400', processing: 'bg-blue-500',
  shipped: 'bg-violet-500', delivered: 'bg-emerald-500', cancelled: 'bg-rose-500', refunded: 'bg-orange-500',
};

export function StatusBadge({ status, variant, dot = true, size = "default" }) {
  const v = variant || status?.toLowerCase() || 'neutral';
  const cls = VARIANTS[v] || VARIANTS.neutral;
  const dotCls = DOT_COLORS[v] || DOT_COLORS.neutral;
  const sizeCls = size === 'sm' ? 'text-[9px] px-1.5 py-0' : 'text-[10px]';

  return (
    <Badge className={`${cls} border capitalize ${sizeCls}`}>
      {dot && <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotCls} mr-1`}/>}
      {status}
    </Badge>
  );
}

export function InlineStat({ label, value, icon: Icon, trend, className = "" }) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {Icon && <Icon className="h-3.5 w-3.5 text-[var(--gs-muted)]"/>}
      <span className="text-[10px] text-[var(--gs-muted)]">{label}</span>
      <span className="text-xs font-semibold">{value}</span>
      {trend != null && (
        <span className={`text-[10px] ${trend > 0 ? 'text-emerald-600' : trend < 0 ? 'text-rose-500' : 'text-[var(--gs-muted)]'}`}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>
      )}
    </div>
  );
}
