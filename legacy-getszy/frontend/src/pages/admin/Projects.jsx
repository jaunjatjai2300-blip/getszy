import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  FolderOpen, Globe, Code2, ExternalLink, Download, Trash2,
  RefreshCw, Clock, CheckCircle2, AlertCircle, Loader2,
  Search, Wand2, Database, Plus, Eye
} from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

function StatusBadge({ s }) {
  if (s === "deployed" || s === "live")
    return <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><CheckCircle2 className="h-2.5 w-2.5 mr-1"/>Live</Badge>;
  if (s === "pending" || s === "building")
    return <Badge className="bg-amber-100 text-amber-700 text-[10px]"><Loader2 className="h-2.5 w-2.5 mr-1 animate-spin"/>Building</Badge>;
  if (s === "failed")
    return <Badge className="bg-rose-100 text-rose-700 text-[10px]"><AlertCircle className="h-2.5 w-2.5 mr-1"/>Failed</Badge>;
  return <Badge variant="outline" className="text-[10px]">{s || "draft"}</Badge>;
}

export default function AdminProjects() {
  const [builderProjects, setBuilderProjects] = useState([]);
  const [hostedSites, setHostedSites]         = useState([]);
  const [search, setSearch]                   = useState("");
  const [loading, setLoading]                 = useState(true);
  const [deleting, setDeleting]               = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [bp, hs] = await Promise.allSettled([
        api.get("/admin/projects?limit=50"),
        api.get("/hosting/list"),
      ]);
      if (bp.status === "fulfilled") setBuilderProjects(bp.value.data.items || bp.value.data || []);
      if (hs.status === "fulfilled") setHostedSites(hs.value.data.items || hs.value.data || []);
    } catch (e) {
      toast.error("Projects load karne mein error");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const deleteBuilder = async (id, name) => {
    if (!window.confirm(`Delete "${name}"?`)) return;
    setDeleting(id);
    try {
      await api.delete(`/builder/projects/${id}`);
      toast.success("Deleted"); await load();
    } catch (e) { toast.error("Delete failed"); } finally { setDeleting(null); }
  };

  const deleteHosted = async (id, slug) => {
    if (!window.confirm(`Delete hosted site "${slug}"?`)) return;
    setDeleting(id);
    try {
      await api.delete(`/hosting/sites/${id}`);
      toast.success("Removed"); await load();
    } catch (e) { toast.error("Delete failed"); } finally { setDeleting(null); }
  };

  const filteredBP = builderProjects.filter(p =>
    !search || (p.title || p.prompt || "").toLowerCase().includes(search.toLowerCase())
  );
  const filteredHS = hostedSites.filter(s =>
    !search || (s.slug || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-5" data-testid="admin-projects-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <FolderOpen className="h-7 w-7 text-[var(--gs-teal)]"/>Projects
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            Builder projects · {builderProjects.length} &nbsp;|&nbsp; Hosted sites · {hostedSites.length}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--gs-muted)]"/>
            <Input className="pl-8 h-9 w-52 text-xs" placeholder="Search…"
              value={search} onChange={e => setSearch(e.target.value)}/>
          </div>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
          </Button>
          <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
            onClick={() => window.open("/admin/build", "_self")}>
            <Plus className="h-3.5 w-3.5 mr-1.5"/>New Project
          </Button>
        </div>
      </div>

      <Tabs defaultValue="builder">
        <TabsList className="h-auto gap-1">
          <TabsTrigger value="builder" className="text-xs">
            <Wand2 className="h-3.5 w-3.5 mr-1"/>Build Studio ({filteredBP.length})
          </TabsTrigger>
          <TabsTrigger value="hosted" className="text-xs">
            <Globe className="h-3.5 w-3.5 mr-1"/>Hosted Sites ({filteredHS.length})
          </TabsTrigger>
        </TabsList>

        {/* ── Builder Projects ── */}
        <TabsContent value="builder" className="mt-4">
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1,2,3].map(i => (
                <div key={i} className="h-48 rounded-2xl bg-[var(--gs-surface-2)] animate-pulse"/>
              ))}
            </div>
          ) : filteredBP.length === 0 ? (
            <Card className="p-10 text-center">
              <Code2 className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/>
              <p className="text-sm text-[var(--gs-muted)] mb-3">Koi projects nahi hain abhi</p>
              <Button size="sm" className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90"
                onClick={() => window.open("/admin/build", "_self")}>
                <Wand2 className="h-3.5 w-3.5 mr-1.5"/>Build Studio kholo
              </Button>
            </Card>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredBP.map(p => (
                <Card key={p.id} className="p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-2">
                    <div className="h-9 w-9 rounded-xl bg-[var(--gs-teal-soft)] grid place-items-center flex-shrink-0">
                      <Code2 className="h-4 w-4 text-[var(--gs-teal)]"/>
                    </div>
                    <StatusBadge s={p.status}/>
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm line-clamp-1">{p.title || "Untitled Project"}</div>
                    <div className="text-[10px] text-[var(--gs-muted)] mt-1 line-clamp-2">
                      {p.prompt || p.description || "No description"}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-[var(--gs-muted)]">
                    <span className="flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5"/>
                      {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN") : "Unknown date"}
                    </span>
                    {p.kind && <Badge variant="outline" className="text-[10px]">{p.kind}</Badge>}
                  </div>
                  <div className="flex items-center gap-1.5">
                    {p.hosted_url && (
                      <Button size="sm" variant="outline" className="flex-1 text-xs h-7"
                        onClick={() => window.open(p.hosted_url, "_blank")}>
                        <Eye className="h-3 w-3 mr-1"/>Preview
                      </Button>
                    )}
                    {p.zip_url && (
                      <Button size="sm" variant="outline" className="h-7 px-2"
                        onClick={() => window.open(`${BACKEND_URL}${p.zip_url}`, "_blank")}>
                        <Download className="h-3 w-3"/>
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500"
                      disabled={deleting === p.id}
                      onClick={() => deleteBuilder(p.id, p.title || "project")}>
                      {deleting === p.id ? <Loader2 className="h-3 w-3 animate-spin"/> : <Trash2 className="h-3 w-3"/>}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── Hosted Sites ── */}
        <TabsContent value="hosted" className="mt-4">
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1,2,3].map(i => (
                <div key={i} className="h-40 rounded-2xl bg-[var(--gs-surface-2)] animate-pulse"/>
              ))}
            </div>
          ) : filteredHS.length === 0 ? (
            <Card className="p-10 text-center">
              <Globe className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/>
              <p className="text-sm text-[var(--gs-muted)] mb-3">Koi hosted sites nahi hain</p>
              <p className="text-xs text-[var(--gs-muted)]">Build Studio se ek site banao aur "Host" karo</p>
            </Card>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredHS.map(s => (
                <Card key={s.id} className="p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-2">
                    <div className="h-9 w-9 rounded-xl bg-blue-50 grid place-items-center flex-shrink-0">
                      <Globe className="h-4 w-4 text-blue-500"/>
                    </div>
                    <StatusBadge s={s.status}/>
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm font-mono">{s.slug}</div>
                    <div className="text-[10px] text-blue-500 mt-0.5">
                      getszy.com/host/{s.slug}
                    </div>
                    {s.size_bytes && (
                      <div className="text-[10px] text-[var(--gs-muted)] mt-1">
                        {(s.size_bytes / 1024).toFixed(1)} KB
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-[var(--gs-muted)]">
                    <span className="flex items-center gap-1">
                      <Clock className="h-2.5 w-2.5"/>
                      {s.created_at ? new Date(s.created_at).toLocaleDateString("en-IN") : ""}
                    </span>
                    <Badge variant="outline" className="text-[10px]">{s.source_kind || "html"}</Badge>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button size="sm" variant="outline" className="flex-1 text-xs h-7"
                      onClick={() => window.open(`${BACKEND_URL}/host/${s.slug}/`, "_blank")}>
                      <ExternalLink className="h-3 w-3 mr-1"/>Visit
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500"
                      disabled={deleting === s.id}
                      onClick={() => deleteHosted(s.id, s.slug)}>
                      {deleting === s.id ? <Loader2 className="h-3 w-3 animate-spin"/> : <Trash2 className="h-3 w-3"/>}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
