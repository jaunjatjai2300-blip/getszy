import { useEffect, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export default function AdminCustomers() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/admin/customers").then(({ data }) => setItems(data)); }, []);
  return (
    <div data-testid="admin-customers-page">
      <h1 className="font-display text-3xl mb-6">Customers</h1>
      <div className="gs-card overflow-x-auto">
        <table className="w-full text-sm min-w-[520px]">
          <thead className="text-left text-xs uppercase tracking-wider text-[var(--gs-muted)] border-b" style={{ borderColor: "var(--gs-border)" }}><tr><th className="p-4">Name</th><th className="p-4">Email</th><th className="p-4">Orders</th><th className="p-4">Lifetime Value</th><th className="p-4 hidden md:table-cell">Joined</th></tr></thead>
          <tbody>{items.map((u) => (
            <tr key={u.id} className="border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
              <td className="p-4 font-semibold">{u.name}</td>
              <td className="p-4 text-[var(--gs-muted)]">{u.email}</td>
              <td className="p-4"><Badge variant="outline">{u.orders_count}</Badge></td>
              <td className="p-4 font-semibold">{fmtINR(u.lifetime_value)}</td>
              <td className="p-4 hidden md:table-cell text-xs text-[var(--gs-muted)]">{new Date(u.created_at).toLocaleDateString()}</td>
            </tr>
          ))}{items.length === 0 && <tr><td colSpan={5} className="py-10 text-center text-[var(--gs-muted)]">No customers yet</td></tr>}</tbody>
        </table>
      </div>
    </div>
  );
}
