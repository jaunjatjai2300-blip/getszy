import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Search, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, Download, RefreshCw } from "lucide-react";

export default function ProdDataTable({ columns, data, searchable = true, searchPlaceholder = "Search...", pagination = 20, onRowClick, actions, title, subtitle, badge, onRefresh, onExport, emptyMsg = "No data found" }) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  const filtered = useMemo(() => {
    let items = data || [];
    if (search) {
      const q = search.toLowerCase();
      items = items.filter(row => columns.some(c => {
        const val = typeof c.accessor === 'function' ? c.accessor(row) : row[c.key];
        return String(val || '').toLowerCase().includes(q);
      }));
    }
    if (sortKey) {
      const col = columns.find(c => c.key === sortKey);
      items = [...items].sort((a, b) => {
        const va = typeof col?.accessor === 'function' ? col.accessor(a) : a[sortKey];
        const vb = typeof col?.accessor === 'function' ? col.accessor(b) : b[sortKey];
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
    }
    return items;
  }, [data, search, sortKey, sortDir, columns]);

  const totalPages = Math.ceil(filtered.length / pagination);
  const paged = filtered.slice(page * pagination, (page + 1) * pagination);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  return (
    <Card className="overflow-hidden">
      {(title || searchable || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <div className="flex items-center gap-3">
            {title && (
              <div>
                <h3 className="font-semibold text-sm">{title}</h3>
                {subtitle && <div className="text-[10px] text-[var(--gs-muted)]">{subtitle}</div>}
              </div>
            )}
            {badge && <Badge className="text-[10px]">{badge}</Badge>}
          </div>
          <div className="flex items-center gap-2">
            {onRefresh && (
              <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={onRefresh}>
                <RefreshCw className="h-3 w-3 mr-1"/>Refresh
              </Button>
            )}
            {onExport && (
              <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={onExport}>
                <Download className="h-3 w-3 mr-1"/>Export
              </Button>
            )}
            {searchable && (
              <div className="relative">
                <Search className="absolute left-2.5 top-1.5 h-3 w-3 text-[var(--gs-muted)]"/>
                <Input className="pl-7 h-7 text-xs w-48" placeholder={searchPlaceholder} value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}/>
              </div>
            )}
          </div>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-[10px] uppercase tracking-wider text-[var(--gs-muted)] bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}>
            <tr>
              {columns.map(col => (
                <th key={col.key} className="px-4 py-2.5 font-semibold cursor-pointer hover:text-[var(--gs-ink)] select-none" onClick={() => col.sortable !== false && toggleSort(col.key)}>
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.sortable !== false && (
                      sortKey === col.key ? (sortDir === 'asc' ? <ArrowUp className="h-3 w-3"/> : <ArrowDown className="h-3 w-3"/>) : <ArrowUpDown className="h-3 w-3 opacity-30"/>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, i) => (
              <tr key={row.id || i} className={`border-t transition-colors ${onRowClick ? 'cursor-pointer hover:bg-[var(--gs-surface-2)]' : 'hover:bg-[var(--gs-surface-2)]/50'}`} style={{ borderColor: "var(--gs-border)" }} onClick={() => onRowClick?.(row)}>
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-2.5 text-xs">
                    {col.render ? col.render(row) : (typeof col.accessor === 'function' ? col.accessor(row) : row[col.key]) ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
            {paged.length === 0 && (
              <tr><td colSpan={columns.length} className="py-12 text-center text-[var(--gs-muted)] text-sm">{emptyMsg}</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-2 border-t text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>
          <span>{filtered.length} total rows</span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="h-3 w-3"/>
            </Button>
            <span>{page + 1} / {totalPages}</span>
            <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="h-3 w-3"/>
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
