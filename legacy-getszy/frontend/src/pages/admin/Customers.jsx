import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Users, Search, RefreshCw, Mail, Calendar, ShoppingCart,
  Zap, TrendingUp, Crown, UserCheck, ChevronDown, ChevronUp,
  Copy, Gift
} from "lucide-react";
import { toast } from "sonner";

const PLAN_COLORS = {
  free:     "bg-slate-100 text-slate-700",
  lite:     "bg-blue-100 text-blue-700",
  pro:      "bg-violet-100 text-violet-700",
  ultra:    "bg-amber-100 text-amber-700",
  founder:  "bg-rose-100 text-rose-700",
};

function PlanBadge({ plan }) {
  const p = (plan || "free").toLowerCase();
  return (
    <Badge className={`${PLAN_COLORS[p] || PLAN_COLORS.free} text-[10px] capitalize`}>
      {p === "ultra" ? "⚡ " : p === "founder" ? "👑 " : ""}
      {plan || "Free"}
    </Badge>
  );
}

export default function AdminCustomers() {
  const [items,    setItems]    = useState([]);
  const [search,   setSearch]   = useState("");
  const [loading,  setLoading]  = useState(true);
  const [sort,     setSort]     = useState({ key: "created_at", dir: -1 });
  const [selected, setSelected] = useState(null);
  const [grantAmt, setGrantAmt] = useState(50);
  const [grantBusy, setGrantBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/customers?limit=200");
      setItems(Array.isArray(r.data) ? r.data : (r.data.items || []));
    } catch (e) {
      toast.error("Customers load nahi ho rahe — backend check karo");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(u =>
    !search ||
    (u.name || "").toLowerCase().includes(search.toLowerCase()) ||
    (u.email || "").toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const v1 = a[sort.key] ?? 0, v2 = b[sort.key] ?? 0;
    return sort.dir * (v1 > v2 ? 1 : v1 < v2 ? -1 : 0);
  });

  const toggleSort = (key) => setSort(s => ({
    key, dir: s.key === key ? -s.dir : -1
  }));

  const SortIcon = ({ k }) => sort.key === k
    ? (sort.dir === -1 ? <ChevronDown className="h-3 w-3 inline ml-0.5"/> : <ChevronUp className="h-3 w-3 inline ml-0.5"/>)
    : null;

  const grantCredits = async () => {
    if (!selected || !grantAmt) return;
    setGrantBusy(true);
    try {
      await api.post("/credits/admin/grant", { email: selected.email, amount: Number(grantAmt) });
      toast.success(`${grantAmt} credits granted to ${selected.email}`);
      setSelected(null);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Grant failed");
    } finally { setGrantBusy(false); }
  };

  // Stat cards
  const totalRevenue = items.reduce((s, u) => s + (u.lifetime_value || 0), 0);
  const paidUsers    = items.filter(u => (u.lifetime_value || 0) > 0).length;
  const avgLTV       = paidUsers ? Math.round(totalRevenue / paidUsers) : 0;

  return (
    <div className="space-y-5" data-testid="admin-customers-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Users className="h-7 w-7 text-[var(--gs-teal)]"/>Customers
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{items.length} total registered users</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--gs-muted)]"/>
            <Input className="pl-8 h-9 w-52 text-xs" placeholder="Name ya email…"
              value={search} onChange={e => setSearch(e.target.value)}/>
          </div>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: Users,    label: "Total Users",   value: items.length,      color: "text-[var(--gs-teal)]", bg: "bg-[var(--gs-teal-soft)]" },
          { icon: Crown,    label: "Paid Users",    value: paidUsers,         color: "text-violet-600",       bg: "bg-violet-50" },
          { icon: TrendingUp,label: "Total Revenue",value: fmtINR(totalRevenue), color: "text-emerald-600",  bg: "bg-emerald-50" },
          { icon: UserCheck, label: "Avg LTV",      value: fmtINR(avgLTV),    color: "text-amber-600",        bg: "bg-amber-50" },
        ].map(s => (
          <Card key={s.label} className="p-4 flex items-center gap-3">
            <div className={`h-9 w-9 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}>
              <s.icon className={`h-4 w-4 ${s.color}`}/>
            </div>
            <div>
              <div className="font-display text-xl leading-none">{loading ? "…" : s.value}</div>
              <div className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</div>
            </div>
          </Card>
        ))}
      </div>

      {/* Table */}
      <Card className="overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead className="text-left text-xs uppercase tracking-wider text-[var(--gs-muted)] border-b"
            style={{ borderColor: "var(--gs-border)" }}>
            <tr>
              <th className="p-4">
                <button className="flex items-center gap-0.5 hover:text-[var(--gs-ink)]" onClick={() => toggleSort("name")}>
                  Customer <SortIcon k="name"/>
                </button>
              </th>
              <th className="p-4">Plan</th>
              <th className="p-4">
                <button className="flex items-center gap-0.5 hover:text-[var(--gs-ink)]" onClick={() => toggleSort("credits")}>
                  Credits <SortIcon k="credits"/>
                </button>
              </th>
              <th className="p-4">
                <button className="flex items-center gap-0.5 hover:text-[var(--gs-ink)]" onClick={() => toggleSort("orders_count")}>
                  Orders <SortIcon k="orders_count"/>
                </button>
              </th>
              <th className="p-4">
                <button className="flex items-center gap-0.5 hover:text-[var(--gs-ink)]" onClick={() => toggleSort("lifetime_value")}>
                  LTV <SortIcon k="lifetime_value"/>
                </button>
              </th>
              <th className="p-4 hidden lg:table-cell">
                <button className="flex items-center gap-0.5 hover:text-[var(--gs-ink)]" onClick={() => toggleSort("created_at")}>
                  Joined <SortIcon k="created_at"/>
                </button>
              </th>
              <th className="p-4 w-20"/>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="py-10 text-center">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto text-[var(--gs-muted)]"/>
              </td></tr>
            ) : sorted.length === 0 ? (
              <tr><td colSpan={7} className="py-10 text-center text-[var(--gs-muted)] text-sm">
                {search ? "No matching customers" : "No customers yet"}
              </td></tr>
            ) : sorted.map(u => (
              <tr key={u.id} className="border-b last:border-0 hover:bg-[var(--gs-surface-2)] transition-colors"
                style={{ borderColor: "var(--gs-border)" }}>
                <td className="p-4">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-full grid place-items-center text-white text-xs font-bold flex-shrink-0"
                      style={{ background: "var(--gs-teal)" }}>
                      {(u.name || u.email || "?")[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="font-semibold">{u.name || "—"}</div>
                      <div className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1">
                        <Mail className="h-2.5 w-2.5"/>{u.email}
                        <button onClick={() => { navigator.clipboard.writeText(u.email); toast.success("Email copied"); }}
                          className="ml-1 hover:text-[var(--gs-teal)] transition-colors">
                          <Copy className="h-2.5 w-2.5"/>
                        </button>
                      </div>
                    </div>
                  </div>
                </td>
                <td className="p-4"><PlanBadge plan={u.plan || u.subscription}/></td>
                <td className="p-4">
                  <div className="flex items-center gap-1 font-semibold text-[var(--gs-teal)]">
                    <Zap className="h-3 w-3"/>
                    {u.credits ?? "—"}
                  </div>
                </td>
                <td className="p-4">
                  <Badge variant="outline" className="text-[10px]">
                    <ShoppingCart className="h-2.5 w-2.5 mr-1"/>{u.orders_count ?? 0}
                  </Badge>
                </td>
                <td className="p-4 font-semibold text-emerald-700">{fmtINR(u.lifetime_value || 0)}</td>
                <td className="p-4 hidden lg:table-cell text-xs text-[var(--gs-muted)]">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-2.5 w-2.5"/>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "2-digit" }) : "—"}
                  </span>
                </td>
                <td className="p-4">
                  <Button size="sm" variant="outline" className="text-xs h-7 px-2"
                    onClick={() => { setSelected(u); setGrantAmt(50); }}>
                    <Gift className="h-3 w-3 mr-1"/>Grant
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Grant Credits Dialog */}
      <Dialog open={!!selected} onOpenChange={o => !o && setSelected(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-[var(--gs-teal)]"/>Grant Credits
            </DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-[var(--gs-surface-2)] text-sm">
                <div className="font-semibold">{selected.name || "Unknown"}</div>
                <div className="text-[var(--gs-muted)] text-xs">{selected.email}</div>
                <div className="mt-1 text-xs">Current credits: <span className="font-bold text-[var(--gs-teal)]">{selected.credits ?? 0}</span></div>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)] mb-1 block">Credits grant karne hain</label>
                <div className="flex gap-2">
                  <Input type="number" value={grantAmt} onChange={e => setGrantAmt(Number(e.target.value))} className="flex-1" min={1} max={9999}/>
                  <div className="flex gap-1">
                    {[25, 50, 100, 200].map(n => (
                      <button key={n} onClick={() => setGrantAmt(n)}
                        className={`text-xs px-2 py-1 rounded-lg border transition-colors ${grantAmt === n ? "bg-[var(--gs-teal)] text-white border-[var(--gs-teal)]" : "border-[var(--gs-border)] hover:bg-[var(--gs-surface-2)]"}`}>
                        +{n}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <Button onClick={grantCredits} disabled={grantBusy || !grantAmt}
                className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
                <Zap className="h-4 w-4 mr-2"/>
                {grantBusy ? "Granting…" : `Grant ${grantAmt} credits`}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
