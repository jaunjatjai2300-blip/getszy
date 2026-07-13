import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Rocket, GitBranch, RotateCcw, Loader2, Plus, History } from "lucide-react";
import { toast } from "sonner";

export default function Releases() {
  const [releases, setReleases] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ version: "", notes: "", channel: "stable" });
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [r, p, c] = await Promise.allSettled([
        api.get("/admin/releases/"),
        api.get("/admin/releases/cicd/pipelines"),
        api.get("/admin/releases/channels"),
      ]);
      if (r.status === "fulfilled") setReleases(r.value.data?.releases || []);
      if (p.status === "fulfilled") setPipelines(p.value.data?.pipelines || []);
      if (c.status === "fulfilled") setChannels(c.value.data?.channels || []);
    } finally { setLoading(false); }
  };

  const createRelease = async () => {
    if (!form.version.trim()) return toast.error("Enter version");
    setCreating(true);
    try {
      await api.post("/admin/releases/", form);
      toast.success("Release created!");
      setShowCreate(false);
      setForm({ version: "", notes: "", channel: "stable" });
      loadAll();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally { setCreating(false); }
  };

  const rollback = async (id) => {
    try {
      await api.post(`/admin/releases/${id}/rollback`);
      toast.success("Rolled back!");
      loadAll();
    } catch (e) {
      toast.error("Rollback failed");
    }
  };

  const runPipeline = async (id) => {
    try {
      await api.post(`/admin/releases/cicd/pipelines/${id}/run`);
      toast.success("Pipeline executed!");
      loadAll();
    } catch (e) {
      toast.error("Pipeline failed");
    }
  };

  return (
    <div className="space-y-6" data-testid="releases-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-red-100 grid place-items-center">
            <Rocket className="h-5 w-5 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-display">Releases & CI/CD</h1>
            <p className="text-xs text-[var(--gs-muted)]">Version management, pipelines, rollback</p>
          </div>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
          <Plus className="h-4 w-4 mr-1" /> New Release
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <Rocket className="h-6 w-6 text-red-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{releases.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Releases</p>
        </Card>
        <Card className="p-4 text-center">
          <GitBranch className="h-6 w-6 text-[var(--gs-teal)] mx-auto mb-1" />
          <div className="text-2xl font-display">{pipelines.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Pipelines</p>
        </Card>
        <Card className="p-4 text-center">
          <RotateCcw className="h-6 w-6 text-amber-600 mx-auto mb-1" />
          <div className="text-2xl font-display">{channels.length}</div>
          <p className="text-[11px] text-[var(--gs-muted)]">Channels</p>
        </Card>
      </div>

      {showCreate && (
        <Card className="p-5 space-y-4">
          <h3 className="font-display">Create Release</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-[var(--gs-muted)]">Version</label>
              <Input value={form.version} onChange={e => setForm(f => ({ ...f, version: e.target.value }))} placeholder="v2.1.0" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--gs-muted)]">Channel</label>
              <select value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}
                className="w-full h-10 px-3 rounded-lg border border-[var(--gs-border)] bg-[var(--gs-surface)] text-sm">
                <option value="stable">Stable</option>
                <option value="beta">Beta</option>
                <option value="nightly">Nightly</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--gs-muted)]">Release Notes</label>
              <Input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="What's new" />
            </div>
          </div>
          <Button onClick={createRelease} disabled={creating} className="bg-[var(--gs-teal)]">
            {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Rocket className="h-4 w-4 mr-2" />}
            Create Release
          </Button>
        </Card>
      )}

      <Tabs defaultValue="releases">
        <TabsList>
          <TabsTrigger value="releases"><Rocket className="h-4 w-4 mr-1" /> Releases</TabsTrigger>
          <TabsTrigger value="pipelines"><GitBranch className="h-4 w-4 mr-1" /> Pipelines</TabsTrigger>
          <TabsTrigger value="channels"><Badge className="h-4 w-4 mr-1" /> Channels</TabsTrigger>
        </TabsList>

        <TabsContent value="releases">
          {loading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-teal)]" /></div>
          ) : releases.length > 0 ? (
            <div className="space-y-2">
              {releases.map(r => (
                <Card key={r.id} className="p-4 flex items-center gap-4">
                  <Rocket className="h-5 w-5 text-red-600" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-display font-bold">{r.version}</p>
                      <Badge variant={r.status === 'deployed' ? 'default' : 'outline'}>{r.status}</Badge>
                      <Badge variant="outline" className="text-[10px]">{r.channel}</Badge>
                    </div>
                    <p className="text-[11px] text-[var(--gs-muted)] mt-0.5">{r.notes || "No release notes"}</p>
                    <p className="text-[10px] text-[var(--gs-muted)]">{r.created_at?.slice(0, 16)}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => rollback(r.id)}>
                    <RotateCcw className="h-3 w-3 mr-1" /> Rollback
                  </Button>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No releases yet</Card>
          )}
        </TabsContent>

        <TabsContent value="pipelines">
          {pipelines.length > 0 ? (
            <div className="space-y-2">
              {pipelines.map(p => (
                <Card key={p.id} className="p-4 flex items-center gap-4">
                  <GitBranch className="h-5 w-5 text-[var(--gs-teal)]" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{p.name}</p>
                    <p className="text-[11px] text-[var(--gs-muted)]">Branch: {p.branch} • Steps: {p.steps?.join(", ")}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => runPipeline(p.id)}>
                    Run
                  </Button>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-8 text-center text-[var(--gs-muted)]">No pipelines configured</Card>
          )}
        </TabsContent>

        <TabsContent value="channels">
          <div className="grid grid-cols-3 gap-4">
            {channels.map(c => (
              <Card key={c.name} className="p-4 text-center">
                <p className="font-display font-bold">{c.name}</p>
                <p className="text-[11px] text-[var(--gs-muted)] mt-1">{c.description}</p>
                <Badge variant="outline" className="mt-2">{c.auto_deploy ? "Auto-deploy" : "Manual"}</Badge>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
