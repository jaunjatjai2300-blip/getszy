import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Smartphone, Globe, ShoppingCart, MessageCircle, BookOpen, Briefcase,
  Calendar, Utensils, Dumbbell, Layout, Code2, Rocket, Eye, Wand2,
  ChevronDown, ChevronRight, RefreshCw, Plus, Settings, Download,
  CheckCircle2, Cpu, Zap, Folder, FolderOpen, FileCode2, Trash2, Play
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const TEMPLATES = [
  { id: "ecommerce", name: "E-commerce", icon: ShoppingCart, desc: "Mobile shopping app", features: ["Product Catalog", "Cart", "Payments", "Orders", "Push Notifications"], platforms: ["flutter", "react-native"] },
  { id: "social", name: "Social", icon: MessageCircle, desc: "Social networking app", features: ["Feed", "Profiles", "Messaging", "Stories", "Groups"], platforms: ["flutter", "react-native"] },
  { id: "blog", name: "Blog", icon: BookOpen, desc: "Content & blog app", features: ["Articles", "Categories", "Comments", "Bookmarks"], platforms: ["flutter", "react-native"] },
  { id: "portfolio", name: "Portfolio", icon: Layout, desc: "Showcase & portfolio", features: ["Projects", "Gallery", "Contact Form", "Resume"], platforms: ["flutter", "react-native"] },
  { id: "crm", name: "CRM", icon: Briefcase, desc: "Mobile CRM", features: ["Contacts", "Deals", "Tasks", "Pipeline", "Reports"], platforms: ["flutter"] },
  { id: "booking", name: "Booking", icon: Calendar, desc: "Appointment booking", features: ["Calendar", "Slots", "Reminders", "Payments"], platforms: ["flutter", "react-native"] },
  { id: "food", name: "Food", icon: Utensils, desc: "Food delivery app", features: ["Menu", "Cart", "Tracking", "Ratings", "Promos"], platforms: ["flutter", "react-native"] },
  { id: "fitness", name: "Fitness", icon: Dumbbell, desc: "Fitness tracker", features: ["Workouts", "Progress", "Goals", "Social"], platforms: ["flutter"] },
];

function FileTreeView({ tree, selectedFile, onSelect }) {
  if (!tree) return null;
  const renderNode = (node, path = "") => {
    if (typeof node === "string") {
      const fullPath = path ? `${path}/${node}` : node;
      return (
        <div key={fullPath} className={`flex items-center gap-1.5 px-2 py-1 text-xs cursor-pointer rounded ${selectedFile === fullPath ? "bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`}
          onClick={() => onSelect(fullPath)}>
          <FileCode2 className="h-3 w-3 flex-shrink-0"/>{node}
        </div>
      );
    }
    return Object.entries(node).map(([name, val]) => (
      <div key={name}>
        <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-semibold">
          {typeof val === "object" ? <FolderOpen className="h-3 w-3 text-amber-500"/> : <FileCode2 className="h-3 w-3"/>}
          {name}
        </div>
        {typeof val === "object" && (
          <div className="ml-3">
            {Object.entries(val).map(([k, v]) => renderNode(v, path ? `${path}/${name}` : name))}
          </div>
        )}
      </div>
    ));
  };
  return <div className="space-y-0.5">{renderNode(tree)}</div>;
}

