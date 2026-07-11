import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Building2, Wand2, ShoppingBag, Webhook, Globe, Mail, Palette, Shield, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function AdminSettings() {
  const [saved, setSaved] = useState(false);

  const save = () => {
    toast.success("Settings saved!");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Settings</h1>
        <p className="text-sm text-[var(--gs-muted)] mt-0.5">Workspace, branding, billing, aur integrations configure karo</p>
      </div>

      <Tabs defaultValue="workspace">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="workspace"><Building2 className="h-3.5 w-3.5 mr-1"/>Workspace</TabsTrigger>
          <TabsTrigger value="branding"><Palette className="h-3.5 w-3.5 mr-1"/>Branding</TabsTrigger>
          <TabsTrigger value="billing"><ShoppingBag className="h-3.5 w-3.5 mr-1"/>Billing</TabsTrigger>
          <TabsTrigger value="integrations"><Webhook className="h-3.5 w-3.5 mr-1"/>Integrations</TabsTrigger>
        </TabsList>

        <TabsContent value="workspace" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><Building2 className="h-5 w-5 text-[var(--gs-teal)]"/>Workspace</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Business Name</label>
                <Input defaultValue="Getszy" placeholder="Your business name"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Website</label>
                <Input defaultValue="https://getszy.com" placeholder="https://…"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Admin Email</label>
                <Input placeholder="admin@getszy.com" type="email"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Country</label>
                <Input defaultValue="India" placeholder="India"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Currency</label>
                <Input defaultValue="INR (₹)" placeholder="INR"/>
              </div>
            </div>
            <Button onClick={save} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
              {saved ? <><CheckCircle2 className="h-4 w-4 mr-1"/>Saved!</> : "Save Workspace"}
            </Button>
          </Card>
        </TabsContent>

        <TabsContent value="branding" className="mt-4">
          <Card className="p-5 space-y-4 max-w-lg">
            <h3 className="font-display text-lg flex items-center gap-2"><Palette className="h-5 w-5 text-[var(--gs-teal)]"/>Branding</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Brand Name</label>
                <Input defaultValue="Getszy" placeholder="Brand name"/>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Primary Color</label>
                <div className="flex items-center gap-2">
                  <Input defaultValue="#2F7E7A" placeholder="#hex"/>
                  <div className="h-9 w-9 rounded-lg border" style={{ background: "#2F7E7A" }}/>
                </div>
              </div>
              <div>
                <label className="text-xs text-[var(--gs-muted)]">Tagline</label>
                <Input defaultValue="India ka AI Business OS" placeholder="Your tagline"/>
              </div>
            </div>
            <Button onClick={save} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">Save Branding</Button>
          </Card>
        </TabsContent>

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
              <p className="text-xs text-[var(--gs-muted)]">Plans update karne ke liye Razorpay dashboard use karo ya backend routes_razorpay.py edit karo.</p>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="integrations" className="mt-4">
          <div className="grid md:grid-cols-2 gap-4 max-w-2xl">
            {[
              { name: "Razorpay",     desc: "Payment gateway — ₹ payments",       icon: ShoppingBag, status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "HuggingFace",  desc: "FLUX images + XTTS voice clone",      icon: Wand2,      status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "Groq",         desc: "Fast LLM — script generation",        icon: Wand2,      status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "OpenRouter",   desc: "92 free AI models — backup LLM",      icon: Globe,      status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "MongoDB",      desc: "Database",                             icon: Shield,     status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "edge-tts",     desc: "Free Indian voices — TTS",            icon: Mail,       status: "connected", color: "border-emerald-200 bg-emerald-50" },
              { name: "fal.ai",       desc: "Premium GPU — FLUX faster (paid)",    icon: Wand2,      status: "optional",  color: "border-amber-200 bg-amber-50" },
              { name: "SadTalker",    desc: "Talking avatar generation",           icon: Globe,      status: "optional",  color: "border-amber-200 bg-amber-50" },
            ].map(intg => (
              <Card key={intg.name} className={`p-4 border ${intg.color}`}>
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-xl bg-white grid place-items-center">
                    <intg.icon className="h-4 w-4 text-[var(--gs-teal)]"/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm">{intg.name}</div>
                    <div className="text-[10px] text-[var(--gs-muted)] truncate">{intg.desc}</div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${intg.status === "connected" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {intg.status === "connected" ? "✓ Live" : "Optional"}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
