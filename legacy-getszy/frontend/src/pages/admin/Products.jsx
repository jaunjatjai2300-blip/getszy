import { useEffect, useState, useMemo } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Plus, Pencil, Trash2, Search, Package, RefreshCw, Download,
  ArrowUpDown, ArrowUp, ArrowDown, BoxesIcon, AlertTriangle,
  TrendingUp, ShoppingCart, Eye, MoreHorizontal, Copy, Filter
} from "lucide-react";
import { toast } from "sonner";
import SectionHeader from "@/components/admin/SectionHeader";
import { StatusBadge } from "@/components/admin/StatusBadge";
import ProdStatCard from "@/components/admin/ProdStatCard";

const EMPTY = { name: "", description: "", price: 0, cost_price: 0, stock: 0, category: "fashion", supplier: "", images: [], is_featured: false, is_digital: false };

export default function AdminProducts() {
  const [items, setItems] = useState([]);
  const [cats, setCats] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [imgUrl, setImgUrl] = useState("");
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("all");
  const [stockFilter, setStockFilter] = useState("all");
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const PER_PAGE = 20;

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/products");
      setItems(Array.isArray(data) ? data : []);
    } catch { toast.error("Failed to load products"); }
    setLoading(false);
  };

  useEffect(() => { load(); api.get("/categories").then(({ data }) => setCats(Array.isArray(data) ? data : [])); }, []);

  const filtered = useMemo(() => {
    let list = items;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name?.toLowerCase().includes(q) || p.category?.toLowerCase().includes(q) || p.supplier?.toLowerCase().includes(q));
    }
    if (catFilter !== 'all') list = list.filter(p => p.category === catFilter);
    if (stockFilter === 'low') list = list.filter(p => p.stock <= 5 && p.stock > 0);
    if (stockFilter === 'out') list = list.filter(p => p.stock === 0);
    if (stockFilter === 'in') list = list.filter(p => p.stock > 5);
    list = [...list].sort((a, b) => {
      const va = a[sortKey], vb = b[sortKey];
      if (va == null) return 1; if (vb == null) return -1;
      if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
      return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    return list;
  }, [items, search, catFilter, stockFilter, sortKey, sortDir]);

  const paged = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(filtered.length / PER_PAGE);

  const toggleSort = (k) => { if (sortKey === k) setSortDir(d => d === 'asc' ? 'desc' : 'asc'); else { setSortKey(k); setSortDir('asc'); } };
  const SortIcon = ({ k }) => sortKey === k ? (sortDir === 'asc' ? <ArrowUp className="h-3 w-3"/> : <ArrowDown className="h-3 w-3"/>) : <ArrowUpDown className="h-3 w-3 opacity-30"/>;

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
    if (!window.confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
    try { await api.delete(`/admin/products/${p.id}`); toast.success("Deleted"); await load(); }
    catch { toast.error("Delete failed"); }
  };

  const dup = (p) => {
    setEditing(null);
    setForm({ ...p, id: undefined, name: `${p.name} (copy)` });
    setImgUrl(p.images?.[0] || "");
    setOpen(true);
  };

  const exportCSV = () => {
    const rows = [['Name', 'Category', 'Price', 'Cost', 'Stock', 'Featured', 'Digital']];
    filtered.forEach(p => rows.push([p.name, p.category, p.price, p.cost_price || 0, p.stock, p.is_featured, p.is_digital]));
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'products.csv'; a.click();
    toast.success("Exported " + filtered.length + " products");
  };

  // Stats
  const totalProducts = items.length;
  const activeProducts = items.filter(p => p.stock > 0).length;
  const lowStock = items.filter(p => p.stock <= 5 && p.stock > 0).length;
  const outOfStock = items.filter(p => p.stock === 0).length;
  const totalValue = items.reduce((s, p) => s + (p.price * (p.stock || 0)), 0);
  const avgPrice = totalProducts ? items.reduce((s, p) => s + (p.price || 0), 0) / totalProducts : 0;

  return (
    <div className="space-y-6" data-testid="admin-products-page">
      <SectionHeader title="Products" subtitle={`${totalProducts} products · ${activeProducts} active`} icon={Package} loading={loading} onRefresh={load}>
        <Button onClick={exportCSV} variant="outline" size="sm" className="h-8"><Download className="h-3.5 w-3.5 mr-1"/>Export</Button>
        <Button onClick={startCreate} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" size="sm" data-testid="admin-add-product-button">
          <Plus className="h-4 w-4 mr-1"/>Add Product
        </Button>
      </SectionHeader>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <ProdStatCard label="Total" value={totalProducts} icon={BoxesIcon}/>
        <ProdStatCard label="Active" value={activeProducts} icon={Package} color="bg-emerald-50" iconColor="text-emerald-600"/>
        <ProdStatCard label="Low Stock" value={lowStock} icon={AlertTriangle} danger={lowStock > 0}/>
        <ProdStatCard label="Out of Stock" value={outOfStock} icon={AlertTriangle} danger={outOfStock > 0}/>
        <ProdStatCard label="Inventory Value" value={fmtINR(totalValue)} icon={TrendingUp} color="bg-blue-50" iconColor="text-blue-600"/>
        <ProdStatCard label="Avg Price" value={fmtINR(avgPrice)} icon={ShoppingCart} color="bg-violet-50" iconColor="text-violet-600"/>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--gs-muted)]"/>
          <Input className="pl-9" placeholder="Search products..." value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}/>
        </div>
        <Select value={catFilter} onValueChange={v => { setCatFilter(v); setPage(0); }}>
          <SelectTrigger className="w-36 h-9 text-xs"><SelectValue placeholder="Category"/></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {cats.map(c => <SelectItem key={c.slug} value={c.slug}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={stockFilter} onValueChange={v => { setStockFilter(v); setPage(0); }}>
          <SelectTrigger className="w-32 h-9 text-xs"><SelectValue placeholder="Stock"/></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Stock</SelectItem>
            <SelectItem value="in">In Stock</SelectItem>
            <SelectItem value="low">Low Stock</SelectItem>
            <SelectItem value="out">Out of Stock</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[700px]">
            <thead className="text-left text-[10px] uppercase tracking-wider text-[var(--gs-muted)] bg-[var(--gs-surface-2)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold cursor-pointer select-none" onClick={() => toggleSort('name')}><div className="flex items-center gap-1">Product <SortIcon k="name"/></div></th>
                <th className="px-4 py-2.5 font-semibold hidden md:table-cell cursor-pointer select-none" onClick={() => toggleSort('category')}><div className="flex items-center gap-1">Category <SortIcon k="category"/></div></th>
                <th className="px-4 py-2.5 font-semibold cursor-pointer select-none" onClick={() => toggleSort('price')}><div className="flex items-center gap-1">Price <SortIcon k="price"/></div></th>
                <th className="px-4 py-2.5 font-semibold hidden md:table-cell">Cost</th>
                <th className="px-4 py-2.5 font-semibold cursor-pointer select-none" onClick={() => toggleSort('stock')}><div className="flex items-center gap-1">Stock <SortIcon k="stock"/></div></th>
                <th className="px-4 py-2.5 font-semibold w-28">Status</th>
                <th className="px-4 py-2.5 font-semibold w-24"></th>
              </tr>
            </thead>
            <tbody>
              {paged.map((p) => (
                <tr key={p.id} className="border-t hover:bg-[var(--gs-surface-2)]/50 transition-colors" style={{ borderColor: "var(--gs-border)" }}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {p.images?.[0] ? (
                        <img src={p.images[0]} alt="" className="h-10 w-10 rounded-lg object-cover bg-[var(--gs-surface-2)]"/>
                      ) : (
                        <div className="h-10 w-10 rounded-lg bg-[var(--gs-surface-2)] grid place-items-center"><Package className="h-4 w-4 text-[var(--gs-muted)]"/></div>
                      )}
                      <div>
                        <div className="font-semibold text-xs truncate max-w-[200px]">{p.name}</div>
                        <div className="text-[10px] text-[var(--gs-muted)]">{p.supplier || "No supplier"}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell capitalize text-xs">{p.category?.replace("-", " ")}</td>
                  <td className="px-4 py-3 font-semibold text-xs">{fmtINR(p.price)}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-[var(--gs-muted)] text-xs">{fmtINR(p.cost_price)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold ${p.stock === 0 ? 'text-rose-600' : p.stock <= 5 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {p.stock}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {p.is_featured && <Badge className="text-[9px] bg-amber-50 text-amber-600 border-0">Featured</Badge>}
                      {p.is_digital && <Badge className="text-[9px] bg-violet-50 text-violet-600 border-0">Digital</Badge>}
                      {p.stock === 0 && <Badge className="text-[9px] bg-rose-50 text-rose-600 border-0">OOS</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-0.5 justify-end">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => dup(p)} title="Duplicate"><Copy className="h-3.5 w-3.5"/></Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => startEdit(p)} data-testid={`admin-edit-product-${p.id}`}><Pencil className="h-3.5 w-3.5"/></Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => del(p)} data-testid={`admin-delete-product-${p.id}`}><Trash2 className="h-3.5 w-3.5 text-rose-500"/></Button>
                    </div>
                  </td>
                </tr>
              ))}
              {paged.length === 0 && (
                <tr><td colSpan={7} className="py-12 text-center text-[var(--gs-muted)] text-sm">{search || catFilter !== 'all' || stockFilter !== 'all' ? "No products match filters" : "No products yet — add your first product"}</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-2 border-t text-xs text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>
            <span>{filtered.length} products</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</Button>
              <span>{page + 1} / {totalPages}</span>
              <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </Card>

      {/* Dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editing ? "Edit Product" : "New Product"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input placeholder="Product name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="admin-product-name-input"/>
            <Textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3}/>
            <div className="grid grid-cols-3 gap-2">
              <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Price *</label><Input type="number" placeholder="0" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} data-testid="admin-product-price-input"/></div>
              <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Cost Price</label><Input type="number" placeholder="0" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })}/></div>
              <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Stock *</label><Input type="number" placeholder="0" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })}/></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Category</label>
                <select className="w-full h-10 rounded-xl border px-3 text-sm" style={{ borderColor: "var(--gs-border)", background: "#fff" }} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                  {cats.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
                </select>
              </div>
              <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Supplier</label><Input placeholder="Optional" value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })}/></div>
            </div>
            <div><label className="text-[10px] text-[var(--gs-muted)] mb-1 block">Image URL</label><Input placeholder="https://..." value={imgUrl || form.images?.[0] || ""} onChange={(e) => setImgUrl(e.target.value)}/></div>
            {imgUrl && <img src={imgUrl} alt="" className="h-20 w-20 rounded-lg object-cover"/>}
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })} className="rounded"/><span className="text-xs">Featured</span></label>
              <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={form.is_digital} onChange={(e) => setForm({ ...form, is_digital: e.target.checked })} className="rounded"/><span className="text-xs">Digital Product</span></label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save} className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="admin-product-save-button">
              {editing ? "Update" : "Create"} Product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
