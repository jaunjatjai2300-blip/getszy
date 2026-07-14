import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Database, Code2, Rocket, Eye, Wand2, ChevronDown, ChevronRight,
  RefreshCw, Plus, FileCode2, Folder, FolderOpen, Settings, Download,
  CheckCircle2, Cpu, Zap, Server, Play, Copy, History, Trash2,
  Search, Filter, Layers
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function APIBuilder() {
  const [tab, setTab] = useState("schema");
  const [collections, setCollections] = useState([]);
  const [generatedAPIs, setGeneratedAPIs] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [selectedCollections, setSelectedCollections] = useState([]);
  const [apiType, setApiType] = useState("rest");
  const [authType, setAuthType] = useState("jwt");
  const [features, setFeatures] = useState(["pagination", "search"]);
  const [generating, setGenerating] = useState(false);
  const [generatedCode, setGeneratedCode] = useState(null);

  const [previewUrl, setPreviewUrl] = useState("");
  const [previewMethod, setPreviewMethod] = useState("GET");
  const [previewBody, setPreviewBody] = useState("");
  const [previewResponse, setPreviewResponse] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [expandedCollection, setExpandedCollection] = useState(null);

  const load = async () => {
    setError(false);
    try {
      const [cols, apis, hist] = await Promise.all([
        api.get("/admin/api-builder/collections").catch(() => ({ data: { items: [] } })),
        api.get("/admin/api-builder/generated").catch(() => ({ data: { items: [] } })),
        api.get("/admin/api-builder/history").catch(() => ({ data: { items: [] } })),
      ]);
      setCollections(cols.data?.items || []);
      setGeneratedAPIs(apis.data?.items || []);
      setHistory(hist.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const generateAPI = async () => {
    if (selectedCollections.length === 0) return;
    setGenerating(true);
    try {
      const r = await api.post("/admin/api-builder/generate", {
        collections: selectedCollections,
        type: apiType,
        auth: authType,
        features,
      });
      setGeneratedCode(r.data);
      setTab("code");
      setHistory(prev => [{ ...r.data, timestamp: new Date().toISOString() }, ...prev]);
    } catch { /* silent */ }
    setGenerating(false);
  };

  const previewAPI = async () => {
    if (!previewUrl.trim()) return;
    setPreviewLoading(true);
    try {
      const r = await api.post("/admin/api-builder/preview", {
        url: previewUrl,
        method: previewMethod,
        body: previewBody ? JSON.parse(previewBody) : undefined,
      });
      setPreviewResponse(r.data);
    } catch (err) {
      setPreviewResponse({ error: err.message || "Request failed" });
    }
    setPreviewLoading(false);
  };

  const deployAPI = async (id) => {
    try {
      await api.post(`/admin/api-builder/deploy/${id}`);
      setGeneratedAPIs(prev => prev.map(a => a.id === id ? { ...a, status: "deployed" } : a));
    } catch { /* silent */ }
  };

  const toggleFeature = (f) => {
    setFeatures(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);
  };

  const toggleCollection = (name) => {
    setSelectedCollections(prev => prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name]);
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">API Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Generate REST, GraphQL & OpenAPI endpoints from MongoDB schemas</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="schema">Schema Explorer</TabsTrigger>
          <TabsTrigger value="generator">Generator</TabsTrigger>
          <TabsTrigger value="code">Generated Code</TabsTrigger>
          <TabsTrigger value="preview">Preview & Test</TabsTrigger>
          <TabsTrigger value="history">History ({history.length})</TabsTrigger>
        </TabsList>

        {/* Schema Explorer */}
        <TabsContent value="schema" className="mt-4">
          <div className="grid lg:grid-cols-[1fr_300px] gap-4">
            <Card className="p-4">
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <Database className="h-4 w-4 text-[var(--gs-teal)]"/>MongoDB Collections
              </h3>
              <div className="space-y-1">
                {collections.map((col) => (
                  <div key={col.name}>
                    <div
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm ${expandedCollection === col.name ? "bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`}
                      onClick={() => setExpandedCollection(expandedCollection === col.name ? null : col.name)}>
                      {expandedCollection === col.name ? <ChevronDown className="h-3 w-3"/> : <ChevronRight className="h-3 w-3"/>}
                      <Database className="h-3.5 w-3.5"/>
                      <span className="font-semibold">{col.name}</span>
                      <Badge variant="outline" className="text-[9px] ml-auto">{col.count ?? "—"}</Badge>
                    </div>
                    {expandedCollection === col.name && col.fields && (
                      <div className="ml-8 space-y-0.5 py-1">
                        {col.fields.map((f) => (
                          <div key={f.name} className="flex items-center gap-2 px-2 py-1 text-xs text-[var(--gs-muted)]">
                            <span className="font-semibold text-[var(--gs-ink)]">{f.name}</span>
                            <Badge variant="outline" className="text-[8px]">{f.type}</Badge>
                            {f.required && <Badge className="bg-rose-100 text-rose-600 text-[8px]">required</Badge>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {collections.length === 0 && (
                  <div className="text-center py-8 text-[var(--gs-muted)] text-sm">No collections found</div>
                )}
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="font-semibold text-sm mb-3">Quick Info</h3>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[var(--gs-muted)]">Total Collections</span>
                  <div className="text-lg font-display">{collections.length}</div>
                </div>
                <div>
                  <span className="text-[var(--gs-muted)]">Total Fields</span>
                  <div className="text-lg font-display">{collections.reduce((a, c) => a + (c.fields?.length || 0), 0)}</div>
                </div>
                <div>
                  <span className="text-[var(--gs-muted)]">Generated APIs</span>
                  <div className="text-lg font-display">{generatedAPIs.length}</div>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* Generator Panel */}
        <TabsContent value="generator" className="mt-4">
          <Card className="p-5 max-w-2xl">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-[var(--gs-teal)]"/>Generate API
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Select Collections</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {collections.map((col) => (
                    <label key={col.name} className="flex items-center gap-2 text-xs cursor-pointer p-2 rounded-lg hover:bg-[var(--gs-surface-2)]">
                      <Checkbox checked={selectedCollections.includes(col.name)} onCheckedChange={() => toggleCollection(col.name)}/>
                      <span className="font-semibold">{col.name}</span>
                      <Badge variant="outline" className="text-[8px] ml-auto">{col.fields?.length || 0} fields</Badge>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">API Type</label>
                  <Select value={apiType} onValueChange={setApiType}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rest">REST API</SelectItem>
                      <SelectItem value="graphql">GraphQL</SelectItem>
                      <SelectItem value="openapi">OpenAPI Spec</SelectItem>
                      <SelectItem value="sdk">SDK Package</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Authentication</label>
                  <Select value={authType} onValueChange={setAuthType}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="jwt">JWT Token</SelectItem>
                      <SelectItem value="apikey">API Key</SelectItem>
                      <SelectItem value="oauth">OAuth 2.0</SelectItem>
                      <SelectItem value="none">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Features</label>
                <div className="grid grid-cols-3 gap-2 mt-1">
                  {["pagination", "search", "filtering", "sorting", "validation", "rate-limiting", "caching", "cors", "logging"].map((f) => (
                    <label key={f} className="flex items-center gap-2 text-xs cursor-pointer">
                      <Checkbox checked={features.includes(f)} onCheckedChange={() => toggleFeature(f)}/>
                      {f}
                    </label>
                  ))}
                </div>
              </div>

              <Button className="bg-[var(--gs-teal)] w-full" onClick={generateAPI} disabled={generating || selectedCollections.length === 0}>
                {generating ? "Generating…" : "Generate API"}
              </Button>
            </div>
          </Card>
        </TabsContent>

        {/* Generated Code */}
        <TabsContent value="code" className="mt-4">
          {generatedCode ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm">Generated Files ({generatedCode.files?.length || 0})</h3>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="h-7 text-[10px]">
                    <Download className="h-3 w-3 mr-1"/>Download All
                  </Button>
                  <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={() => deployAPI(generatedCode.id)}>
                    <Rocket className="h-3 w-3 mr-1"/>Deploy
                  </Button>
                </div>
              </div>
              <div className="grid lg:grid-cols-[250px_1fr] gap-4">
                <Card className="p-4">
                  <h4 className="text-xs font-semibold mb-2">Files</h4>
                  <div className="space-y-0.5">
                    {(generatedCode.files || []).map((f, i) => (
                      <div key={i} className="flex items-center gap-1.5 px-2 py-1 text-xs rounded cursor-pointer hover:bg-[var(--gs-surface-2)]">
                        <FileCode2 className="h-3 w-3 text-amber-500"/>
                        {f.name}
                      </div>
                    ))}
                  </div>
                </Card>
                <Card className="p-4">
                  {(generatedCode.files || []).map((f, i) => (
                    <div key={i} className="mb-4">
                      <div className="text-xs font-mono text-[var(--gs-muted)] mb-1">{f.name}</div>
                      <pre className="text-xs font-mono bg-black text-green-400 p-4 rounded-lg overflow-x-auto max-h-64">
                        <code>{f.content}</code>
                      </pre>
                    </div>
                  ))}
                </Card>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Code2 className="h-8 w-8 mx-auto mb-2 opacity-30"/>Generate an API first to see code here
            </div>
          )}
        </TabsContent>

        {/* Preview & Test */}
        <TabsContent value="preview" className="mt-4">
          <div className="grid lg:grid-cols-2 gap-4">
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
                <Eye className="h-4 w-4 text-[var(--gs-teal)]"/>API Tester
              </h3>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Select value={previewMethod} onValueChange={setPreviewMethod}>
                    <SelectTrigger className="w-24 h-9"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GET">GET</SelectItem>
                      <SelectItem value="POST">POST</SelectItem>
                      <SelectItem value="PUT">PUT</SelectItem>
                      <SelectItem value="DELETE">DELETE</SelectItem>
                      <SelectItem value="PATCH">PATCH</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input placeholder="/api/v1/resource" value={previewUrl} onChange={e => setPreviewUrl(e.target.value)}/>
                </div>
                {(previewMethod === "POST" || previewMethod === "PUT" || previewMethod === "PATCH") && (
                  <div>
                    <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Request Body (JSON)</label>
                    <Textarea value={previewBody} onChange={e => setPreviewBody(e.target.value)}
                      placeholder='{"key": "value"}' className="mt-1 font-mono text-xs min-h-[120px]"/>
                  </div>
                )}
                <Button className="w-full bg-[var(--gs-teal)]" onClick={previewAPI} disabled={previewLoading}>
                  {previewLoading ? "Sending…" : "Send Request"}
                </Button>
              </div>
            </Card>
            <Card className="p-5">
              <h3 className="font-semibold text-sm mb-4">Response</h3>
              {previewResponse ? (
                <pre className="text-xs font-mono bg-black text-green-400 p-4 rounded-lg overflow-x-auto min-h-[200px] max-h-[400px]">
                  <code>{JSON.stringify(previewResponse, null, 2)}</code>
                </pre>
              ) : (
                <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
                  Send a request to see the response
                </div>
              )}
            </Card>
          </div>
        </TabsContent>

        {/* History */}
        <TabsContent value="history" className="mt-4">
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left" style={{ borderColor: "var(--gs-border)" }}>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Timestamp</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Type</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Collections</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Auth</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Status</th>
                    <th className="p-3 text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
                  {history.map((h, i) => (
                    <tr key={h.id || i} className="hover:bg-[var(--gs-surface-2)]">
                      <td className="p-3 text-xs text-[var(--gs-muted)]">{h.timestamp ? new Date(h.timestamp).toLocaleString("en-IN") : "—"}</td>
                      <td className="p-3"><Badge variant="outline" className="text-[10px] uppercase">{h.type}</Badge></td>
                      <td className="p-3">{(h.collections || []).join(", ")}</td>
                      <td className="p-3"><Badge variant="outline" className="text-[10px]">{h.auth}</Badge></td>
                      <td className="p-3">
                        {h.status === "deployed" ? (
                          <span className="flex items-center gap-1 text-emerald-600 text-xs"><CheckCircle2 className="h-3 w-3"/>Deployed</span>
                        ) : (
                          <Badge variant="outline" className="text-[10px]">{h.status || "draft"}</Badge>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => deployAPI(h.id)}>
                          <Rocket className="h-3 w-3 mr-1"/>Deploy
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {history.length === 0 && (
                    <tr><td colSpan={6} className="p-6 text-center text-[var(--gs-muted)] text-sm">No API generation history</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
