import { useEffect, useState } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

const EMPTY = { name: "", description: "", price: 0, cost_price: 0, stock: 0, category: "fashion", supplier: "", images: [], is_featured: false, is_digital: false };

export default function AdminProducts() {
  const [items, setItems] = useState([]);
  const [cats, setCats] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [imgUrl, setImgUrl] = useState("");

  const load = async () => {
    const { data } = await api.get("/admin/products");
    setItems(data);
  };
  useEffect(() => { load(); api.get("/categories").then(({ data }) => setCats(data)); }, []);

  const startEdit = (p) => { setEditing(p); setForm({ ...p, supplier: p.supplier || "" }); setOpen(true); };
  const startCreate = () => { setEditing(null); setForm(EMPTY); setImgUrl(""); setOpen(true); };

  const save = async () => {
    const payload = { ...form, price: Number(form.price), cost_price: Number(form.cost_price || 0), stock: Number(form.stock || 0), images: imgUrl ? [imgUrl] : (form.images || []) };
    try {
      if (editing) { await api.put(`/admin/products/${editing.id}`, payload); toast.success("Product updated"); }
      else { await api.post("/admin/products", payload); toast.success("Product added"); }
      setOpen(false); await load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  const del = async (p) => {
    if (!window.confirm(`Delete ${p.name}?`)) return;
    await api.delete(`/admin/products/${p.id}`); toast.success("Deleted"); await load();
  };

  return (
    <div data-testid="admin-products-page">
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="font-display text-3xl">Products</h1><p className="text-sm text-[var(--gs-muted)]">{items.length} total</p></div>
        <Button onClick={startCreate} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-add-product-button"><Plus className="h-4 w-4 mr-2"/>Add product</Button>
      </div>
      <div className="gs-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wider text-[var(--gs-muted)] border-b" style={{ borderColor: "var(--gs-border)" }}><tr><th className="p-4">Product</th><th className="p-4 hidden md:table-cell">Category</th><th className="p-4">Price</th><th className="p-4 hidden md:table-cell">Cost</th><th className="p-4">Stock</th><th className="p-4 w-24"></th></tr></thead>
          <tbody>{items.map((p) => (
            <tr key={p.id} className="border-b last:border-0" style={{ borderColor: "var(--gs-border)" }}>
              <td className="p-4"><div className="flex items-center gap-3"><img src={p.images?.[0]} alt="" className="h-10 w-10 rounded-lg object-cover" style={{ background: "var(--gs-surface-2)" }}/><div><div className="font-semibold truncate max-w-[200px]">{p.name}</div><div className="text-xs text-[var(--gs-muted)]">{p.supplier || "—"}</div></div></div></td>
              <td className="p-4 hidden md:table-cell capitalize">{p.category?.replace("-", " ")}</td>
              <td className="p-4 font-semibold">{fmtINR(p.price)}</td>
              <td className="p-4 hidden md:table-cell text-[var(--gs-muted)]">{fmtINR(p.cost_price)}</td>
              <td className="p-4"><span className={p.stock <= 5 ? "text-rose-600 font-semibold" : ""}>{p.stock}</span></td>
              <td className="p-4"><div className="flex gap-1 justify-end"><Button size="icon" variant="ghost" onClick={() => startEdit(p)} data-testid={`admin-edit-product-${p.id}`}><Pencil className="h-4 w-4"/></Button><Button size="icon" variant="ghost" onClick={() => del(p)} data-testid={`admin-delete-product-${p.id}`}><Trash2 className="h-4 w-4 text-rose-500"/></Button></div></td>
            </tr>
          ))}</tbody>
        </table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Edit product" : "Add product"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="admin-product-name-input"/>
            <Textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}/>
            <div className="grid grid-cols-3 gap-2">
              <Input type="number" placeholder="Price" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} data-testid="admin-product-price-input"/>
              <Input type="number" placeholder="Cost price" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })}/>
              <Input type="number" placeholder="Stock" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })}/>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select className="h-11 rounded-xl border px-3" style={{ borderColor: "var(--gs-border)", background: "#fff" }} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{cats.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}</select>
              <Input placeholder="Supplier (optional)" value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })}/>
            </div>
            <Input placeholder="Image URL" value={imgUrl || form.images?.[0] || ""} onChange={(e) => setImgUrl(e.target.value)}/>
            <div className="flex gap-4 text-sm"><label className="flex items-center gap-2"><input type="checkbox" checked={form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })}/>Featured</label><label className="flex items-center gap-2"><input type="checkbox" checked={form.is_digital} onChange={(e) => setForm({ ...form, is_digital: e.target.checked })}/>Digital product</label></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={save} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-product-save-button">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