export default function MobileBuilder() {
  const [tab, setTab] = useState("templates");
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [fileTree, setFileTree] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [appName, setAppName] = useState("");
  const [platform, setPlatform] = useState("flutter");
  const [template, setTemplate] = useState("");
  const [features, setFeatures] = useState([]);
  const [backendUrl, setBackendUrl] = useState("");
  const [generating, setGenerating] = useState(false);

  const [screenName, setScreenName] = useState("");

  const load = async () => {
    setError(false);
    try {
      const r = await api.get("/admin/mobile-builder/projects").catch(() => ({ data: { items: [] } }));
      setProjects(r.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const loadProject = async (id) => {
    try {
      const r = await api.get(`/admin/mobile-builder/projects/${id}`);
      setSelectedProject(r.data);
      setFileTree(r.data?.file_tree || null);
      setTab("files");
    } catch { /* silent */ }
  };

  const loadFile = async (filePath) => {
    if (!selectedProject) return;
    try {
      const r = await api.get(`/admin/mobile-builder/projects/${selectedProject.id}/file?path=${encodeURIComponent(filePath)}`);
      setFileContent(r.data?.content || "");
      setSelectedFile(filePath);
    } catch { /* silent */ }
  };

  const generateProject = async () => {
    if (!appName.trim()) return;
    setGenerating(true);
    try {
      const r = await api.post("/admin/mobile-builder/generate", {
        app_name: appName, platform, template, features, backend_url: backendUrl,
      });
      setProjects(prev => [...prev, r.data?.item].filter(Boolean));
      setAppName("");
      setTemplate("");
      setFeatures([]);
      setBackendUrl("");
      setTab("projects");
    } catch { /* silent */ }
    setGenerating(false);
  };

  const buildProject = async (id) => {
    try {
      await api.post(`/admin/mobile-builder/projects/${id}/build`);
      setProjects(prev => prev.map(p => p.id === id ? { ...p, status: "building" } : p));
    } catch { /* silent */ }
  };

  const addScreen = async () => {
    if (!screenName.trim() || !selectedProject) return;
    try {
      await api.post(`/admin/mobile-builder/projects/${selectedProject.id}/add-screen`, { name: screenName });
      const r = await api.get(`/admin/mobile-builder/projects/${selectedProject.id}`);
      setSelectedProject(r.data);
      setFileTree(r.data?.file_tree || null);
      setScreenName("");
    } catch { /* silent */ }
  };

  const toggleFeature = (f) => {
    setFeatures(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  const selectedTemplate = TEMPLATES.find(t => t.id === template);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Mobile Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Generate Flutter & React Native apps with AI</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="generate">Generate</TabsTrigger>
          <TabsTrigger value="projects">Projects ({projects.length})</TabsTrigger>
          {selectedProject && <TabsTrigger value="files">Files</TabsTrigger>}
        </TabsList>

        {/* Templates Gallery */}
        <TabsContent value="templates" className="mt-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {TEMPLATES.map(t => (
              <Card key={t.id}
                className={`p-5 cursor-pointer hover:shadow-md transition-all ${template === t.id ? "ring-2 ring-[var(--gs-teal)]" : ""}`}
                onClick={() => { setTemplate(t.id); setTab("generate"); }}>
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                    <t.icon className="h-5 w-5 text-[var(--gs-teal)]"/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm">{t.name}</h3>
                    <p className="text-[11px] text-[var(--gs-muted)] mt-0.5">{t.desc}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {t.features.slice(0, 3).map(f => (
                        <Badge key={f} variant="outline" className="text-[9px]">{f}</Badge>
                      ))}
                      {t.features.length > 3 && <Badge variant="outline" className="text-[9px]">+{t.features.length - 3}</Badge>}
                    </div>
                    <div className="flex items-center gap-1.5 mt-2">
                      {t.platforms.includes("flutter") && (
                        <Badge className="bg-blue-100 text-blue-700 text-[8px]">Flutter</Badge>
                      )}
                      {t.platforms.includes("react-native") && (
                        <Badge className="bg-cyan-100 text-cyan-700 text-[8px]">React Native</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Generate Form */}
        <TabsContent value="generate" className="mt-4">
          <Card className="p-5 max-w-2xl">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-[var(--gs-teal)]"/>Generate Mobile App
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">App Name</label>
                <Input className="mt-1" placeholder="e.g. MyStore" value={appName} onChange={e => setAppName(e.target.value)}/>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Platform</label>
                <div className="flex gap-2 mt-1">
                  <Button variant={platform === "flutter" ? "default" : "outline"} size="sm" className="h-8" onClick={() => setPlatform("flutter")}>
                    <Smartphone className="h-3 w-3 mr-1"/>Flutter
                  </Button>
                  <Button variant={platform === "react-native" ? "default" : "outline"} size="sm" className="h-8" onClick={() => setPlatform("react-native")}>
                    <Smartphone className="h-3 w-3 mr-1"/>React Native
                  </Button>
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Template</label>
                <Select value={template} onValueChange={setTemplate}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Select template"/></SelectTrigger>
                  <SelectContent>
                    {TEMPLATES.filter(t => t.platforms.includes(platform)).map(t => (
                      <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {selectedTemplate && (
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Features</label>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    {selectedTemplate.features.map(f => (
                      <label key={f} className="flex items-center gap-2 text-xs cursor-pointer">
                        <Checkbox checked={features.includes(f)} onCheckedChange={() => toggleFeature(f)}/>
                        {f}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Backend URL</label>
                <Input className="mt-1" placeholder="https://api.example.com" value={backendUrl} onChange={e => setBackendUrl(e.target.value)}/>
              </div>

              <Button className="bg-[var(--gs-teal)] w-full" onClick={generateProject} disabled={generating || !appName.trim()}>
                {generating ? "Generating…" : "Generate App"}
              </Button>
            </div>
          </Card>
        </TabsContent>

        {/* Projects List */}
        <TabsContent value="projects" className="mt-4">
          {projects.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Smartphone className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi projects nahi — Generate tab se naya banao
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {projects.map((p, i) => (
                <Card key={p.id || i} className="p-5 hover:shadow-md transition-all cursor-pointer" onClick={() => loadProject(p.id)}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-sm">{p.app_name || p.name}</h3>
                      <p className="text-[11px] text-[var(--gs-muted)]">{p.template} template</p>
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${
                      p.status === "live" ? "text-emerald-600" :
                      p.status === "building" ? "text-blue-600" :
                      "text-[var(--gs-muted)]"
                    }`}>{p.status || "draft"}</Badge>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <Badge className={p.platform === "flutter" ? "bg-blue-100 text-blue-700 text-[9px]" : "bg-cyan-100 text-cyan-700 text-[9px]"}>
                      {p.platform}
                    </Badge>
                    <span className="text-[10px] text-[var(--gs-muted)]">{p.file_count ?? 0} files</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="h-7 text-[10px] flex-1" onClick={(e) => { e.stopPropagation(); loadProject(p.id); }}>
                      <Eye className="h-3 w-3 mr-1"/>View
                    </Button>
                    <Button variant="outline" size="sm" className="h-7 text-[10px] flex-1" onClick={(e) => { e.stopPropagation(); buildProject(p.id); }}>
                      <Rocket className="h-3 w-3 mr-1"/>Build
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Files View */}
        <TabsContent value="files" className="mt-4">
          <div className="grid lg:grid-cols-[250px_1fr] gap-4">
            <Card className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-xs">File Tree</h3>
              </div>
              {fileTree ? (
                <FileTreeView tree={fileTree} selectedFile={selectedFile} onSelect={loadFile}/>
              ) : (
                <div className="text-[var(--gs-muted)] text-xs">Loading file tree…</div>
              )}

              <div className="mt-4 pt-3 border-t" style={{ borderColor: "var(--gs-border)" }}>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Add Screen</label>
                <div className="flex gap-1.5 mt-1">
                  <Input className="h-7 text-xs" placeholder="Screen name" value={screenName} onChange={e => setScreenName(e.target.value)}/>
                  <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={addScreen} disabled={!screenName.trim()}>
                    <Plus className="h-3 w-3"/>
                  </Button>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              {selectedFile ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono text-[var(--gs-muted)]">{selectedFile}</span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" className="h-7 text-[10px]">
                        <Wand2 className="h-3 w-3 mr-1"/>AI Enhance
                      </Button>
                      <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]">
                        <Download className="h-3 w-3 mr-1"/>Save
                      </Button>
                    </div>
                  </div>
                  <Textarea value={fileContent} onChange={e => setFileContent(e.target.value)}
                    className="font-mono text-xs min-h-[400px] bg-black text-green-400 border-none"/>
                </div>
              ) : (
                <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
                  <FileCode2 className="h-8 w-8 mx-auto mb-2 opacity-30"/>Select a file to view
                </div>
              )}
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
