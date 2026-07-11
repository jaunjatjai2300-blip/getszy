import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { MessageCircle, Plus, Trash2, Copy, Save, Loader2, Sparkles, Send, Bot, User } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

let _id = () => Math.random().toString(36).slice(2,8);

const TRIGGER_TYPES = ["Keyword Match","Page Visit","Time on Page","Exit Intent","Button Click","After Message"];
const RESPONSE_TYPES = ["Text Reply","Quick Replies","Card","Collect Input","Redirect URL","End Chat"];

function FlowNode({ node, index, onChange, onDelete }) {
  return (
    <div className="p-4 bg-[var(--gs-surface-2)] rounded-xl border border-[var(--gs-border)] space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-violet-600 bg-violet-50 px-2 py-0.5 rounded-full">Step {index+1}</span>
        <Input value={node.label} onChange={e=>onChange({...node,label:e.target.value})} placeholder="Step name…" className="h-7 text-xs flex-1"/>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/></Button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[10px] text-[var(--gs-muted)] mb-1 uppercase tracking-wider">Trigger</p>
          <Select value={node.trigger} onValueChange={v=>onChange({...node,trigger:v})}>
            <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Trigger…"/></SelectTrigger>
            <SelectContent>{TRIGGER_TYPES.map(t=><SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <p className="text-[10px] text-[var(--gs-muted)] mb-1 uppercase tracking-wider">Response Type</p>
          <Select value={node.type} onValueChange={v=>onChange({...node,type:v})}>
            <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="Type…"/></SelectTrigger>
            <SelectContent>{RESPONSE_TYPES.map(t=><SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      {node.trigger==="Keyword Match" && (
        <Input value={node.keywords||""} onChange={e=>onChange({...node,keywords:e.target.value})} placeholder="Keywords (comma separated): hello, hi, namaste" className="h-7 text-xs"/>
      )}
      <Textarea value={node.message} onChange={e=>onChange({...node,message:e.target.value})} placeholder="Bot ka message / response likhein…" rows={2} className="text-xs resize-none"/>
      {(node.type==="Quick Replies"||node.type==="Card") && (
        <Input value={node.options||""} onChange={e=>onChange({...node,options:e.target.value})} placeholder="Options (comma separated): Yes, No, Tell me more" className="h-7 text-xs"/>
      )}
      {node.type==="Collect Input" && (
        <Input value={node.inputVar||""} onChange={e=>onChange({...node,inputVar:e.target.value})} placeholder="Variable name to save input (e.g. user_name, user_email)" className="h-7 text-xs"/>
      )}
      {node.type==="Redirect URL" && (
        <Input value={node.url||""} onChange={e=>onChange({...node,url:e.target.value})} placeholder="Redirect URL…" className="h-7 text-xs"/>
      )}
      <div className="flex items-center gap-2">
        <Switch checked={!!node.active} onCheckedChange={v=>onChange({...node,active:v})} className="scale-75"/>
        <span className="text-xs text-[var(--gs-muted)]">Active</span>
      </div>
    </div>
  );
}

function ChatPreview({ botName, greeting, flows }) {
  const [msgs, setMsgs] = useState([{ from:"bot", text: greeting||"Namaste! Main kaise help kar sakta hoon?" }]);
  const [input, setInput] = useState("");

  const send = () => {
    if (!input.trim()) return;
    const userMsg = { from:"user", text:input };
    setMsgs(m=>[...m,userMsg]);
    setInput("");
    const matched = flows.find(f => f.active && f.trigger==="Keyword Match" &&
      f.keywords?.split(",").some(k=>input.toLowerCase().includes(k.trim().toLowerCase())));
    setTimeout(() => {
      if (matched) {
        setMsgs(m=>[...m,{ from:"bot", text:matched.message, options:matched.options?.split(",").map(o=>o.trim()).filter(Boolean) }]);
      } else {
        setMsgs(m=>[...m,{ from:"bot", text:"Samajh nahi aaya. Kya aap aur detail mein bata sakte hain?" }]);
      }
    }, 600);
  };

  return (
    <Card className="overflow-hidden border-2 border-[var(--gs-border)] max-w-sm mx-auto">
      <div className="bg-[var(--gs-teal)] text-white p-3 flex items-center gap-2">
        <div className="h-8 w-8 rounded-full bg-white/20 grid place-items-center"><Bot className="h-4 w-4"/></div>
        <div><p className="font-semibold text-sm">{botName||"Getszy Bot"}</p><p className="text-[10px] opacity-80">Online</p></div>
      </div>
      <div className="h-72 overflow-y-auto p-3 space-y-2 bg-[var(--gs-surface)]">
        {msgs.map((m,i) => (
          <div key={i} className={`flex ${m.from==="user"?"justify-end":"justify-start"}`}>
            {m.from==="bot" && <div className="h-6 w-6 rounded-full bg-[var(--gs-teal-soft)] grid place-items-center mr-1.5 flex-shrink-0 mt-1"><Bot className="h-3 w-3 text-[var(--gs-teal)]"/></div>}
            <div className={`max-w-[75%] space-y-1.5`}>
              <div className={`px-3 py-2 rounded-2xl text-xs ${m.from==="user"?"bg-[var(--gs-teal)] text-white":"bg-white border border-[var(--gs-border)]"}`}>{m.text}</div>
              {m.options && <div className="flex flex-wrap gap-1">{m.options.map((o,j)=><button key={j} className="text-[10px] px-2 py-1 rounded-full border border-[var(--gs-teal)] text-[var(--gs-teal)] bg-white hover:bg-[var(--gs-teal-soft)]" onClick={()=>{setInput(o);setTimeout(()=>document.getElementById("chatInput")?.click(),50);}}>{o}</button>)}</div>}
            </div>
          </div>
        ))}
      </div>
      <div className="p-2 border-t flex gap-2 bg-white">
        <Input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()} placeholder="Message likhein…" className="h-8 text-xs flex-1"/>
        <Button id="chatInput" size="icon" className="h-8 w-8" style={{background:"var(--gs-teal)",color:"#fff"}} onClick={send}><Send className="h-3.5 w-3.5"/></Button>
      </div>
    </Card>
  );
}

export default function ChatbotBuilder() {
  const [botName, setBotName] = useState("Getszy Assistant");
  const [greeting, setGreeting] = useState("Namaste! Main aapki kaise help kar sakta hoon?");
  const [flows, setFlows] = useState([
    { id:_id(), label:"Welcome", trigger:"Page Visit", type:"Text Reply", message:"Namaste! Welcome to Getszy. Kaise help kar sakta hoon?", active:true },
    { id:_id(), label:"Pricing", trigger:"Keyword Match", type:"Quick Replies", keywords:"price, pricing, cost, kitna, rate", message:"Hamare plans ₹499/month se shuru hote hain. Kaunsa plan dekhna chahenge?", options:"Starter Plan, Pro Plan, Enterprise", active:true },
    { id:_id(), label:"Support", trigger:"Keyword Match", type:"Text Reply", keywords:"help, support, problem, issue", message:"Zaroor help karunga! Please apni problem detail mein batayein.", active:true },
  ]);
  const [tab, setTab] = useState("build");
  const [generating, setGenerating] = useState(false);

  const addFlow = () => setFlows(f=>[...f,{ id:_id(), label:`Step ${f.length+1}`, trigger:"Keyword Match", type:"Text Reply", message:"", active:true }]);
  const updateFlow = (id,data) => setFlows(f=>f.map(x=>x.id===id?data:x));
  const deleteFlow = id => setFlows(f=>f.filter(x=>x.id!==id));

  const generateFlows = async () => {
    if (!botName.trim()) { toast.error("Bot ka naam likhein"); return; }
    setGenerating(true);
    try {
      const r = await api.post("/admin/ai-platform/playground", {
        model:"llama-3.1-8b-instant", provider:"groq",
        system:"You are a chatbot designer. Create practical chatbot flows for an Indian SaaS business. Reply in JSON only.",
        message:`Create 5 chatbot flow steps for a bot named "${botName}" for an Indian business. Include flows for: pricing, support, lead capture, FAQ, and escalation. Return JSON array with: label, trigger (from: ${TRIGGER_TYPES.join(",")}), type (from: ${RESPONSE_TYPES.join(",")}), keywords (if keyword match), message, options (if quick replies).`,
        temperature:0.6, max_tokens:1200
      });
      try {
        const text = r.data.response||"";
        const match = text.match(/\[[\s\S]*\]/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          setFlows(parsed.map(f=>({id:_id(),active:true,...f})));
          toast.success("Chatbot flows generate ho gayi!");
        }
      } catch { toast.error("Parse error — manually flows banao"); }
    } catch { toast.error("AI unavailable"); }
    finally { setGenerating(false); }
  };

  const exportCode = () => {
    const code = `// ${botName} Chatbot Config\nconst chatbotConfig = ${JSON.stringify({botName,greeting,flows},null,2)};`;
    navigator.clipboard.writeText(code);
    toast.success("Config copied!");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><MessageCircle className="h-7 w-7 text-violet-600"/>Chatbot Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Conversational chatbot flows banao — AI se ya khud</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={()=>setTab(t=>t==="build"?"preview":"build")}>
            {tab==="build"?"👁 Preview":"✏️ Edit"}
          </Button>
          <Button variant="outline" size="sm" onClick={exportCode}><Copy className="h-3.5 w-3.5 mr-1"/>Export</Button>
          <Button size="sm" onClick={generateFlows} disabled={generating} style={{background:"var(--gs-teal)",color:"#fff"}}>
            {generating?<Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/>:<Sparkles className="h-3.5 w-3.5 mr-1"/>}AI Generate
          </Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="grid md:grid-cols-2 gap-3">
          <div><p className="text-xs font-semibold mb-1.5">Bot Name</p><Input value={botName} onChange={e=>setBotName(e.target.value)} placeholder="e.g. Getszy Assistant"/></div>
          <div><p className="text-xs font-semibold mb-1.5">Greeting Message</p><Input value={greeting} onChange={e=>setGreeting(e.target.value)} placeholder="Pehla message…"/></div>
        </div>
        <div className="flex items-center gap-3 mt-3">
          <Badge variant="outline">{flows.length} flows</Badge>
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700">{flows.filter(f=>f.active).length} active</Badge>
        </div>
      </Card>

      {tab==="preview" ? (
        <div className="py-4"><ChatPreview botName={botName} greeting={greeting} flows={flows}/></div>
      ) : (
        <div className="space-y-3">
          {flows.map((f,i) => (
            <FlowNode key={f.id} node={f} index={i} onChange={d=>updateFlow(f.id,d)} onDelete={()=>deleteFlow(f.id)}/>
          ))}
          <Button variant="outline" className="w-full border-dashed gap-2" onClick={addFlow}>
            <Plus className="h-4 w-4"/>Flow Step Add Karo
          </Button>
        </div>
      )}
    </div>
  );
}
