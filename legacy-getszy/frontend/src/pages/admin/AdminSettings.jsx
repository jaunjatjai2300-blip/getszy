import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Building2, Wand2, ShoppingBag, Webhook, Globe, Mail, Palette, Shield, CheckCircle2, Flag, RefreshCw, ToggleLeft, ToggleRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

function FieldGroup({ label, children }) {
  return (
    <div>
      <label className="text-xs font-medium text-[var(--gs-muted)]">{label}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

const DEFAULT_WORKSPACE = {
  business_name: "Getszy",
  website: "https://getszy.com",
  admin_email: "",
  country: "India",
  currency: "INR (₹)",
  timezone: "Asia/Kolkata",
};

const DEFAULT_BRANDING = {
  brand_name: "Getszy",
  tagline: "India ka AI Business OS",
  primary_color: "#2F7E7A",
  logo_url: "",
};

const DEFAULT_FLAGS = {
  video_factory: true,
  avatar_studio: true,
  app_builder: true,
  social_scheduler: true,
  cj_dropshipping: false,
  shiprocket: false,
  affiliate_program: false,
  team_accounts: false,
};

export default function AdminSettings() {
  const [workspace,   setWorkspace]   = useState(DEFAULT_WORKSPACE);
  const [branding,    setBranding]    = useState(DEFAULT_BRANDING);
  const [flags,       setFlags]       = useState(DEFAULT_FLAGS);
  const [emailCfg,    setEmailCfg]    = useState({ smtp_host: "", smtp_port: "587", smtp_user: "", from_name: "Getszy" });
  const [saving,      setSaving]      = useState("");
  const [loading,     setLoading]     = useState(true);

  const loadAll = useCallback(async () => {
    setLoading(true);
    const sections = ["workspace", "branding", "feature_flags", "email"];
    const results = await Promise.allSettled(sections.map(s => api.get(`/admin/settings?section=${s}`)));
    const [ws, br, ff, em] = results;
    if (ws.status === "fulfilled" && ws.value.data?.data) setWorkspace(d => ({...d, ...ws.value.data.data}));
    if (br.status === "fulfilled" && br.value.data?.data) setBranding(d => ({...d, ...br.value.data.data}));
    if (ff.status === "fulfilled" && ff.value.data?.data) setFlags(d => ({...d, ...ff.value.data.data}));
    if (em.status === "fulfilled" && em.value.data?.data) setEmailCfg(d => ({...d, ...em.value.data.data}));
    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const save = async (section, data) => {
    setSaving(section);
    try {
      await api.post("/admin/settings", { section, data });
      toast.success(`${section} settings saved!`);
    } catch (e) {
      toast.error("Save failed");
    } finally { setSaving(""); }
  };

  const toggleFlag = (key) => setFlags(f => ({ ...f, [key]: !f[key] }));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-3xl">Settings</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Workspace, branding, feature flags, email — sab saved in DB</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadAll} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Reload
        </Button>
      </div>

      <Tabs defaultValue="workspace">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="workspace"><Building2 className="h-3.5 w-3.5 mr-1"/>Workspace</TabsTrigger>
          <TabsTrigger value="branding"><Palette className="h-3.5 w-3.5 mr-1"/>Branding</TabsTrigger>
          <TabsTrigger value="flags"><Flag className="h-3.5 w-3.5 mr-1"/>Feature Flags</TabsTrigger>
          <TabsTrigger value="email"><Mail className="h-3.5 w-3.5 mr-1"/>Email</TabsTrigger>
          <TabsTrigger value="billing"><ShoppingBag className="h-3.5 w-3.5 mr-1"/>Billing</TabsTrigger>
          <TabsTrigger value="integrations"><Webhook className="h-3.5 w-3.5 mr-1"/>Integrations</TabsTrigger>
        </TabsList>

        {/* ── Workspace ── */}
        <TabsContent value="workspace" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><Building2 className="h-5 w-5 text-[var(--gs-teal)]"/>Workspace</h3>
            <div className="space-y-3">
              <FieldGroup label="Business Name">
                <Input value={workspace.business_name} onChange={e => setWorkspace(s => ({...s, business_name: e.target.value}))}/>
              </FieldGroup>
              <FieldGroup label="Website">
                <Input value={workspace.website} onChange={e => setWorkspace(s => ({...s, website: e.target.value}))}/>
              </FieldGroup>
              <FieldGroup label="Admin Email">
                <Input type="email" value={workspace.admin_email} onChange={e => setWorkspace(s => ({...s, admin_email: e.target.value}))} placeholder="admin@getszy.com"/>
              </FieldGroup>
              <div className="grid grid-cols-2 gap-3">
                <FieldGroup label="Country">
                  <Input value={workspace.country} onChange={e => setWorkspace(s => ({...s, country: e.target.value}))}/>
                </FieldGroup>
                <FieldGroup label="Currency">
                  <Input value={workspace.currency} onChange={e => setWorkspace(s => ({...s, currency: e.target.value}))}/>
                </FieldGroup>
              </div>
              <FieldGroup label="Timezone">
                <Input value={workspace.timezone} onChange={e => setWorkspace(s => ({...s, timezone: e.target.value}))}/>
              </FieldGroup>
            </div>
            <Button onClick={() => save("workspace", workspace)} disabled={saving === "workspace"} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {saving === "workspace" ? <RefreshCw className="h-4 w-4 mr-1 animate-spin"/> : <CheckCircle2 className="h-4 w-4 mr-1"/>}Save Workspace
            </Button>
          </Card>
        </TabsContent>

        {/* ── Branding ── */}
        <TabsContent value="branding" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><Palette className="h-5 w-5 text-[var(--gs-teal)]"/>Branding</h3>
            <div className="space-y-3">
              <FieldGroup label="Brand Name">
                <Input value={branding.brand_name} onChange={e => setBranding(s => ({...s, brand_name: e.target.value}))}/>
              </FieldGroup>
              <FieldGroup label="Tagline">
                <Input value={branding.tagline} onChange={e => setBranding(s => ({...s, tagline: e.target.value}))}/>
              </FieldGroup>
              <FieldGroup label="Primary Color">
                <div className="flex items-center gap-2">
                  <Input value={branding.primary_color} onChange={e => setBranding(s => ({...s, primary_color: e.target.value}))} placeholder="#hex"/>
                  <input type="color" value={branding.primary_color} onChange={e => setBranding(s => ({...s, primary_color: e.target.value}))}
                    className="h-9 w-12 rounded-lg border cursor-pointer p-1"/>
                </div>
              </FieldGroup>
              <FieldGroup label="Logo URL">
                <Input value={branding.logo_url} onChange={e => setBranding(s => ({...s, logo_url: e.target.value}))} placeholder="https://..."/>
              </FieldGroup>
            </div>
            <Button onClick={() => save("branding", branding)} disabled={saving === "branding"} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {saving === "branding" ? <RefreshCw className="h-4 w-4 mr-1 animate-spin"/> : <CheckCircle2 className="h-4 w-4 mr-1"/>}Save Branding
            </Button>
          </Card>
        </TabsContent>

        {/* ── Feature Flags ── */}
        <TabsContent value="flags" className="mt-4">
          <Card className="p-5 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2 mb-4"><Flag className="h-5 w-5 text-[var(--gs-teal)]"/>Feature Flags</h3>
            <p className="text-xs text-[var(--gs-muted)] mb-4">Features on/off karo — saved in DB, reflects across app instantly.</p>
            <div className="space-y-3">
              {[
                { key: "video_factory",     label: "Video Factory",        desc: "Kling-style video pipeline" },
                { key: "avatar_studio",     label: "Avatar Studio",        desc: "FLUX images + XTTS + SadTalker" },
                { key: "app_builder",       label: "App Builder",          desc: "Prompt → app generator" },
                { key: "social_scheduler",  label: "Social Scheduler",     desc: "Auto-post to platforms" },
                { key: "cj_dropshipping",   label: "CJ Dropshipping",      desc: "Requires CJ API keys" },
                { key: "shiprocket",        label: "Shiprocket",           desc: "Requires Shiprocket credentials" },
                { key: "affiliate_program", label: "Affiliate Program",    desc: "User referral tracking" },
                { key: "team_accounts",     label: "Team Accounts",        desc: "Multi-user workspaces" },
              ].map(f => (
                <div key={f.key} className="flex items-center justify-between p-3 rounded-xl bg-[var(--gs-surface-2)]">
                  <div>
                    <div className="text-sm font-semibold">{f.label}</div>
                    <div className="text-[10px] text-[var(--gs-muted)]">{f.desc}</div>
                  </div>
                  <button onClick={() => toggleFlag(f.key)} className="flex-shrink-0">
                    {flags[f.key]
                      ? <ToggleRight className="h-7 w-7 text-[var(--gs-teal)]"/>
                      : <ToggleLeft className="h-7 w-7 text-[var(--gs-muted)]"/>
                    }
                  </button>
                </div>
              ))}
            </div>
            <Button className="mt-4 bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 w-full" onClick={() => save("feature_flags", flags)} disabled={saving === "feature_flags"}>
              {saving === "feature_flags" ? <RefreshCw className="h-4 w-4 mr-1 animate-spin"/> : <CheckCircle2 className="h-4 w-4 mr-1"/>}Save Flags
            </Button>
          </Card>
        </TabsContent>

        {/* ── Email ── */}
        <TabsContent value="email" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><Mail className="h-5 w-5 text-[var(--gs-teal)]"/>Email Configuration</h3>
            <p className="text-xs text-[var(--gs-muted)]">Transactional email ke liye SMTP configure karo (Gmail / SendGrid / Mailgun).</p>
            <div className="space-y-3">
              <FieldGroup label="SMTP Host">
                <Input value={emailCfg.smtp_host} onChange={e => setEmailCfg(s => ({...s, smtp_host: e.target.value}))} placeholder="smtp.gmail.com"/>
              </FieldGroup>
              <div className="grid grid-cols-2 gap-3">
                <FieldGroup label="SMTP Port">
                  <Input value={emailCfg.smtp_port} onChange={e => setEmailCfg(s => ({...s, smtp_port: e.target.value}))} placeholder="587"/>
                </FieldGroup>
                <FieldGroup label="From Name">
                  <Input value={emailCfg.from_name} onChange={e => setEmailCfg(s => ({...s, from_name: e.target.value}))} placeholder="Getszy"/>
                </FieldGroup>
              </div>
              <FieldGroup label="SMTP Username">
                <Input value={emailCfg.smtp_user} onChange={e => setEmailCfg(s => ({...s, smtp_user: e.target.value}))} placeholder="you@gmail.com"/>
              </FieldGroup>
            </div>
            <p className="text-[10px] text-[var(--gs-muted)]">Note: SMTP password ko .env mein SMTP_PASSWORD key se set karo — yahan enter mat karo.</p>
            <Button onClick={() => save("email", emailCfg)} disabled={saving === "email"} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {saving === "email" ? <RefreshCw className="h-4 w-4 mr-1 animate-spin"/> : <CheckCircle2 className="h-4 w-4 mr-1"/>}Save Email Config
            </Button>
          </Card>
        </TabsContent>

        {/* ── Billing ── */}
        <TabsContent value="billing" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><ShoppingBag className="h-5 w-5 text-[var(--gs-teal)]"/>Billing & Plans</h3>
            <div className="space-y-3">
              {[
                { name: "Lite Pack",  price: "₹199",  credits: 100, color: "bg-slate-50 border-slate-200" },
                { name: "Pro Pack",   price: "₹499",  credits: 300, color: "bg-blue-50 border-blue-200" },
                { name: "Ultra Pack", price: "₹999",  credits: 700, color: "bg-violet-50 border-violet-200" },
              ].map(plan => (
                <div key={plan.name} className={`p-3 rounded-xl border ${plan.color} flex items-center justify-between`}>
                  <div>
                    <div className="font-semibold text-sm">{plan.name}</div>
                    <div className="text-xs text-[var(--gs-muted)]">{plan.credits} credits</div>
                  </div>
                  <div className="font-display text-xl">{plan.price}</div>
                </div>
              ))}
              <p className="text-xs text-[var(--gs-muted)] pt-2">Plans update karne ke liye Razorpay dashboard use karo ya backend <code className="font-mono text-[10px]">routes_razorpay.py</code> edit karo.</p>
            </div>
          </Card>
        </TabsContent>

        {/* ── Integrations ── */}
        <TabsContent value="integrations" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4 max-w-2xl">
            {[
              { name: "Razorpay",    desc: "Payment gateway — ₹ payments",      icon: ShoppingBag, status: "connected" },
              { name: "HuggingFace", desc: "FLUX images + XTTS voice clone",     icon: Wand2,       status: "connected" },
              { name: "Groq",        desc: "Fast LLM — script generation",       icon: Wand2,       status: "connected" },
              { name: "OpenRouter",  desc: "92 free AI models — backup LLM",     icon: Globe,       status: "connected" },
              { name: "MongoDB",     desc: "Database",                            icon: Shield,      status: "connected" },
              { name: "edge-tts",    desc: "Free Indian voices — TTS",           icon: Mail,        status: "connected" },
              { name: "fal.ai",      desc: "Premium GPU — FLUX faster (paid)",   icon: Wand2,       status: "optional" },
              { name: "SadTalker",   desc: "Talking avatar generation",          icon: Globe,       status: "optional" },
            ].map(intg => (
              <Card key={intg.name} className={`p-4 border ${intg.status === "connected" ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl bg-white grid place-items-center">
                    <intg.icon className="h-4 w-4 text-[var(--gs-teal)]"/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm">{intg.name}</div>
                    <div className="text-[10px] text-[var(--gs-muted)] truncate">{intg.desc}</div>
                  </div>
                  <Badge className={intg.status === "connected" ? "bg-emerald-100 text-emerald-700 text-[10px]" : "bg-amber-100 text-amber-700 text-[10px]"}>
                    {intg.status === "connected" ? "✓ Live" : "Optional"}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
