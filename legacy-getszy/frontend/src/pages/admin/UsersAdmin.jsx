import { useEffect, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Users, Zap, Search, RefreshCw, CheckCircle2, XCircle, Mail, Calendar, ShoppingBag } from "lucide-react";
import { toast } from "sonner";

function PlanBadge({ plan }) {
  if (!plan || plan === "free") return <Badge variant="outline" className="text-[10px]">Free</Badge>;
  return <Badge className="text-[10px] bg-[var(--gs-teal)] text-white">{plan}</Badge>;
}

export default function UsersAdmin() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [grantEmail, setGrantEmail] = useState("");
  const [grantAmount, setGrantAmount] = useState(100);
  const [grantBusy, setGrantBusy] = useState(false);
  const [txEmail, setTxEmail] = useState("");
  const [txData, setTxData] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/customers");
      setUsers(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const grant = async () => {
    if (!grantEmail || !grantAmount) return;
    setGrantBusy(true);
    try {
      const r = await api.post("/credits/admin/grant", { email: grantEmail, amount: Number(grantAmount), reason: "Admin grant" });
      toast.success(`${grantAmount} credits granted to ${grantEmail}. Balance: ${r.data.credits}`);
      setGrantEmail("");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to grant credits");
    } finally { setGrantBusy(false); }
  };

  const loadTx = async () => {
    if (!txEmail) return;
    try {
      const r = await api.get(`/credits/admin/transactions?user_email=${txEmail}&limit=30`);
      setTxData(r.data);
    } catch { toast.error("User not found"); }
  };

  const filtered = users.filter(u =>
    !search || u.name?.toLowerCase().includes(search.toLowerCase()) || u.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Users</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">{users.length} total users</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? "animate-spin" : ""}`}/> Refresh
        </Button>
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all"><Users className="h-3.5 w-3.5 mr-1"/>All Users</TabsTrigger>
          <TabsTrigger value="credits"><Zap className="h-3.5 w-3.5 mr-1"/>Grant Credits</TabsTrigger>
          <TabsTrigger value="history"><ShoppingBag className="h-3.5 w-3.5 mr-1"/>Credit History</TabsTrigger>
        </TabsList>

        {/* All Users */}
        <TabsContent value="all" className="mt-4 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--gs-muted)]"/>
            <Input className="pl-9" placeholder="Name ya email se search karo…" value={search} onChange={e => setSearch(e.target.value)}/>
          </div>

          <Card className="overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="text-left text-[10px] uppercase tracking-wider text-[var(--gs-muted)] border-b bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}>
                <tr>
                  <th className="p-3">User</th>
                  <th className="p-3">Plan</th>
                  <th className="p-3">Credits</th>
                  <th className="p-3">Orders</th>
                  <th className="p-3">Lifetime Value</th>
                  <th className="p-3 hidden md:table-cell">Joined</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.id} className="border-b last:border-0 hover:bg-[var(--gs-surface-2)] transition-colors" style={{ borderColor: "var(--gs-border)" }}>
                    <td className="p-3">
                      <div className="flex items-center gap-2.5">
                        <div className="h-7 w-7 rounded-full bg-[var(--gs-teal-soft)] grid place-items-center text-[var(--gs-teal)] text-xs font-bold shrink-0">
                          {u.name?.[0]?.toUpperCase() || "?"}
                        </div>
                        <div>
                          <div className="font-semibold text-xs">{u.name}</div>
                          <div className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1">
                            <Mail className="h-2.5 w-2.5"/>{u.email}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3"><PlanBadge plan={u.plan}/></td>
                    <td className="p-3">
                      <div className="flex items-center gap-1 text-xs">
                        <Zap className="h-3 w-3 text-amber-500"/>
                        <span className="font-semibold">{u.credits ?? "—"}</span>
                      </div>
                    </td>
                    <td className="p-3"><Badge variant="outline" className="text-[10px]">{u.orders_count}</Badge></td>
                    <td className="p-3 font-semibold text-xs">{fmtINR(u.lifetime_value)}</td>
                    <td className="p-3 hidden md:table-cell text-[10px] text-[var(--gs-muted)]">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3"/>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString("en-IN") : "—"}
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={6} className="py-10 text-center text-[var(--gs-muted)] text-sm">
                    {search ? "Koi user nahi mila" : "Abhi koi users nahi hain"}
                  </td></tr>
                )}
              </tbody>
            </table>
          </Card>
        </TabsContent>

        {/* Grant Credits */}
        <TabsContent value="credits" className="mt-4">
          <Card className="p-5 max-w-md space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-5 w-5 text-amber-500"/>
              <h3 className="font-display text-lg">Grant Credits</h3>
            </div>
            <p className="text-xs text-[var(--gs-muted)]">Kisi bhi user ko manually credits do — testing ya compensation ke liye.</p>
            <div>
              <label className="text-xs text-[var(--gs-muted)]">User Email *</label>
              <Input value={grantEmail} onChange={e => setGrantEmail(e.target.value)} placeholder="user@example.com"/>
            </div>
            <div>
              <label className="text-xs text-[var(--gs-muted)]">Credits Amount *</label>
              <Input type="number" value={grantAmount} onChange={e => setGrantAmount(e.target.value)} min={1} max={10000}/>
            </div>
            <Button onClick={grant} disabled={grantBusy || !grantEmail}
              className="w-full bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {grantBusy ? "Granting…" : `Grant ${grantAmount} Credits`}
            </Button>
          </Card>
        </TabsContent>

        {/* Credit History */}
        <TabsContent value="history" className="mt-4 space-y-3">
          <div className="flex gap-2 max-w-md">
            <Input value={txEmail} onChange={e => setTxEmail(e.target.value)} placeholder="User ka email daalo…"/>
            <Button onClick={loadTx} variant="outline">Load</Button>
          </div>
          {txData.length > 0 ? (
            <Card className="overflow-x-auto">
              <table className="w-full text-xs min-w-[480px]">
                <thead className="text-left text-[10px] uppercase tracking-wider text-[var(--gs-muted)] border-b bg-[var(--gs-surface-2)]" style={{ borderColor: "var(--gs-border)" }}>
                  <tr>
                    <th className="p-3">Type</th>
                    <th className="p-3">Amount</th>
                    <th className="p-3">Reason</th>
                    <th className="p-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {txData.map((t, i) => (
                    <tr key={i} className="border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
                      <td className="p-3">
                        {t.delta > 0
                          ? <span className="text-emerald-600 flex items-center gap-1"><CheckCircle2 className="h-3 w-3"/>Credit</span>
                          : <span className="text-rose-500 flex items-center gap-1"><XCircle className="h-3 w-3"/>Debit</span>
                        }
                      </td>
                      <td className="p-3 font-semibold">{t.delta > 0 ? "+" : ""}{t.delta}</td>
                      <td className="p-3 text-[var(--gs-muted)]">{t.reason}</td>
                      <td className="p-3 text-[var(--gs-muted)]">{t.created_at ? new Date(t.created_at).toLocaleDateString("en-IN") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)] text-sm">
              Upar email daalo aur Load karo
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
