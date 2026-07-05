import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";

export default function AdminSuppliers() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", contact: "", email: "", notes: "" });

  const load = async () => { const { data } = await api.get("/admin/suppliers"); setItems(data); };
  useEffect(() => { load(); }, []);

  const startCreate = () => { setEditing(null); setForm({ name: "", contact: "", email: "", notes: "" }); setOpen(true); };
  const startEdit = (s) => { setEditing(s); setForm({ name: s.name, contact: s.contact || "", email: s.email || "", notes: s.notes || "" }); setOpen(true); };
  const save = async () => {
    if (!form.name) return toast.error("Name required");
    if (editing) await api.put(`/admin/suppliers/${editing.id}`, form);
    else await api.post("/admin/suppliers", form);
    toast.success(editing ? "Updated" : "Supplier added"); setOpen(false); await load();
  };
  const del = async (s) => { if (!window.confirm(`Delete ${s.name}?`)) return; await api.delete(`/admin/suppliers/${s.id}`); await load(); };

  return (
    <div data-testid="admin-suppliers-page">
      <div className="flex items-center justify-between mb-6"><div><h1 className="font-display text-3xl">Suppliers</h1><p className="text-sm text-[var(--gs-muted)]">{items.length} suppliers</p></div><Button onClick={startCreate} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-add-supplier-button"><Plus className="h-4 w-4 mr-2"/>Add supplier</Button></div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{items.map((s) => (
        <div key={s.id} className="gs-card p-5">
          <div className="flex justify-between items-start mb-2"><div className="font-semibold">{s.name}</div><div className="flex gap-1"><Button size="icon" variant="ghost" onClick={() => startEdit(s)}><Pencil className="h-3.5 w-3.5"/></Button><Button size="icon" variant="ghost" onClick={() => del(s)}><Trash2 className="h-3.5 w-3.5 text-rose-500"/></Button></div></div>
          {s.contact && <div className="text-sm text-[var(--gs-muted)]">{s.contact}</div>}
          {s.email && <div className="text-sm text-[var(--gs-muted)]">{s.email}</div>}
          {s.notes && <p className="text-xs mt-2 text-[var(--gs-muted)]">{s.notes}</p>}
        </div>
      ))}</div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Edit supplier" : "Add supplier"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/>
            <Input placeholder="Contact" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })}/>
            <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}/>
            <Textarea placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}/>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button onClick={save} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
