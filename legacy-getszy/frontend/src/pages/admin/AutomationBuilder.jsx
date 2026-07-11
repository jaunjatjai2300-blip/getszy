import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Workflow, Plus, Trash2, Copy, Play, Loader2, Sparkles, Zap, ArrowDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

let _id = () => Math.random().toString(36).slice(2,8);

const TRIGGERS = ["New Order","New User Signup","Payment Failed","Order Shipped","Low Stock Alert","Form Submitted","Subscription Renewed","Subscription Cancelled","New Review","Manual Trigger"];
const ACTIONS = ["Send Email","Send WhatsApp","Send SMS","Update Order Status","Add Tag to User","Remove Tag","Create Task","Add Credits","Send Webhook","Notify Admin","Wait (delay)"];
const CONDITIONS = ["Always","If order > ₹1000","If user is new","If user is subscribed","If product in stock","If tag equals","If custom field"];

function StepCard({ step, index, onChange, onDelete, isLast }) {
  const isAction = step.kind==="action";
  const isCondition = step.kind==="condition";
  return (
    <div className="relative">
      <div className={`p-4 rounded-xl border space-y-3 ${isAction?"bg-blue-50 border-blue-200":isCondition?"bg-amber-50 border-amber-200":"bg-emerald-50 border-emerald-200"}`}>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${isAction?"bg-blue-600 text-white":isCondition?"bg-amber-600 text-white":"bg-emerald-600 text-white"}`}>
            {isCondition?"CONDITION":isAction?"ACTION":"TRIGGER"}
          </span>
          <Input value={step.label} onChange={e=>onChange({...step,label:e.target.value})} placeholder="Step name…" className="h-7 text-xs flex-1 bg-white"/>
          <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/></Button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Select value={step.event} onValueChange={v=>onChange({...step,event:v})}>
            <SelectTrigger className="h-7 text-xs bg-white"><SelectValue placeholder={isCondition?"Condition…":isAction?"Action…":"Trigger…"}/></SelectTrigger>
            <SelectContent>
              {(isCondition?CONDITIONS:isAction?ACTIONS:TRIGGERS).map(t=><SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <Input value={step.value||""} onChange={e=>onChange({...step,value:e.target.value})} placeholder="Value / detail…" className="h-7 text-xs bg-white"/>
        </div>
        {isAction && step.event==="Send Email" && (
          <Input value={step.template||""} onChange={e=>onChange({...step,template:e.target.value})} placeholder="Email subject / template name…" className="h-7 text-xs bg-white"/>
        )}
        {isAction && step.event==="Wait (delay)" && (
          <Input value={step.delay||""} onChange={e=>onChange({...step,delay:e.target.value})} placeholder="Delay duration (e.g. 1h, 2d, 30m)…" className="h-7 text-xs bg-white"/>
        )}
        <div className="flex items-center gap-2">
          <Switch checked={!!step.active} onCheckedChange={v=>onChange({...step,active:v})} className="scale-75"/>
          <span className="text-xs text-[var(--gs-muted)]">{step.active?"Active":"Inactive"}</span>
        </div>
      </div>
      {!isLast && <div className="flex justify-center my-1"><ArrowDown className="h-5 w-5 text-[var(--gs-muted)]"/></div>}
    </div>
  );
}

export default function AutomationBuilder() {
  const [name, setName] = useState("");
  const [active, setActive] = useState(false);
  const [steps, setSteps] = useState([
    { id:_id(), kind:"trigger",    label:"Trigger",     event:"New Order",   value:"",  active:true },
    { id:_id(), kind:"condition",  label:"Condition",   event:"If order > ₹1000", value:"1000", active:true },
    { id:_id(), kind:"action",     label:"Send Email",  event:"Send Email",  value:"",  template:"Order confirmed — Premium", active:true },
    { id:_id(), kind:"action",     label:"Notify Admin",event:"Notify Admin",value:"New high-value order!", active:true },
  ]);
  const [generating, setGenerating] = useState(false);
  const [runs] = useState([
    { at:"10 min ago", status:"success", trigger:"New Order" },
    { at:"2 hrs ago",  status:"success", trigger:"New Order" },
    { at:"1 day ago",  status:"failed",  trigger:"Payment Failed" },
  ]);

  const addStep = (kind) => setSteps(s=>[...s,{ id:_id(), kind, label:kind==="trigger"?"New Trigger":kind==="condition"?"New Condition":"New Action", event:"", value:"", active:true }]);
  const updateStep = (id,data) => setSteps(s=>s.map(x=>x.id===id?data:x));
  const deleteStep = id => setSteps(s=>s.filter(x=>x.id!==id));

  const generateAutomation = async () => {
    if (!name.trim()) { toast.error("Automation ka naam likhein"); return; }
    setGenerating(true);
    try {
      const r = await api.post("/admin/ai-platform/playground", {
        model:"llama-3.1-8b-instant", provider:"groq",
        system:"You are an automation workflow designer for Indian SaaS businesses. Reply in JSON only.",
        message:`Create a practical automation workflow named "${name}" for an Indian ecommerce/SaaS business. Include 1 trigger, 1-2 conditions, and 2-3 actions. Use these triggers: ${TRIGGERS.slice(0,5).join(", ")}. Use these actions: ${ACTIONS.slice(0,5).join(", ")}. Return JSON array with: kind (trigger/condition/action), label, event, value.`,
        temperature:0.5, max_tokens:800
      });
      try {
        const text = r.data.response||"";
        const match = text.match(/\[[\s\S]*\]/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          setSteps(parsed.map(s=>({id:_id(),active:true,...s})));
          toast.success("Automation generate ho gayi!");
        }
      } catch { toast.error("Parse error — manually steps banao"); }
    } catch { toast.error("AI unavailable"); }
    finally { setGenerating(false); }
  };

  const copyConfig = () => {
    navigator.clipboard.writeText(JSON.stringify({name,active,steps},null,2));
    toast.success("Config copied!");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Workflow className="h-7 w-7 text-amber-600"/>Automation Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">If-this-then-that automation workflows banao</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={copyConfig}><Copy className="h-3.5 w-3.5 mr-1"/>Export</Button>
          <Button size="sm" onClick={generateAutomation} disabled={generating} style={{background:"var(--gs-teal)",color:"#fff"}}>
            {generating?<Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/>:<Sparkles className="h-3.5 w-3.5 mr-1"/>}AI Generate
          </Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="grid md:grid-cols-2 gap-3">
          <Input value={name} onChange={e=>setName(e.target.value)} placeholder="Automation name (e.g. High Value Order Flow)"/>
          <div className="flex items-center gap-3">
            <Switch checked={active} onCheckedChange={setActive}/>
            <span className="text-sm font-medium">{active?"🟢 Active":"⚫ Draft"}</span>
            <Badge variant="outline">{steps.length} steps</Badge>
            <Badge className="bg-emerald-50 text-emerald-700">{steps.filter(s=>s.active).length} enabled</Badge>
          </div>
        </div>
      </Card>

      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-1">
          {steps.map((s,i) => (
            <StepCard key={s.id} step={s} index={i} onChange={d=>updateStep(s.id,d)} onDelete={()=>deleteStep(s.id)} isLast={i===steps.length-1}/>
          ))}
          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={()=>addStep("trigger")} className="flex-1 border-dashed text-emerald-600 border-emerald-300 gap-1"><Plus className="h-3.5 w-3.5"/>Trigger</Button>
            <Button variant="outline" size="sm" onClick={()=>addStep("condition")} className="flex-1 border-dashed text-amber-600 border-amber-300 gap-1"><Plus className="h-3.5 w-3.5"/>Condition</Button>
            <Button variant="outline" size="sm" onClick={()=>addStep("action")} className="flex-1 border-dashed text-blue-600 border-blue-300 gap-1"><Plus className="h-3.5 w-3.5"/>Action</Button>
          </div>
        </div>
        <Card className="p-4 space-y-3 h-fit">
          <h3 className="font-semibold text-sm flex items-center gap-2"><Zap className="h-4 w-4 text-amber-600"/>Run History</h3>
          {runs.map((r,i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <div>
                <p className="font-medium">{r.trigger}</p>
                <p className="text-[var(--gs-muted)]">{r.at}</p>
              </div>
              <Badge className={r.status==="success"?"bg-emerald-100 text-emerald-700":"bg-rose-100 text-rose-700"}>
                {r.status==="success"?"✓ Success":"✗ Failed"}
              </Badge>
            </div>
          ))}
          <div className="pt-2 border-t text-[10px] text-[var(--gs-muted)]">
            Live run history VPS pe deploy karne ke baad dikhai dega
          </div>
        </Card>
      </div>
    </div>
  );
}
