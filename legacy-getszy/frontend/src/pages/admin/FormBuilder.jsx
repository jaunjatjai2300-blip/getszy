import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { FormInput, Plus, Trash2, GripVertical, Eye, Code2, Copy, Save, Loader2, Check } from "lucide-react";
import { toast } from "sonner";

const FIELD_TYPES = [
  { value:"text", label:"Text", icon:"📝" },
  { value:"email", label:"Email", icon:"📧" },
  { value:"number", label:"Number", icon:"🔢" },
  { value:"phone", label:"Phone", icon:"📱" },
  { value:"textarea", label:"Long Text", icon:"📄" },
  { value:"select", label:"Dropdown", icon:"📋" },
  { value:"radio", label:"Radio", icon:"🔘" },
  { value:"checkbox", label:"Checkbox", icon:"☑️" },
  { value:"date", label:"Date", icon:"📅" },
  { value:"file", label:"File Upload", icon:"📎" },
  { value:"rating", label:"Rating", icon:"⭐" },
];

let _id = ()=> Math.random().toString(36).slice(2,8);

function FieldCard({ field, index, onChange, onDelete }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-[var(--gs-surface-2)] rounded-xl border border-[var(--gs-border)]">
      <div className="pt-1 text-[var(--gs-muted)] cursor-grab"><GripVertical className="h-4 w-4"/></div>
      <div className="flex-1 space-y-2">
        <div className="flex gap-2">
          <Input className="h-8 text-xs flex-1" placeholder="Field Label" value={field.label} onChange={e=>onChange({label:e.target.value})}/>
          <Select value={field.type} onValueChange={v=>onChange({type:v})}>
            <SelectTrigger className="h-8 text-xs w-36"><SelectValue/></SelectTrigger>
            <SelectContent>{FIELD_TYPES.map(t=><SelectItem key={t.value} value={t.value} className="text-xs">{t.icon} {t.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex gap-3 items-center">
          <Input className="h-7 text-xs flex-1" placeholder="Placeholder text" value={field.placeholder||""} onChange={e=>onChange({placeholder:e.target.value})}/>
          <label className="flex items-center gap-1.5 text-xs text-[var(--gs-muted)] cursor-pointer select-none">
            <Switch className="scale-75" checked={!!field.required} onCheckedChange={v=>onChange({required:v})}/>Required
          </label>
        </div>
        {["select","radio"].includes(field.type)&&(
          <div><Input className="h-7 text-xs" placeholder="Options (comma separated): Yes, No, Maybe" value={(field.options||[]).join(", ")} onChange={e=>onChange({options:e.target.value.split(",").map(o=>o.trim()).filter(Boolean)})}/></div>
        )}
      </div>
      <button onClick={onDelete} className="pt-1 text-rose-400 hover:text-rose-600"><Trash2 className="h-4 w-4"/></button>
    </div>
  );
}

function FormPreview({ form, fields }) {
  return (
    <div className="max-w-md mx-auto">
      <Card className="p-6 space-y-4">
        <div>
          <h2 className="text-lg font-bold">{form.title||"Untitled Form"}</h2>
          {form.description&&<p className="text-sm text-[var(--gs-muted)] mt-1">{form.description}</p>}
        </div>
        {fields.map(f=>(
          <div key={f.id} className="space-y-1">
            <label className="text-sm font-medium">{f.label||"Field"}{f.required&&<span className="text-rose-500 ml-0.5">*</span>}</label>
            {f.type==="textarea"?<Textarea className="text-sm" placeholder={f.placeholder} rows={3}/>:
             f.type==="select"?<Select><SelectTrigger className="h-9 text-sm"><SelectValue placeholder={f.placeholder||"Select…"}/></SelectTrigger><SelectContent>{(f.options||[]).map(o=><SelectItem key={o} value={o} className="text-xs">{o}</SelectItem>)}</SelectContent></Select>:
             f.type==="radio"?<div className="space-y-1">{(f.options||["Option 1","Option 2"]).map(o=><label key={o} className="flex items-center gap-2 text-sm"><input type="radio" name={f.id}/>{o}</label>)}</div>:
             f.type==="checkbox"?<label className="flex items-center gap-2 text-sm"><input type="checkbox"/>{f.label}</label>:
             f.type==="rating"?<div className="flex gap-1">{[1,2,3,4,5].map(i=><button key={i} className="text-2xl">⭐</button>)}</div>:
             <Input className="h-9 text-sm" type={f.type==="phone"?"tel":f.type} placeholder={f.placeholder}/>}
          </div>
        ))}
        <Button className="w-full bg-[var(--gs-teal)]">{form.submit_label||"Submit"}</Button>
      </Card>
    </div>
  );
}

export default function FormBuilder() {
  const [form, setForm] = useState({ title:"", description:"", submit_label:"Submit", success_message:"Thank you! Form submitted." });
  const [fields, setFields] = useState([
    { id:_id(), type:"text", label:"Full Name", placeholder:"Your name", required:true },
    { id:_id(), type:"email", label:"Email Address", placeholder:"you@example.com", required:true },
  ]);
  const [tab, setTab] = useState("builder");
  const [saved, setSaved] = useState(false);

  const addField = (type="text")=>{
    setFields(p=>[...p,{id:_id(),type,label:FIELD_TYPES.find(t=>t.value===type)?.label||"Field",placeholder:"",required:false,options:[]}]);
  };

  const updateField = (id,changes)=>setFields(p=>p.map(f=>f.id===id?{...f,...changes}:f));
  const deleteField = (id)=>setFields(p=>p.filter(f=>f.id!==id));

  const embedCode = `<!-- Getszy Form Embed -->
<div id="getszy-form-${form.title.toLowerCase().replace(/\s+/g,'-')||'form'}"></div>
<script src="https://getszy.com/embed/form.js" data-form="${form.title}" async></script>`;

  const jsonSchema = JSON.stringify({ title:form.title, description:form.description, fields:fields.map(f=>({id:f.id,type:f.type,label:f.label,placeholder:f.placeholder,required:f.required,...(f.options?.length?{options:f.options}:{})})), submit_label:form.submit_label, success_message:form.success_message }, null, 2);

  const handleSave = ()=>{ setSaved(true); toast.success("Form schema saved!"); setTimeout(()=>setSaved(false),2000); };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><FormInput className="h-7 w-7 text-[var(--gs-teal)]"/>Form Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Drag & drop form builder — embed anywhere</p>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-[var(--gs-surface-2)] rounded-lg p-1 gap-1">
            {[["builder","🛠 Builder"],["preview","👁 Preview"],["code","</> Embed"]].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)} className={`text-xs px-3 py-1.5 rounded-md transition-all ${tab===t?"bg-white shadow text-[var(--gs-teal)] font-medium":"text-[var(--gs-muted)] hover:text-foreground"}`}>{l}</button>
            ))}
          </div>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={handleSave}>
            {saved?<><Check className="h-3.5 w-3.5 mr-1"/>Saved</>:<><Save className="h-3.5 w-3.5 mr-1"/>Save</>}
          </Button>
        </div>
      </div>

      {tab==="builder"&&(
        <div className="grid lg:grid-cols-[280px_1fr] gap-5">
          {/* Field Palette */}
          <div className="space-y-3">
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Form Settings</p>
            <Input className="h-9 text-sm" placeholder="Form Title *" value={form.title} onChange={e=>setForm(p=>({...p,title:e.target.value}))}/>
            <Textarea className="text-xs" rows={2} placeholder="Description (optional)" value={form.description} onChange={e=>setForm(p=>({...p,description:e.target.value}))}/>
            <Input className="h-8 text-xs" placeholder="Submit Button Label" value={form.submit_label} onChange={e=>setForm(p=>({...p,submit_label:e.target.value}))}/>
            <hr className="border-[var(--gs-border)]"/>
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Add Fields</p>
            <div className="grid grid-cols-2 gap-1.5">
              {FIELD_TYPES.map(t=>(
                <button key={t.value} onClick={()=>addField(t.value)}
                  className="flex items-center gap-2 p-2 rounded-lg text-xs bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] hover:text-[var(--gs-teal)] transition-colors text-left">
                  <span>{t.icon}</span>{t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Form Canvas */}
          <div className="space-y-3">
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">{fields.length} Fields</p>
            {fields.length===0?<Card className="p-12 text-center text-sm text-[var(--gs-muted)]">← Left se fields add karo</Card>:
              fields.map((f,i)=><FieldCard key={f.id} field={f} index={i} onChange={c=>updateField(f.id,c)} onDelete={()=>deleteField(f.id)}/>)
            }
            <Button variant="outline" size="sm" onClick={()=>addField()} className="w-full h-9 border-dashed">
              <Plus className="h-3.5 w-3.5 mr-1"/>Add Field
            </Button>
          </div>
        </div>
      )}

      {tab==="preview"&&<FormPreview form={form} fields={fields}/>}

      {tab==="code"&&(
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Embed Code</p>
              <button onClick={()=>{navigator.clipboard?.writeText(embedCode);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy</button>
            </div>
            <pre className="bg-[#0a0a0a] text-emerald-400 text-xs p-4 rounded-xl overflow-x-auto font-mono">{embedCode}</pre>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">JSON Schema</p>
              <button onClick={()=>{navigator.clipboard?.writeText(jsonSchema);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy</button>
            </div>
            <pre className="bg-[#0a0a0a] text-blue-300 text-xs p-4 rounded-xl overflow-x-auto font-mono max-h-64">{jsonSchema}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
