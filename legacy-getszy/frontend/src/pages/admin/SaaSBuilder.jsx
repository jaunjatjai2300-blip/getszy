import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Layout, Database, ShoppingCart, GraduationCap, Users, Calendar,
  Briefcase, Globe, Image, Code2, Rocket, Eye, Wand2, ChevronDown,
  ChevronRight, FileCode2, Folder, FolderOpen, RefreshCw, Plus,
  Settings, Download, CheckCircle2, Cpu, Zap, CreditCard, Server,
  Paintbrush, Search, Tag, Star
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const TEMPLATES = [
  { id: "crm", name: "CRM", icon: Users, desc: "Customer relationship management", features: ["Leads", "Deals", "Contacts", "Pipeline"] },
  { id: "erp", name: "ERP", icon: Briefcase, desc: "Enterprise resource planning", features: ["Inventory", "Accounting", "HR", "Procurement"] },
  { id: "lms", name: "LMS", icon: GraduationCap, desc: "Learning management system", features: ["Courses", "Quizzes", "Certificates", "Progress"] },
  { id: "hrms", name: "HRMS", icon: Users, desc: "Human resource management", features: ["Employees", "Payroll", "Attendance", "Leaves"] },
  { id: "ecommerce", name: "E-commerce", icon: ShoppingCart, desc: "Online store platform", features: ["Products", "Cart", "Payments", "Shipping"] },
  { id: "booking", name: "Booking", icon: Calendar, desc: "Appointment booking system", features: ["Calendar", "Slots", "Reminders", "Payments"] },
  { id: "marketplace", name: "Marketplace", icon: Globe, desc: "Multi-vendor marketplace", features: ["Vendors", "Products", "Commissions", "Payouts"] },
  { id: "social", name: "Social", icon: Globe, desc: "Social networking platform", features: ["Feed", "Profiles", "Messaging", "Groups"] },
  { id: "portfolio", name: "Portfolio", icon: Image, desc: "Portfolio & showcase site", features: ["Projects", "Gallery", "Blog", "Contact"] },
];

