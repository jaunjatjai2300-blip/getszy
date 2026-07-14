import { useEffect, useState, useCallback } from "react";
import { api, fmtINR } from "@/lib/api";
import {
  Users, Briefcase, Package, ShoppingCart, Calendar, Clock,
  CheckCircle2, XCircle, AlertTriangle, TrendingUp, ArrowUpDown,
  RefreshCw, Plus, Search, Eye, Building2, UserCheck, FileText,
  Truck, BarChart3, DollarSign, MapPin, Star
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

function KpiCard({ label, value, sub, icon: Icon, color = "bg-[var(--gs-teal-soft)]", iconColor = "text-[var(--gs-teal)]" }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{label}</div>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${color}`}>
          <Icon className={`h-4 w-4 ${iconColor}`}/>
        </div>
      </div>
      <div className="text-2xl font-display" style={{ fontVariantNumeric: "tabular-nums" }}>{value ?? "—"}</div>
      {sub && <div className="text-[11px] text-[var(--gs-muted)]">{sub}</div>}
    </Card>
  );
}

function StatusBadge({ status }) {
  const map = {
    active: "bg-emerald-100 text-emerald-700",
    inactive: "bg-slate-100 text-slate-600",
    pending: "bg-amber-100 text-amber-700",
    approved: "bg-emerald-100 text-emerald-700",
    rejected: "bg-rose-100 text-rose-700",
    won: "bg-emerald-100 text-emerald-700",
    lost: "bg-rose-100 text-rose-700",
    lead: "bg-blue-100 text-blue-700",
    qualified: "bg-violet-100 text-violet-700",
    proposal: "bg-amber-100 text-amber-700",
    delivered: "bg-blue-100 text-blue-700",
    partial: "bg-orange-100 text-orange-700",
  };
  return <Badge className={`text-[10px] capitalize ${map[status] || "bg-slate-100 text-slate-600"}`}>{status}</Badge>;
}

function KanbanColumn({ title, deals, color }) {
  return (
    <div className="flex-1 min-w-[200px]">
      <div className="flex items-center gap-2 mb-2">
        <div className={`h-2 w-2 rounded-full ${color}`}/>
        <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{title}</span>
        <Badge variant="outline" className="text-[9px]">{deals.length}</Badge>
      </div>
      <div className="space-y-2">
        {deals.map((d, i) => (
          <Card key={d.id || i} className="p-3 hover:shadow-md transition-all cursor-pointer">
            <div className="font-semibold text-xs">{d.name || d.title}</div>
            <div className="text-[11px] text-[var(--gs-muted)] mt-0.5">{d.contact || d.company}</div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs font-semibold text-[var(--gs-teal)]">{fmtINR(d.value)}</span>
              <Badge variant="outline" className="text-[8px]">{d.stage}</Badge>
            </div>
          </Card>
        ))}
        {deals.length === 0 && (
          <div className="text-center py-4 text-[var(--gs-muted)] text-xs">No deals</div>
        )}
      </div>
    </div>
  );
}

/* ========== CRM TAB ========== */
function CRMTab() {
  const [contacts, setContacts] = useState([]);
  const [deals, setDeals] = useState([]);
  const [activities, setActivities] = useState([]);
  const [crmStats, setCrmStats] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get("/admin/business-builders/crm/contacts").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/crm/deals").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/crm/activities").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/crm/stats").catch(() => ({ data: {} })),
    ]).then(([c, d, a, s]) => {
      setContacts(c.data?.items || []);
      setDeals(d.data?.items || []);
      setActivities(a.data?.items || []);
      setCrmStats(s.data);
    });
  }, []);

  const cs = crmStats || {};
  const leadDeals = deals.filter(d => d.stage === "lead");
  const qualifiedDeals = deals.filter(d => d.stage === "qualified");
  const proposalDeals = deals.filter(d => d.stage === "proposal");
  const wonDeals = deals.filter(d => d.stage === "won");
  const lostDeals = deals.filter(d => d.stage === "lost");

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Pipeline Value" value={fmtINR(cs.pipeline_value)} sub="Total pipeline" icon={DollarSign}/>
        <KpiCard label="Conversion Rate" value={`${cs.conversion_rate ?? 0}%`} sub="Win rate" icon={TrendingUp} color="bg-emerald-50" iconColor="text-emerald-600"/>
        <KpiCard label="Deals This Month" value={cs.deals_this_month ?? deals.length} sub="Active deals" icon={Briefcase} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="Total Contacts" value={contacts.length} sub="All contacts" icon={Users} color="bg-violet-50" iconColor="text-violet-600"/>
      </div>

      {/* Deal Pipeline Kanban */}
      <Card className="p-4">
        <h3 className="font-semibold text-sm mb-3">Deal Pipeline</h3>
        <div className="flex gap-3 overflow-x-auto pb-2">
          <KanbanColumn title="Lead" deals={leadDeals} color="bg-blue-500"/>
          <KanbanColumn title="Qualified" deals={qualifiedDeals} color="bg-violet-500"/>
          <KanbanColumn title="Proposal" deals={proposalDeals} color="bg-amber-500"/>
          <KanbanColumn title="Won" deals={wonDeals} color="bg-emerald-500"/>
          <KanbanColumn title="Lost" deals={lostDeals} color="bg-rose-500"/>
        </div>
      </Card>

      {/* Contacts Table */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Contacts</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Name</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Email</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Company</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {contacts.map((c, i) => (
                <tr key={c.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{c.name}</td>
                  <td className="p-3 text-[var(--gs-muted)]">{c.email}</td>
                  <td className="p-3">{c.company || "—"}</td>
                  <td className="p-3"><StatusBadge status={c.status}/></td>
                </tr>
              ))}
              {contacts.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No contacts yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Activity Log */}
      <Card className="p-4">
        <h3 className="font-semibold text-sm mb-3">Activity Log</h3>
        <div className="space-y-2">
          {activities.map((a, i) => (
            <div key={a.id || i} className="flex items-center gap-3 p-2.5 rounded-lg bg-[var(--gs-surface-2)] text-xs">
              <div className="h-6 w-6 rounded-full bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                <ActivityIcon type={a.type}/>
              </div>
              <div className="flex-1 min-w-0">
                <span className="font-medium">{a.description}</span>
                {a.contact_name && <span className="text-[var(--gs-muted)]"> — {a.contact_name}</span>}
              </div>
              <span className="text-[var(--gs-muted)] flex-shrink-0">{a.timestamp ? new Date(a.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : ""}</span>
            </div>
          ))}
          {activities.length === 0 && (
            <div className="text-center py-4 text-[var(--gs-muted)] text-sm">No activity yet</div>
          )}
        </div>
      </Card>
    </div>
  );
}

function ActivityIcon({ type }) {
  const map = { call: <DollarSign className="h-3 w-3 text-blue-600"/>, email: <FileText className="h-3 w-3 text-emerald-600"/>, meeting: <Users className="h-3 w-3 text-violet-600"/>, note: <Star className="h-3 w-3 text-amber-600"/> };
  return map[type] || <Clock className="h-3 w-3 text-[var(--gs-muted)]"/>;
}

/* ========== ERP TAB ========== */
function ERPTab() {
  const [warehouses, setWarehouses] = useState([]);
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [stockLevels, setStockLevels] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [vendors, setVendors] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get("/admin/business-builders/erp/warehouses").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/erp/purchase-orders").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/erp/stock-levels").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/erp/low-stock").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/erp/vendors").catch(() => ({ data: { items: [] } })),
    ]).then(([w, po, sl, ls, v]) => {
      setWarehouses(w.data?.items || []);
      setPurchaseOrders(po.data?.items || []);
      setStockLevels(sl.data?.items || []);
      setLowStock(ls.data?.items || []);
      setVendors(v.data?.items || []);
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Warehouses" value={warehouses.length} icon={Building2}/>
        <KpiCard label="Purchase Orders" value={purchaseOrders.length} sub="All orders" icon={FileText} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="Low Stock Items" value={lowStock.length} sub="Alerts" icon={AlertTriangle} color="bg-rose-50" iconColor="text-rose-600"/>
        <KpiCard label="Vendors" value={vendors.length} sub="Active vendors" icon={Truck} color="bg-violet-50" iconColor="text-violet-600"/>
      </div>

      {/* Warehouse Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {warehouses.map((w, i) => (
          <Card key={w.id || i} className="p-4">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-sm">{w.name}</h3>
              <Badge variant="outline" className="text-[10px]">{w.location}</Badge>
            </div>
            <div className="space-y-1 text-xs text-[var(--gs-muted)]">
              <div>Capacity: {w.capacity ?? "—"}</div>
              <div>Items: {w.items_count ?? 0}</div>
            </div>
          </Card>
        ))}
      </div>

      {/* Purchase Orders */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Purchase Orders</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">PO #</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Vendor</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Amount</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {purchaseOrders.map((po, i) => (
                <tr key={po.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-mono text-xs font-semibold">#{po.po_number}</td>
                  <td className="p-3">{po.vendor}</td>
                  <td className="p-3 font-semibold">{fmtINR(po.amount)}</td>
                  <td className="p-3"><StatusBadge status={po.status}/></td>
                  <td className="p-3 text-xs text-[var(--gs-muted)]">{po.date ? new Date(po.date).toLocaleDateString("en-IN") : "—"}</td>
                </tr>
              ))}
              {purchaseOrders.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No purchase orders</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Stock Levels */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Stock Levels</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Product</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Warehouse</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Quantity</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Reorder Level</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {stockLevels.map((sl, i) => {
                const isLow = (sl.quantity || 0) <= (sl.reorder_level || 0);
                return (
                  <tr key={sl.id || i} className={`hover:bg-[var(--gs-surface-2)] ${isLow ? "bg-rose-50" : ""}`}>
                    <td className="p-3 font-semibold">{sl.product_name}</td>
                    <td className="p-3 text-[var(--gs-muted)]">{sl.warehouse}</td>
                    <td className="p-3 font-semibold">{sl.quantity}</td>
                    <td className="p-3">{sl.reorder_level}</td>
                    <td className="p-3">{isLow ? <Badge className="bg-rose-100 text-rose-700 text-[10px]">Low Stock</Badge> : <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">OK</Badge>}</td>
                  </tr>
                );
              })}
              {stockLevels.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No stock data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Vendors */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Vendors</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Name</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Contact</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Email</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {vendors.map((v, i) => (
                <tr key={v.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{v.name}</td>
                  <td className="p-3 text-[var(--gs-muted)]">{v.contact || "—"}</td>
                  <td className="p-3 text-[var(--gs-muted)]">{v.email || "—"}</td>
                  <td className="p-3"><StatusBadge status={v.status}/></td>
                </tr>
              ))}
              {vendors.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No vendors</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========== HRMS TAB ========== */
function HRMSTab() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [payroll, setPayroll] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get("/admin/business-builders/hrms/employees").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/hrms/departments").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/hrms/attendance").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/hrms/leave-requests").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/hrms/payroll").catch(() => ({ data: { items: [] } })),
    ]).then(([e, d, a, l, p]) => {
      setEmployees(e.data?.items || []);
      setDepartments(d.data?.items || []);
      setAttendance(a.data?.items || []);
      setLeaveRequests(l.data?.items || []);
      setPayroll(p.data?.items || []);
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Employees" value={employees.length} sub="Total staff" icon={Users}/>
        <KpiCard label="Departments" value={departments.length} sub="Active" icon={Building2} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="Today Attendance" value={attendance.filter(a => a.present).length} sub={`of ${employees.length}`} icon={UserCheck} color="bg-emerald-50" iconColor="text-emerald-600"/>
        <KpiCard label="Pending Leaves" value={leaveRequests.filter(l => l.status === "pending").length} sub="Requests" icon={Clock} color="bg-amber-50" iconColor="text-amber-600"/>
      </div>

      {/* Department Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {departments.map((d, i) => (
          <Card key={d.id || i} className="p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                <Building2 className="h-5 w-5 text-[var(--gs-teal)]"/>
              </div>
              <div>
                <div className="font-semibold text-sm">{d.name}</div>
                <div className="text-[11px] text-[var(--gs-muted)]">{d.employees_count ?? 0} employees</div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Employee List */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Employees</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Name</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Department</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Position</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {employees.map((e, i) => (
                <tr key={e.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{e.name}</td>
                  <td className="p-3 text-[var(--gs-muted)]">{e.department || "—"}</td>
                  <td className="p-3">{e.position || "—"}</td>
                  <td className="p-3"><StatusBadge status={e.status}/></td>
                </tr>
              ))}
              {employees.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No employees yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Attendance */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Today's Attendance</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Employee</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Check In</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Check Out</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {attendance.map((a, i) => (
                <tr key={a.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{a.employee_name}</td>
                  <td className="p-3 text-xs">{a.check_in || "—"}</td>
                  <td className="p-3 text-xs">{a.check_out || "—"}</td>
                  <td className="p-3">{a.present ? <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Present</Badge> : <Badge className="bg-rose-100 text-rose-700 text-[10px]">Absent</Badge>}</td>
                </tr>
              ))}
              {attendance.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No attendance data for today</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Leave Requests */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Leave Requests</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Employee</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Type</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">From</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">To</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {leaveRequests.map((l, i) => (
                <tr key={l.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{l.employee_name}</td>
                  <td className="p-3"><Badge variant="outline" className="text-[10px]">{l.type}</Badge></td>
                  <td className="p-3 text-xs">{l.from ? new Date(l.from).toLocaleDateString("en-IN") : "—"}</td>
                  <td className="p-3 text-xs">{l.to ? new Date(l.to).toLocaleDateString("en-IN") : "—"}</td>
                  <td className="p-3"><StatusBadge status={l.status}/></td>
                </tr>
              ))}
              {leaveRequests.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No leave requests</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Payroll */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Payroll</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Employee</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Month</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Basic</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Deductions</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Net Pay</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {payroll.map((p, i) => (
                <tr key={p.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-semibold">{p.employee_name}</td>
                  <td className="p-3 text-xs">{p.month}</td>
                  <td className="p-3">{fmtINR(p.basic)}</td>
                  <td className="p-3 text-rose-500">{fmtINR(p.deductions)}</td>
                  <td className="p-3 font-semibold text-[var(--gs-teal)]">{fmtINR(p.net_pay)}</td>
                </tr>
              ))}
              {payroll.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-[var(--gs-muted)] text-sm">No payroll data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========== BOOKING TAB ========== */
function BookingTab() {
  const [services, setServices] = useState([]);
  const [slots, setSlots] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [todayAppointments, setTodayAppointments] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get("/admin/business-builders/booking/services").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/booking/slots").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/booking/appointments").catch(() => ({ data: { items: [] } })),
      api.get("/admin/business-builders/booking/today").catch(() => ({ data: { items: [] } })),
    ]).then(([s, sl, a, t]) => {
      setServices(s.data?.items || []);
      setSlots(sl.data?.items || []);
      setAppointments(a.data?.items || []);
      setTodayAppointments(t.data?.items || []);
    });
  }, []);

  const slotGrid = {};
  slots.forEach(s => {
    if (!slotGrid[s.date]) slotGrid[s.date] = [];
    slotGrid[s.date].push(s);
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Services" value={services.length} sub="Active" icon={Calendar}/>
        <KpiCard label="Today's Appointments" value={todayAppointments.length} sub="Booked" icon={Clock} color="bg-blue-50" iconColor="text-blue-600"/>
        <KpiCard label="Total Appointments" value={appointments.length} sub="All time" icon={Calendar} color="bg-violet-50" iconColor="text-violet-600"/>
        <KpiCard label="Available Slots" value={slots.filter(s => s.available).length} sub="This week" icon={CheckCircle2} color="bg-emerald-50" iconColor="text-emerald-600"/>
      </div>

      {/* Services */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {services.map((s, i) => (
          <Card key={s.id || i} className="p-4">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-sm">{s.name}</h3>
              <Badge variant="outline" className="text-[10px]">{s.duration || "60 min"}</Badge>
            </div>
            <p className="text-[11px] text-[var(--gs-muted)] mb-2">{s.description || "—"}</p>
            <div className="text-xs font-semibold text-[var(--gs-teal)]">{fmtINR(s.price)}</div>
          </Card>
        ))}
      </div>

      {/* Available Slots Grid */}
      <Card className="p-4">
        <h3 className="font-semibold text-sm mb-3">Available Slots</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(slotGrid).map(([date, daySlots]) => (
            <div key={date}>
              <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2">{date}</div>
              <div className="flex flex-wrap gap-1.5">
                {daySlots.map((sl, i) => (
                  <Badge key={i} variant="outline" className={`text-[10px] ${sl.available ? "border-emerald-300 text-emerald-600" : "border-rose-300 text-rose-400 line-through"}`}>
                    {sl.time}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
          {Object.keys(slotGrid).length === 0 && (
            <div className="text-center py-6 text-[var(--gs-muted)] text-sm col-span-3">No slots available</div>
          )}
        </div>
      </Card>

      {/* Today's Appointments */}
      <Card className="overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: "var(--gs-border)" }}>
          <h3 className="font-semibold text-sm">Today's Appointments</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Time</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Client</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Service</th>
                <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {todayAppointments.map((a, i) => (
                <tr key={a.id || i} className="hover:bg-[var(--gs-surface-2)]">
                  <td className="p-3 font-mono text-xs">{a.time}</td>
                  <td className="p-3 font-semibold">{a.client_name}</td>
                  <td className="p-3 text-[var(--gs-muted)]">{a.service}</td>
                  <td className="p-3"><StatusBadge status={a.status}/></td>
                </tr>
              ))}
              {todayAppointments.length === 0 && (
                <tr><td colSpan={4} className="p-6 text-center text-[var(--gs-muted)] text-sm">No appointments today</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ========== MAIN TABS ========== */
export default function BusinessBuilders() {
  const [mainTab, setMainTab] = useState("crm");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Business Builders</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">CRM, ERP, HRMS & Booking — all-in-one business management</p>
        </div>
      </div>

      <Tabs value={mainTab} onValueChange={setMainTab}>
        <TabsList>
          <TabsTrigger value="crm">CRM</TabsTrigger>
          <TabsTrigger value="erp">ERP</TabsTrigger>
          <TabsTrigger value="hrms">HRMS</TabsTrigger>
          <TabsTrigger value="booking">Booking</TabsTrigger>
        </TabsList>

        <TabsContent value="crm" className="mt-4"><CRMTab/></TabsContent>
        <TabsContent value="erp" className="mt-4"><ERPTab/></TabsContent>
        <TabsContent value="hrms" className="mt-4"><HRMSTab/></TabsContent>
        <TabsContent value="booking" className="mt-4"><BookingTab/></TabsContent>
      </Tabs>
    </div>
  );
}
