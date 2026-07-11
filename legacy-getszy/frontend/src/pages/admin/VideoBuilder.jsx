import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Film, Plus, Trash2, Play, Download, Copy, Loader2, Sparkles, GripVertical } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

const SHOT_TYPES = ["Wide Shot","Medium Shot","Close-up","Extreme Close-up","Over-the-shoulder","POV","Bird's Eye","Low Angle"];
const TRANSITIONS = ["Cut","Fade","Dissolve","Wipe","Zoom"];
const VIDEO_STYLES = ["Corporate","Educational","Social Media Reel","Product Demo","Explainer","Documentary","Vlog","Cinematic"];

let _id = () => Math.random().toString(36).slice(2,8);

function SceneCard({ scene, index, onChange, onDelete }) {
  return (
    <div className="p-4 bg-[var(--gs-surface-2)] rounded-xl border border-[var(--gs-border)] space-y-3">
      <div className="flex items-center gap-2">
        <GripVertical className="h-4 w-4 text-[var(--gs-muted)] flex-shrink-0"/>
        <span className="text-xs font-bold text-[var(--gs-teal)] bg-[var(--gs-teal-soft)] px-2 py-0.5 rounded-full">Scene {index+1}</span>
        <Input value={scene.title} onChange={e=>onChange({...scene,title:e.target.value})} placeholder="Scene title…" className="h-7 text-xs flex-1"/>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400 hover:text-rose-600 flex-shrink-0" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/></Button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Select value={scene.shot} onValueChange={v=>onChange({...scene,shot:v})}>
          <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Shot type"/></SelectTrigger>
          <SelectContent>{SHOT_TYPES.map(s=><SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={scene.transition} onValueChange={v=>onChange({...scene,transition:v})}>
          <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Transition"/></SelectTrigger>
          <SelectContent>{TRANSITIONS.map(t=><SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <Textarea value={scene.visual} onChange={e=>onChange({...scene,visual:e.target.value})} placeholder="Visual description — kya dikhna chahiye screen pe…" rows={2} className="text-xs resize-none"/>
      <Textarea value={scene.voiceover} onChange={e=>onChange({...scene,voiceover:e.target.value})} placeholder="Voiceover / narration text…" rows={2} className="text-xs resize-none"/>
      <Input value={scene.duration} onChange={e=>onChange({...scene,duration:e.target.value})} placeholder="Duration (e.g. 5s, 10s)" className="h-7 text-xs"/>
    </div>
  );
}

export default function VideoBuilder() {
  const [title, setTitle] = useState("");
  const [style, setStyle] = useState("Explainer");
  const [topic, setTopic] = useState("");
  const [scenes, setScenes] = useState([
    { id:_id(), title:"Opening Hook", shot:"Close-up", transition:"Fade", visual:"", voiceover:"", duration:"5s" },
    { id:_id(), title:"Main Content", shot:"Wide Shot", transition:"Cut", visual:"", voiceover:"", duration:"15s" },
    { id:_id(), title:"Call to Action", shot:"Medium Shot", transition:"Fade", visual:"", voiceover:"", duration:"5s" },
  ]);
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState(false);

  const addScene = () => setScenes(s=>[...s,{ id:_id(), title:`Scene ${s.length+1}`, shot:"Medium Shot", transition:"Cut", visual:"", voiceover:"", duration:"5s" }]);
  const updateScene = (id,data) => setScenes(s=>s.map(x=>x.id===id?data:x));
  const deleteScene = id => setScenes(s=>s.filter(x=>x.id!==id));

  const totalDuration = () => {
    let total = 0;
    scenes.forEach(s => { const m = s.duration?.match(/(\d+)/); if(m) total += parseInt(m[1]); });
    return total;
  };

  const generateScript = async () => {
    if (!topic.trim()) { toast.error("Pehle topic likhein"); return; }
    setGenerating(true);
    try {
      const r = await api.post("/admin/ai-platform/playground", {
        model: "llama-3.1-8b-instant", provider: "groq",
        system: `You are a video scriptwriter for ${style} style videos. Write in Hinglish (Hindi+English mix). Be specific and visual.`,
        message: `Create a ${style} video script about: "${topic}"\n\nFor each of ${scenes.length} scenes, provide:\n- Scene title\n- Visual description (what to show on screen)\n- Voiceover text\n- Suggested duration\n\nFormat as JSON array with keys: title, visual, voiceover, duration`,
        temperature: 0.7, max_tokens: 1500
      });
      try {
        const text = r.data.response || "";
        const match = text.match(/\[[\s\S]*\]/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          setScenes(parsed.map((s,i) => ({ id:_id(), shot: SHOT_TYPES[i%SHOT_TYPES.length], transition: i===0?"Fade":"Cut", ...s, duration: s.duration||"8s" })));
          toast.success("Script generate ho gaya! Edit kar sakte ho");
        } else {
          toast.info("Script aa gayi — manually scenes fill karo");
        }
      } catch { toast.info("AI ne script di — parse error, manually fill karo"); }
    } catch { toast.error("AI unavailable — manually script likhein"); }
    finally { setGenerating(false); }
  };

  const exportScript = () => {
    const content = `VIDEO SCRIPT: ${title || "Untitled"}\nStyle: ${style} | Duration: ~${totalDuration()}s\n\n` +
      scenes.map((s,i) => `SCENE ${i+1}: ${s.title}\n━━━━━━━━━━━━━━━\nShot: ${s.shot} | Transition: ${s.transition} | Duration: ${s.duration}\n\nVISUAL:\n${s.visual||"(not set)"}\n\nVOICEOVER:\n${s.voiceover||"(not set)"}\n`).join("\n");
    const blob = new Blob([content], {type:"text/plain"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download=`${title||"video-script"}.txt`; a.click();
    toast.success("Script download ho gayi!");
  };

  const copyScript = () => {
    const content = scenes.map((s,i)=>`Scene ${i+1} - ${s.title}\nVisual: ${s.visual}\nVO: ${s.voiceover}`).join("\n\n");
    navigator.clipboard.writeText(content);
    toast.success("Script clipboard pe copy ho gayi!");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Film className="h-7 w-7 text-[var(--gs-teal)]"/>Video Script Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Scene-by-scene video script banao — AI se ya manually</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={copyScript}><Copy className="h-3.5 w-3.5 mr-1"/>Copy</Button>
          <Button variant="outline" size="sm" onClick={exportScript}><Download className="h-3.5 w-3.5 mr-1"/>Export .txt</Button>
          <Button size="sm" onClick={()=>setPreview(p=>!p)} style={{background:"var(--gs-teal)",color:"#fff"}}>
            <Play className="h-3.5 w-3.5 mr-1"/>{preview?"Edit":"Preview"}
          </Button>
        </div>
      </div>

      <Card className="p-4 space-y-4">
        <div className="grid md:grid-cols-3 gap-3">
          <Input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Video title…" className="h-9"/>
          <Select value={style} onValueChange={setStyle}>
            <SelectTrigger className="h-9"><SelectValue/></SelectTrigger>
            <SelectContent>{VIDEO_STYLES.map(s=><SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
          <div className="flex gap-2">
            <Input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Topic ya idea likhein…" className="h-9 flex-1"/>
            <Button onClick={generateScript} disabled={generating} size="sm" className="h-9 gap-1" style={{background:"var(--gs-teal)",color:"#fff"}}>
              {generating?<Loader2 className="h-3.5 w-3.5 animate-spin"/>:<Sparkles className="h-3.5 w-3.5"/>}
              {generating?"...":"AI"}
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-[var(--gs-muted)]">
          <Badge variant="outline">{scenes.length} scenes</Badge>
          <Badge variant="outline">~{totalDuration()}s total</Badge>
          <Badge variant="outline" className="capitalize">{style}</Badge>
        </div>
      </Card>

      {preview ? (
        <Card className="p-6 space-y-6 bg-[#0d0d0d] text-white">
          <h2 className="font-display text-2xl text-center">{title || "Video Script"}</h2>
          <p className="text-center text-gray-400 text-sm">{style} · ~{totalDuration()}s</p>
          {scenes.map((s,i) => (
            <div key={s.id} className="border border-gray-700 rounded-xl p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-400 bg-emerald-900/40 px-2 py-0.5 rounded-full">Scene {i+1}</span>
                <span className="font-semibold">{s.title}</span>
                <span className="text-xs text-gray-500 ml-auto">{s.shot} · {s.duration}</span>
              </div>
              {s.visual && <p className="text-xs text-blue-300 bg-blue-900/20 p-2 rounded-lg">📷 {s.visual}</p>}
              {s.voiceover && <p className="text-xs text-yellow-200 bg-yellow-900/20 p-2 rounded-lg">🎙 {s.voiceover}</p>}
              {s.transition && <p className="text-[10px] text-gray-500">→ {s.transition}</p>}
            </div>
          ))}
        </Card>
      ) : (
        <div className="space-y-3">
          {scenes.map((s,i) => (
            <SceneCard key={s.id} scene={s} index={i} onChange={d=>updateScene(s.id,d)} onDelete={()=>deleteScene(s.id)}/>
          ))}
          <Button variant="outline" onClick={addScene} className="w-full border-dashed gap-2">
            <Plus className="h-4 w-4"/>Scene Add Karo
          </Button>
        </div>
      )}
    </div>
  );
}