export default function SaaSBuilder() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [fileTree, setFileTree] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [tab, setTab] = useState("templates");

  const [genName, setGenName] = useState("");
  const [genTemplate, setGenTemplate] = useState("");
  const [genFeatures, setGenFeatures] = useState([]);
  const [genDatabase, setGenDatabase] = useState("mongodb");
  const [genFrontend, setGenFrontend] = useState("react");
  const [genAuth, setGenAuth] = useState("email");
  const [genPayment, setGenPayment] = useState("razorpay");
  const [genDeploy, setGenDeploy] = useState("vercel");
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    setError(false);
    try {
      const r = await api.get("/admin/saas-builder/projects").catch(() => ({ data: { items: [] } }));
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
      const r = await api.get(`/admin/saas-builder/projects/${id}`);
      setSelectedProject(r.data);
      setFileTree(r.data?.file_tree || null);
      setTab("files");
    } catch { /* silent */ }
  };

  const loadFile = async (projectId, filePath) => {
    try {
      const r = await api.get(`/admin/saas-builder/projects/${projectId}/file?path=${encodeURIComponent(filePath)}`);
      setFileContent(r.data?.content || "");
      setSelectedFile(filePath);
    } catch { /* silent */ }
  };

  const saveFile = async () => {
    if (!selectedProject || !selectedFile) return;
    try {
      await api.put(`/admin/saas-builder/projects/${selectedProject.id}/file`, { path: selectedFile, content: fileContent });
    } catch { /* silent */ }
  };

  const generateProject = async () => {
    if (!genName.trim()) return;
    setGenerating(true);
    try {
      const r = await api.post("/admin/saas-builder/generate", {
        name: genName, template: genTemplate, features: genFeatures,
        database: genDatabase, frontend: genFrontend, auth: genAuth,
        payment: genPayment, deploy: genDeploy,
      });
      setProjects(prev => [...prev, r.data?.item].filter(Boolean));
      setGenName("");
      setGenTemplate("");
      setGenFeatures([]);
      setTab("projects");
    } catch { /* silent */ }
    setGenerating(false);
  };

  const deployProject = async (id) => {
    try {
      await api.post(`/admin/saas-builder/projects/${id}/deploy`);
      setProjects(prev => prev.map(p => p.id === id ? { ...p, status: "deploying" } : p));
    } catch { /* silent */ }
  };

  const toggleGenFeature = (f) => {
    setGenFeatures(prev => prev.includes(f) ? prev.filter(x => x !== f) : [...prev, f]);
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  const selectedTemplate = TEMPLATES.find(t => t.id === genTemplate);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">SaaS Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Generate, customize & deploy full-stack SaaS projects</p>
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

        {/* Templates */}
        <TabsContent value="templates" className="mt-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {TEMPLATES.map(t => (
              <Card key={t.id}
                className={`p-5 cursor-pointer hover:shadow-md transition-all ${genTemplate === t.id ? "ring-2 ring-[var(--gs-teal)]" : ""}`}
                onClick={() => { setGenTemplate(t.id); setTab("generate"); }}>
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-xl bg-[var(--gs-teal)]/10 grid place-items-center flex-shrink-0">
                    <t.icon className="h-5 w-5 text-[var(--gs-teal)]"/>
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">{t.name}</h3>
                    <p className="text-[11px] text-[var(--gs-muted)] mt-0.5">{t.desc}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {t.features.map(f => (
                        <Badge key={f} variant="outline" className="text-[9px]">{f}</Badge>
                      ))}
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
              <Wand2 className="h-4 w-4 text-[var(--gs-teal)]"/>Generate Project
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Project Name</label>
                <Input className="mt-1" placeholder="e.g. My SaaS App" value={genName} onChange={e => setGenName(e.target.value)}/>
              </div>
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Template</label>
                <Select value={genTemplate} onValueChange={setGenTemplate}>
                  <SelectTrigger className="mt-1"><SelectValue placeholder="Select template"/></SelectTrigger>
                  <SelectContent>
                    {TEMPLATES.map(t => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {selectedTemplate && (
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Features</label>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    {selectedTemplate.features.map(f => (
                      <label key={f} className="flex items-center gap-2 text-xs cursor-pointer">
                        <Checkbox checked={genFeatures.includes(f)} onCheckedChange={() => toggleGenFeature(f)}/>
                        {f}
                      </label>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Database</label>
                  <Select value={genDatabase} onValueChange={setGenDatabase}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mongodb">MongoDB</SelectItem>
                      <SelectItem value="postgres">PostgreSQL</SelectItem>
                      <SelectItem value="mysql">MySQL</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Frontend</label>
                  <Select value={genFrontend} onValueChange={setGenFrontend}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="react">React</SelectItem>
                      <SelectItem value="nextjs">Next.js</SelectItem>
                      <SelectItem value="vue">Vue</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Auth</label>
                  <Select value={genAuth} onValueChange={setGenAuth}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="email">Email + Password</SelectItem>
                      <SelectItem value="google">Google OAuth</SelectItem>
                      <SelectItem value="both">Both</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Payment</label>
                  <Select value={genPayment} onValueChange={setGenPayment}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="razorpay">Razorpay</SelectItem>
                      <SelectItem value="stripe">Stripe</SelectItem>
                      <SelectItem value="none">None</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">Deploy</label>
                  <Select value={genDeploy} onValueChange={setGenDeploy}>
                    <SelectTrigger className="mt-1"><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vercel">Vercel</SelectItem>
                      <SelectItem value="netlify">Netlify</SelectItem>
                      <SelectItem value="docker">Docker</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button className="bg-[var(--gs-teal)] w-full" onClick={generateProject} disabled={generating}>
                {generating ? "Generating…" : "Generate Project"}
              </Button>
            </div>
          </Card>
        </TabsContent>

        {/* Projects List */}
        <TabsContent value="projects" className="mt-4">
          {projects.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Code2 className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi projects nahi — Generate tab se naya banao
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {projects.map((p, i) => (
                <Card key={p.id || i} className="p-5 hover:shadow-md transition-all cursor-pointer" onClick={() => loadProject(p.id)}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-sm">{p.name}</h3>
                      <p className="text-[11px] text-[var(--gs-muted)]">{p.template} template</p>
                    </div>
                    <Badge variant="outline" className={`text-[10px] ${
                      p.status === "live" ? "text-emerald-600" :
                      p.status === "deploying" ? "text-blue-600" :
                      "text-[var(--gs-muted)]"
                    }`}>{p.status || "draft"}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {(p.tech_stack || [p.frontend, p.database].filter(Boolean)).map(t => (
                      <Badge key={t} variant="outline" className="text-[9px]">{t}</Badge>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="h-7 text-[10px] flex-1" onClick={(e) => { e.stopPropagation(); loadProject(p.id); }}>
                      <Eye className="h-3 w-3 mr-1"/>View
                    </Button>
                    <Button variant="outline" size="sm" className="h-7 text-[10px] flex-1" onClick={(e) => { e.stopPropagation(); deployProject(p.id); }}>
                      <Rocket className="h-3 w-3 mr-1"/>Deploy
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
              <h3 className="font-semibold text-xs mb-3">File Tree</h3>
              {fileTree ? (
                <FileTreeView tree={fileTree} projectId={selectedProject?.id} onSelect={loadFile} selectedFile={selectedFile}/>
              ) : (
                <div className="text-[var(--gs-muted)] text-xs">Loading file tree…</div>
              )}
            </Card>
            <Card className="p-4">
              {selectedFile ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono text-[var(--gs-muted)]">{selectedFile}</span>
                    <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={saveFile}>Save</Button>
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

function FileTreeView({ tree, projectId, onSelect, selectedFile }) {
  if (!tree) return null;

  const renderNode = (node, path = "") => {
    if (typeof node === "string") {
      const fullPath = path ? `${path}/${node}` : node;
      return (
        <div key={fullPath} className={`flex items-center gap-1.5 px-2 py-1 text-xs cursor-pointer rounded ${selectedFile === fullPath ? "bg-[var(--gs-teal)]/10 text-[var(--gs-teal)]" : "hover:bg-[var(--gs-surface-2)]"}`}
          onClick={() => onSelect(projectId, fullPath)}>
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
