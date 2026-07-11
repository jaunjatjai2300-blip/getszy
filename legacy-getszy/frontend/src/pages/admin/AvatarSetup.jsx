import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import {
  Bot, Cpu, Zap, CheckCircle2, AlertTriangle, Copy,
  Monitor, Layers, Mic, Video, Image, RefreshCw
} from "lucide-react";

function CopyBlock({ code }) {
  return (
    <div className="relative group">
      <pre className="text-[11px] font-mono bg-[#0f172a] text-green-300 rounded-xl p-4 overflow-x-auto leading-relaxed whitespace-pre-wrap">{code}</pre>
      <button
        onClick={() => { navigator.clipboard.writeText(code); toast.success("Copied!"); }}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white/10 hover:bg-white/20 rounded-lg p-1.5"
      ><Copy className="h-3.5 w-3.5 text-white"/></button>
    </div>
  );
}

function ModelCard({ icon: Icon, name, desc, free, needsGpu, status, vram }) {
  const ready = status === "ready";
  const needsSetup = status === "needs_key";
  return (
    <Card className="p-4 flex gap-4 items-start">
      <div className={`h-10 w-10 rounded-xl grid place-items-center flex-shrink-0 ${ready ? "bg-[var(--gs-teal-soft)]" : needsGpu ? "bg-amber-50" : "bg-violet-50"}`}>
        <Icon className={`h-5 w-5 ${ready ? "text-[var(--gs-teal)]" : needsGpu ? "text-amber-600" : "text-violet-600"}`}/>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-sm">{name}</span>
          {free && <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">Free</Badge>}
          {needsGpu && <Badge className="bg-amber-100 text-amber-700 text-[10px]">GPU req</Badge>}
          {vram && <Badge className="bg-slate-100 text-slate-600 text-[10px]">{vram} VRAM</Badge>}
        </div>
        <p className="text-xs text-[var(--gs-muted)] mt-0.5">{desc}</p>
      </div>
      <div>
        {ready
          ? <Badge className="bg-emerald-100 text-emerald-700 text-xs"><CheckCircle2 className="h-3 w-3 mr-1"/>Active</Badge>
          : needsGpu
          ? <Badge className="bg-amber-100 text-amber-700 text-xs"><AlertTriangle className="h-3 w-3 mr-1"/>GPU needed</Badge>
          : <Badge className="bg-violet-100 text-violet-700 text-xs">Add HF_TOKEN</Badge>
        }
      </div>
    </Card>
  );
}

export default function AvatarSetup() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gpuData, setGpuData] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [avatarR, sysR] = await Promise.allSettled([
        api.get("/avatar/status"),
        api.get("/admin/system-stats"),
      ]);
      if (avatarR.status === "fulfilled") setStatus(avatarR.value.data);
      if (sysR.status === "fulfilled") setGpuData(sysR.value.data?.gpu);
    } catch (e) {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const providers = status?.providers || {};
  const hfActive = !!providers.flux_images;
  const sadtalkerActive = !!providers.sadtalker;
  const xttsActive = !!providers.xtts;
  const cogvideoActive = !!providers.cogvideo;

  const models = [
    {
      icon: Image, name: "FLUX.1-schnell", desc: "HD image generation — free via HuggingFace API. Just set HF_TOKEN.",
      free: true, needsGpu: false, vram: null, status: hfActive ? "ready" : "needs_key",
    },
    {
      icon: Mic, name: "XTTS v2 (Coqui)", desc: "Multilingual voice clone — runs locally, needs 8GB+ VRAM.",
      free: true, needsGpu: true, vram: "8GB+", status: xttsActive ? "ready" : "gpu_needed",
    },
    {
      icon: Bot, name: "SadTalker", desc: "Photo → talking avatar video — 4GB VRAM minimum.",
      free: true, needsGpu: true, vram: "4GB+", status: sadtalkerActive ? "ready" : "gpu_needed",
    },
    {
      icon: Video, name: "CogVideoX-5b", desc: "Text → AI video clip — heavy model, needs 24GB VRAM.",
      free: true, needsGpu: true, vram: "24GB+", status: cogvideoActive ? "ready" : "gpu_needed",
    },
  ];

  return (
    <div className="space-y-7" data-testid="avatar-setup-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2">
            <Bot className="h-7 w-7 text-[var(--gs-teal)]"/>Avatar Studio — VPS Setup
          </h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">
            GPU models (XTTS, SadTalker, CogVideoX) + FLUX free-tier status
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}/>Refresh
        </Button>
      </div>

      {/* GPU detection banner */}
      <Card className={`p-4 flex items-center gap-4 ${gpuData ? "border-emerald-300 bg-emerald-50" : "border-amber-300 bg-amber-50"}`}>
        <Monitor className={`h-6 w-6 ${gpuData ? "text-emerald-600" : "text-amber-600"}`}/>
        <div className="flex-1">
          {gpuData ? (
            <>
              <div className="font-semibold text-emerald-800">GPU Detected ✅</div>
              <div className="text-xs text-emerald-700">{gpuData.name} · VRAM: {gpuData.vram_total} (Free: {gpuData.vram_free})</div>
            </>
          ) : (
            <>
              <div className="font-semibold text-amber-800">No GPU detected on this host</div>
              <div className="text-xs text-amber-700">GPU models need CUDA. FLUX HD images work via HuggingFace API (no GPU needed).</div>
            </>
          )}
        </div>
        {gpuData
          ? <Badge className="bg-emerald-200 text-emerald-800">CUDA ready</Badge>
          : <Badge className="bg-amber-200 text-amber-800">CPU only</Badge>
        }
      </Card>

      {/* Model cards */}
      <div>
        <h2 className="font-display text-xl mb-3 flex items-center gap-2"><Layers className="h-5 w-5 text-[var(--gs-teal)]"/>Model Status</h2>
        <div className="grid md:grid-cols-2 gap-3">
          {models.map(m => <ModelCard key={m.name} {...m}/>)}
        </div>
      </div>

      {/* Step 1: HF_TOKEN (no GPU needed) */}
      <Card className="p-5 space-y-3">
        <h3 className="font-semibold flex items-center gap-2">
          <Zap className="h-4 w-4 text-[var(--gs-teal)]"/>
          Step 1 — Enable FLUX HD Images (no GPU needed)
          {hfActive && <Badge className="bg-emerald-100 text-emerald-700 text-xs ml-auto">✓ Done</Badge>}
        </h3>
        <p className="text-sm text-[var(--gs-muted)]">
          Register free at <span className="font-mono text-[var(--gs-teal)]">huggingface.co</span> → Settings → Access Tokens → New Token (read scope). Then set on VPS:
        </p>
        <CopyBlock code={`# On VPS terminal:\necho 'HF_TOKEN=hf_yourTokenHere' >> /opt/getszy/.env\ndocker compose restart getszy-backend`}/>
        <p className="text-xs text-[var(--gs-muted)]">This unlocks FLUX.1-schnell HD images immediately — no GPU required.</p>
      </Card>

      {/* Step 2: GPU install */}
      <Card className="p-5 space-y-3">
        <h3 className="font-semibold flex items-center gap-2">
          <Cpu className="h-4 w-4 text-amber-600"/>
          Step 2 — Install NVIDIA CUDA on VPS (for SadTalker + XTTS + CogVideoX)
        </h3>
        <p className="text-sm text-[var(--gs-muted)]">
          Your VPS needs a GPU (NVIDIA recommended). Minimum: <strong>RTX 3060 / 4060 (8GB VRAM)</strong> for XTTS + SadTalker.
          CogVideoX needs 24GB+ — optional.
        </p>

        <div className="space-y-3">
          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider">2a. Install NVIDIA drivers + CUDA toolkit</p>
          <CopyBlock code={`# Ubuntu 22.04 VPS — run as root
apt-get update && apt-get install -y nvidia-driver-535 cuda-toolkit-12-2
reboot

# After reboot — verify:
nvidia-smi`}/>

          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider mt-4">2b. Install NVIDIA Container Toolkit (Docker GPU passthrough)</p>
          <CopyBlock code={`curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update && apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker`}/>

          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider mt-4">2c. Enable GPU in docker-compose.yml</p>
          <CopyBlock code={`# In /opt/getszy/docker-compose.yml, add to getszy-backend service:
services:
  getszy-backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]`}/>

          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wider mt-4">2d. Install Python GPU dependencies</p>
          <CopyBlock code={`# In Dockerfile, add before pip install:
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# SadTalker model weights (auto-downloaded on first run):
RUN pip install sadtalker

# XTTS v2 (Coqui):
RUN pip install TTS

# Then rebuild:
cd /opt/getszy && docker compose up -d --build`}/>
        </div>
      </Card>

      {/* Step 3: Cost estimate */}
      <Card className="p-5 space-y-3">
        <h3 className="font-semibold flex items-center gap-2">
          <Video className="h-4 w-4 text-violet-600"/>
          Step 3 — Recommended VPS GPU options (India)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[var(--gs-muted)] border-b" style={{ borderColor: "var(--gs-border)" }}>
                <th className="pb-2 pr-4">Provider</th>
                <th className="pb-2 pr-4">GPU</th>
                <th className="pb-2 pr-4">VRAM</th>
                <th className="pb-2 pr-4">Cost</th>
                <th className="pb-2">Models supported</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--gs-border)" }}>
              {[
                { p: "RunPod.io",    gpu: "RTX 4060",    vram: "8GB",  cost: "~₹7/hr",   models: "XTTS + SadTalker" },
                { p: "Vast.ai",      gpu: "RTX 3090",    vram: "24GB", cost: "~₹15/hr",  models: "All models incl. CogVideoX" },
                { p: "Lambda Labs",  gpu: "A10",         vram: "24GB", cost: "$0.75/hr",  models: "All models" },
                { p: "Scaleway",     gpu: "NVIDIA H100", vram: "80GB", cost: "€2.49/hr", models: "All + 2× concurrent" },
              ].map(r => (
                <tr key={r.p} className="text-sm">
                  <td className="py-2 pr-4 font-medium">{r.p}</td>
                  <td className="py-2 pr-4 text-[var(--gs-muted)]">{r.gpu}</td>
                  <td className="py-2 pr-4"><Badge className="text-[10px] bg-slate-100 text-slate-700">{r.vram}</Badge></td>
                  <td className="py-2 pr-4 font-mono text-xs">{r.cost}</td>
                  <td className="py-2 text-xs text-[var(--gs-muted)]">{r.models}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-[var(--gs-muted)]">
          💡 Tip: Use RunPod spot instance (₹2-5/hr) for testing. Upgrade to dedicated when production volume increases.
          FLUX HD images work without any GPU via free HuggingFace API.
        </p>
      </Card>
    </div>
  );
}
