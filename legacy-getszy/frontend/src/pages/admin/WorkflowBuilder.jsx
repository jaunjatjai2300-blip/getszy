import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { GitBranch, Plus, Trash2, Copy, Play, Loader2, Sparkles, ArrowRight, Users, Clock } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

let _id = () => Math.random().toString(36).slice(2,8);

const STEP_TYPES = ["Task","Approval","Notification","Decision","Sub-workflow","Delay","Integration","End"];
const ASSIGNEES = ["Founder","Sales Team","Support Team","Finance","Operations","Auto (AI)"];
const PRIORITIES = ["Low","Medium","High","Critical"];
const STATUSES = ["Draft","Active","Paused","Archived"];

function WorkflowStep({ step, index, onChange, onDelete, isLast }) {
  const typeColors = {
    "Task":"bg-blue-50 border-blue-200","Approval":"bg-amber-50 border-amber-200",
    "Notification":"bg-emerald-50 border-emerald-200","Decision":"bg-violet-50 border-violet-200",
    "Delay":"bg-slate-50 border-slate-200","End":"bg-rose-50 border-rose-200",
    "Integration":"bg-cyan-50 border-cyan-200","Sub-workflow":"bg-pink-50 border-pink-200"
  };
  return (
    <div className="flex items-stretch gap-2">
      <div className={`flex-1 p-4 rounded-xl border space-y-3 ${typeColors[step.type]||"bg-[var(--gs-surface-2)] border-[var(--gs-border)]"}`}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold bg-white/60 px-2 py-0.5 rounded-full border">{step.type}</span>
          <Input value={step.name} onChange={e=>onChange({...step,name:e.target.value})} placeholder="Step name…" className="h-7 text-xs flex-1 bg-white"/>
          <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400" onClick={onDelete}><Trash2 className="h-3.5 w-3.5"/></Button>
        </div>
        <Textarea value={step.description||""} onChange={e=>onChange({...step,description:e.target.value})} placeholder="Step description / instructions…" rows={2} className="text-xs resize-none bg-white"/>
        <div className="grid grid-cols-3 gap-2">
          <Select value={step.assignee||""} onValueChange={v=>onChange({...step,assignee:v})}>
            <SelectTrigger className="h-7 text-xs bg-white"><SelectValue placeholder="Assign to…"/></SelectTrigger>
            <SelectContent>{ASSIGNEES.map(a=><SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={step.priority||""} onValueChange={v=>onChange({...step,priority:v})}>
            <SelectTrigger className="h-7 text-xs bg-white"><SelectValue placeholder="Priority…"/></SelectTrigger>
            <SelectContent>{PRIORITIES.map(p=><SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
          <Input value={step.sla||""} onChange={e=>onChange({...step,sla:e.target.value})} placeholder="SLA (e.g. 2h, 1d)" className="h-7 text-xs bg-white"/>
        </div>
        {step.type==="Decision" && (
          <Input value={step.condition||""} onChange={e=>onChange({...step,condition:e.target.value})} placeholder="Decision condition (e.g. approved? yes → next, no → reject)" className="h-7 text-xs bg-white"/>
        )}
        {step.type==="Notification" && (
          <Input value={step.message||""} onChange={e=>onChange({...step,message:e.target.value})} placeholder="Notification message…" className="h-7 text-xs bg-white"/>
        )}
        {step.type==="Delay" && (
          <Input value={step.delay||""} onChange={e=>onChange({...step,delay:e.target.value})} placeholder="Wait duration (e.g. 30m, 2h, 1d)" className="h-7 text-xs bg-white"/>
        )}
      </div>
      {!isLast && <div className="flex items-center"><ArrowRight className="h-5 w-5 text-[var(--gs-muted)]"/></div>}
    </div>
  );
}

export default function WorkflowBuilder() {
  const [workflow, setWorkflow] = useState({
    name: "Order Processing Workflow",
    description: "Naya order aane ke baad ka standard process",
    status: "Active",
    category: "Operations",
    steps: [
      { id:_id(), type:"Task",         name:"Order Receive Karo",     description:"New order verify karo",           assignee:"Auto (AI)",  priority:"High",   sla:"30m" },
      { id:_id(), type:"Notification", name:"Confirm Customer",       description:"Order confirmation email bhejo",  assignee:"Auto (AI)",  priority:"Medium", message:"Aapka order receive ho gaya!" },
      { id:_id(), type:"Task",         name:"Stock Check",            description:"Product available hai check karo",assignee:"Operations", priority:"High",   sla:"1h" },
      { id:_id(), type:"Approval",     name:"Dispatch Approval",      description:"Manager se dispatch approve karo",assignee:"Founder",    priority:"High",   sla:"2h" },
      { id:_id(), type:"Task",         name:"Ship Karo",              description:"Order pack aur ship karo",        assignee:"Operations", priority:"High",   sla:"1d" },
      { id:_id(), type:"Notification", name:"Tracking Update",        description:"Tracking number customer ko do",  assignee:"Auto (AI)",  priority:"Low",    message:"Aapka order dispatch ho gaya!" },
      { id:_id(), type:"End",          name:"Workflow Complete",      description:"Order delivered, workflow end",   assignee:"",           priority:"Low" },
    ]
  });
  const [generating, setGenerating] = useState(false);
  const [tab, setTab] = useState("build");

  const updateWorkflow = (field, value) => setWorkflow(w=>({...w,[field]:value}));
  const addStep = (type) => setWorkflow(w=>({...w, steps:[...w.steps, { id:_id(), type, name:`New ${type}`, description:"", assignee:"", priority:"Medium" }]}));
  const updateStep = (id,data) => setWorkflow(w=>({...w, steps:w.steps.map(x=>x.id===id?data:x)}));
  const deleteStep = (id) => setWorkflow(w=>({...w, steps:w.steps.filter(x=>x.id!==id)}));

  const generateWorkflow = async () => {
    if (!workflow.name.trim()) { toast.error("Workflow ka naam likhein"); return; }
    setGenerating(true);
    try {
      const r = await api.post("/admin/ai-platform/playground", {
        model:"llama-3.1-8b-instant", provider:"groq",
        system:"You are a business process designer for Indian companies. Create practical, detailed workflow steps. Reply in JSON.",
        message:`Create a business workflow for: "${workflow.name}". ${workflow.description?`Context: ${workflow.description}`:""}. Generate 5-7 steps covering the complete process. Use step types from: ${STEP_TYPES.join(", ")}. Return JSON array with: type, name, description, assignee (from: ${ASSIGNEES.join(", ")}), priority (Low/Medium/High/Critical), sla (time estimate like 1h or 1d).`,
        temperature:0.5, max_tokens:1200
      });
      try {
        const text = r.data.response||"";
        const match = text.match(/\[[\s\S]*\]/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          setWorkflow(w=>({...w, steps:parsed.map(s=>({id:_id(),...s}))}));
          toast.success("Workflow generate ho gaya!");
        }
      } catch { toast.error("Parse error"); }
    } catch { toast.error("AI unavailable"); }
    finally { setGenerating(false); }
  };

  const exportJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(workflow,null,2));
    toast.success("Workflow JSON copied!");
  };

  const stepStats = {
    total: workflow.steps.length,
    tasks: workflow.steps.filter(s=>s.type==="Task").length,
    approvals: workflow.steps.filter(s=>s.type==="Approval").length,
    critical: workflow.steps.filter(s=>s.priority==="Critical"||s.priority==="High").length,
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><GitBranch className="h-7 w-7 text-indigo-600"/>Workflow Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Business process workflows banao aur team assign karo</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={exportJSON}><Copy className="h-3.5 w-3.5 mr-1"/>Export JSON</Button>
          <Button size="sm" onClick={generateWorkflow} disabled={generating} style={{background:"var(--gs-teal)",color:"#fff"}}>
            {generating?<Loader2 className="h-3.5 w-3.5 animate-spin mr-1"/>:<Sparkles className="h-3.5 w-3.5 mr-1"/>}AI Generate
          </Button>
        </div>
      </div>

      <Card className="p-4 space-y-3">
        <div className="grid md:grid-cols-2 gap-3">
          <Input value={workflow.name} onChange={e=>updateWorkflow("name",e.target.value)} placeholder="Workflow name…"/>
          <div className="flex gap-2">
            <Select value={workflow.status} onValueChange={v=>updateWorkflow("status",v)}>
              <SelectTrigger className="h-9 flex-1"><SelectValue/></SelectTrigger>
              <SelectContent>{STATUSES.map(s=><SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
            <Input value={workflow.category||""} onChange={e=>updateWorkflow("category",e.target.value)} placeholder="Category…" className="h-9 flex-1"/>
          </div>
        </div>
        <Textarea value={workflow.description} onChange={e=>updateWorkflow("description",e.target.value)} placeholder="Workflow description…" rows={2} className="text-xs resize-none"/>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{stepStats.total} steps</Badge>
          <Badge variant="outline" className="bg-blue-50 text-blue-700">{stepStats.tasks} tasks</Badge>
          <Badge variant="outline" className="bg-amber-50 text-amber-700">{stepStats.approvals} approvals</Badge>
          <Badge variant="outline" className="bg-rose-50 text-rose-700">{stepStats.critical} high-priority</Badge>
          <Badge className={workflow.status==="Active"?"bg-emerald-100 text-emerald-700":"bg-slate-100 text-slate-700"}>{workflow.status}</Badge>
        </div>
      </Card>

      <div className="grid lg:grid-cols-4 gap-5">
        <div className="lg:col-span-3 space-y-3">
          {workflow.steps.map((s,i) => (
            <WorkflowStep key={s.id} step={s} index={i} onChange={d=>updateStep(s.id,d)} onDelete={()=>deleteStep(s.id)} isLast={i===workflow.steps.length-1}/>
          ))}
        </div>
        <Card className="p-4 h-fit space-y-3">
          <h3 className="font-semibold text-sm">Step Add Karo</h3>
          <div className="space-y-1.5">
            {STEP_TYPES.map(type => (
              <button key={type} onClick={()=>addStep(type)} className="w-full flex items-center gap-2 p-2 rounded-lg text-xs hover:bg-[var(--gs-teal-soft)] hover:text-[var(--gs-teal)] transition-colors border border-[var(--gs-border)] text-left">
                <Plus className="h-3.5 w-3.5 flex-shrink-0"/>{type}
              </button>
            ))}
          </div>
          <div className="pt-2 border-t space-y-1.5 text-xs text-[var(--gs-muted)]">
            <p><Users className="h-3 w-3 inline mr-1"/>Assign tasks to team members</p>
            <p><Clock className="h-3 w-3 inline mr-1"/>Set SLA deadlines per step</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
