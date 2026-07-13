import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Search, Star, Download, ShoppingCart, Plus, RefreshCw, Filter,
  Grid3X3, Tag, DollarSign, Eye, ExternalLink, Code2, Paintbrush,
  Database, Zap, Shield, Globe, Users, BarChart3, Layout, Briefcase,
  Settings, Package, Rocket, Heart, Share2, ChevronRight
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const CATEGORIES = [
  { id: "all", label: "All", icon: Grid3X3 },
  { id: "templates", label: "Templates", icon: Layout },
  { id: "plugins", label: "Plugins", icon: Zap },
  { id: "themes", label: "Themes", icon: Paintbrush },
  { id: "integrations", label: "Integrations", icon: Globe },
  { id: "ai-tools", label: "AI Tools", icon: Sparkles },
  { id: "dev-tools", label: "Dev Tools", icon: Code2 },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "security", label: "Security", icon: Shield },
];

function StarRating({ rating }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map(s => (
        <Star key={s} className={`h-3 w-3 ${s <= Math.round(rating) ? "text-amber-400 fill-amber-400" : "text-slate-300"}`}/>
      ))}
      <span className="text-[10px] text-[var(--gs-muted)] ml-1">{rating?.toFixed(1)}</span>
    </div>
  );
}

export default function Marketplace() {
  const [items, setItems] = useState([]);
  const [installs, setInstalls] = useState([]);
  const [earnings, setEarnings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState("browse");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newListing, setNewListing] = useState({
    title: "", description: "", category: "templates", price: "0", tags: "", tech_stack: "",
  });

  const load = async () => {
    setError(false);
    try {
      const [itemsRes, installsRes, earningsRes] = await Promise.all([
        api.get("/admin/marketplace/items").catch(() => ({ data: { items: [] } })),
        api.get("/admin/marketplace/my-installs").catch(() => ({ data: { items: [] } })),
        api.get("/admin/marketplace/earnings").catch(() => ({ data: null })),
      ]);
      setItems(itemsRes.data?.items || []);
      setInstalls(installsRes.data?.items || []);
      setEarnings(earningsRes.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const installItem = async (id) => {
    try {
      await api.post(`/admin/marketplace/items/${id}/install`);
      setItems(prev => prev.map(item => item.id === id ? { ...item, installed: true, installs: (item.installs || 0) + 1 } : item));
    } catch { /* silent */ }
  };

  const uninstallItem = async (id) => {
    try {
      await api.post(`/admin/marketplace/items/${id}/uninstall`);
      setItems(prev => prev.map(item => item.id === id ? { ...item, installed: false } : item));
      setInstalls(prev => prev.filter(item => item.id !== id));
    } catch { /* silent */ }
  };

  const createListing = async () => {
    if (!newListing.title.trim()) return;
    try {
      const r = await api.post("/admin/marketplace/items", newListing);
      setItems(prev => [...prev, r.data?.item].filter(Boolean));
      setNewListing({ title: "", description: "", category: "templates", price: "0", tags: "", tech_stack: "" });
      setShowCreateForm(false);
      setTab("browse");
    } catch { /* silent */ }
  };

  const filteredItems = items.filter(item => {
    const matchSearch = !search || item.title?.toLowerCase().includes(search.toLowerCase()) || item.description?.toLowerCase().includes(search.toLowerCase());
    const matchCategory = category === "all" || item.category === category;
    return matchSearch && matchCategory;
  });

  const featured = items.filter(i => i.featured).slice(0, 4);

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Marketplace</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Browse, install & publish SaaS components</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={() => { setShowCreateForm(true); setTab("create"); }}>
            <Plus className="h-3.5 w-3.5 mr-1"/>Publish
          </Button>
          <Button variant="outline" size="sm" className="h-8" onClick={load}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="browse">Browse</TabsTrigger>
          <TabsTrigger value="installs">My Installs ({installs.length})</TabsTrigger>
          <TabsTrigger value="earnings">Earnings</TabsTrigger>
          <TabsTrigger value="create">Create</TabsTrigger>
        </TabsList>

        {/* Browse */}
        <TabsContent value="browse" className="mt-4 space-y-4">
          {/* Featured */}
          {featured.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-2 px-1">Featured</div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {featured.map(item => (
                  <MarketplaceCard key={item.id} item={item} onInstall={installItem}/>
                ))}
              </div>
            </div>
          )}

          {/* Search & Filter */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--gs-muted)]"/>
              <Input placeholder="Search marketplace…" value={search} onChange={e => setSearch(e.target.value)} className="pl-9 text-xs"/>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map(c => (
              <button key={c.id} onClick={() => setCategory(c.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
                  category === c.id ? "bg-[var(--gs-teal)] text-white" : "bg-white border hover:bg-[var(--gs-surface-2)]"
                }`}>
                <c.icon className="h-3 w-3"/>{c.label}
              </button>
            ))}
          </div>

          {/* Items Grid */}
          {filteredItems.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <ShoppingCart className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi items nahi
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {filteredItems.map(item => (
                <MarketplaceCard key={item.id} item={item} onInstall={installItem}/>
              ))}
            </div>
          )}
        </TabsContent>

        {/* My Installs */}
        <TabsContent value="installs" className="mt-4">
          {installs.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Download className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi installs nahi — Browse tab se install karo
            </div>
          ) : (
            <div className="space-y-2">
              {installs.map((item, i) => (
                <Card key={item.id || i} className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                      <Package className="h-5 w-5 text-[var(--gs-teal)]"/>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold">{item.title}</div>
                      <div className="text-[11px] text-[var(--gs-muted)]">Installed {item.installed_at}</div>
                    </div>
                    <Badge variant="outline" className="text-[10px] text-emerald-600">Installed</Badge>
                    <Button variant="outline" size="sm" className="h-7 text-[10px] text-rose-500" onClick={() => uninstallItem(item.id)}>
                      Uninstall
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Earnings */}
        <TabsContent value="earnings" className="mt-4">
          {earnings ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "Total Earnings", value: `₹${earnings.total || 0}` },
                  { label: "This Month", value: `₹${earnings.this_month || 0}` },
                  { label: "Total Sales", value: earnings.total_sales || 0 },
                  { label: "Active Listings", value: earnings.active_listings || 0 },
                ].map(s => (
                  <Card key={s.label} className="p-4">
                    <div className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold mb-1">{s.label}</div>
                    <div className="text-xl font-display">{s.value}</div>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">Earnings data available after first sale</div>
          )}
        </TabsContent>

        {/* Create */}
        <TabsContent value="create" className="mt-4">
          <Card className="p-5 max-w-xl">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Plus className="h-4 w-4 text-[var(--gs-teal)]"/>Create Listing
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Title</label>
                <Input className="mt-1 text-xs" placeholder="Listing title" value={newListing.title} onChange={e => setNewListing(p => ({ ...p, title: e.target.value }))}/>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Description</label>
                <Textarea className="mt-1 text-xs" placeholder="Description" rows={3} value={newListing.description} onChange={e => setNewListing(p => ({ ...p, description: e.target.value }))}/>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Category</label>
                  <Select value={newListing.category} onValueChange={v => setNewListing(p => ({ ...p, category: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.filter(c => c.id !== "all").map(c => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Price (₹)</label>
                  <Input className="mt-1 text-xs" type="number" placeholder="0 for free" value={newListing.price} onChange={e => setNewListing(p => ({ ...p, price: e.target.value }))}/>
                </div>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Tags (comma separated)</label>
                <Input className="mt-1 text-xs" placeholder="react, saas, template" value={newListing.tags} onChange={e => setNewListing(p => ({ ...p, tags: e.target.value }))}/>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Tech Stack</label>
                <Input className="mt-1 text-xs" placeholder="React, Node.js, MongoDB" value={newListing.tech_stack} onChange={e => setNewListing(p => ({ ...p, tech_stack: e.target.value }))}/>
              </div>
              <Button className="bg-[var(--gs-teal)] w-full" onClick={createListing}>Publish Listing</Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MarketplaceCard({ item, onInstall }) {
  return (
    <Card className="p-4 hover:shadow-md transition-all flex flex-col">
      <div className="flex items-start gap-3 mb-3">
        <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
          <Package className="h-5 w-5 text-[var(--gs-teal)]"/>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold truncate">{item.title}</h3>
          <p className="text-[11px] text-[var(--gs-muted)] line-clamp-2">{item.description}</p>
        </div>
      </div>
      <div className="flex items-center gap-1 mb-3">
        <StarRating rating={item.rating}/>
        <span className="text-[10px] text-[var(--gs-muted)] ml-1">({item.rating_count || 0})</span>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <Badge variant="outline" className="text-[9px]">{item.category}</Badge>
        {item.price > 0 ? (
          <Badge className="text-[9px] bg-[var(--gs-teal)]">₹{item.price}</Badge>
        ) : (
          <Badge variant="outline" className="text-[9px] text-emerald-600">Free</Badge>
        )}
      </div>
      <div className="flex items-center gap-2 mt-auto">
        <span className="text-[10px] text-[var(--gs-muted)] flex items-center gap-1">
          <Download className="h-2.5 w-2.5"/>{item.installs || 0} installs
        </span>
        <div className="flex-1"/>
        {!item.installed ? (
          <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={() => onInstall(item.id)}>
            <Download className="h-3 w-3 mr-1"/>Install
          </Button>
        ) : (
          <Badge variant="outline" className="text-[10px] text-emerald-600">Installed</Badge>
        )}
      </div>
    </Card>
  );
}
