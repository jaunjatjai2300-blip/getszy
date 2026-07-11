import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Zap, Plus, Trash2, Save, Check, Copy, Play, ChevronDown, ChevronRight, Key, AlertCircle } from "lucide-react";
import { toast } from "sonner";

const METHODS = ["GET","POST","PUT","PATCH","DELETE"];
const METHOD_COLORS = { GET:"bg-emerald-100 text-emerald-700", POST:"bg-blue-100 text-blue-700", PUT:"bg-amber-100 text-amber-700", PATCH:"bg-purple-100 text-purple-700", DELETE:"bg-rose-100 text-rose-700" };
const AUTH_TYPES = ["None","Bearer Token","API Key","Basic Auth","OAuth 2.0"];
const PARAM_TYPES = ["string","number","boolean","array","object","file"];

let uid=()=>Math.random().toString(36).slice(2,8);

const DEFAULT_ENDPOINTS = [
  { id:uid(), method:"GET", path:"/api/users", tag:"Users", summary:"List all users", description:"Paginated list of all registered users", auth:"Bearer Token", expanded:true,
    params:[{id:uid(),in:"query",name:"page",type:"number",required:false,description:"Page number"},{id:uid(),in:"query",name:"limit",type:"number",required:false,description:"Items per page (default 20)"}],
    responses:[{code:"200",description:"List of users"},{code:"401",description:"Unauthorized"}]},
  { id:uid(), method:"POST", path:"/api/users", tag:"Users", summary:"Create user", description:"Create a new user account", auth:"Bearer Token", expanded:false,
    params:[{id:uid(),in:"body",name:"email",type:"string",required:true,description:"User email"},{id:uid(),in:"body",name:"name",type:"string",required:true,description:"Full name"}],
    responses:[{code:"201",description:"User created"},{code:"400",description:"Validation error"}]},
];

function EndpointCard({ ep, onChange, onDelete }) {
  const toggle=()=>onChange({expanded:!ep.expanded});
  const addParam=()=>onChange({params:[...ep.params,{id:uid(),in:"query",name:"",type:"string",required:false,description:""}]});
  const updParam=(pid,k,v)=>onChange({params:ep.params.map(p=>p.id===pid?{...p,[k]:v}:p)});
  const delParam=(pid)=>onChange({params:ep.params.filter(p=>p.id!==pid)});
  const addResp=()=>onChange({responses:[...(ep.responses||[]),{code:"200",description:""}]});
  const updResp=(i,k,v)=>onChange({responses:ep.responses.map((r,idx)=>idx===i?{...r,[k]:v}:r)});
  const delResp=(i)=>onChange({responses:ep.responses.filter((_,idx)=>idx!==i)});

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-[var(--gs-surface-2)]" onClick={toggle}>
        {ep.expanded?<ChevronDown className="h-4 w-4 text-[var(--gs-muted)] flex-shrink-0"/>:<ChevronRight className="h-4 w-4 text-[var(--gs-muted)] flex-shrink-0"/>}
        <Badge className={`text-[10px] font-mono flex-shrink-0 ${METHOD_COLORS[ep.method]||""}`}>{ep.method}</Badge>
        <code className="text-sm font-mono flex-1 text-[var(--gs-teal)]">{ep.path||"/api/endpoint"}</code>
        <span className="text-xs text-[var(--gs-muted)] hidden sm:block">{ep.summary}</span>
        {ep.auth!=="None"&&<Key className="h-3.5 w-3.5 text-amber-500 flex-shrink-0"/>}
        <button onClick={e=>{e.stopPropagation();onDelete();}} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-3.5 w-3.5"/></button>
      </div>

      {ep.expanded&&(
        <div className="p-4 border-t border-[var(--gs-border)] space-y-4">
          <div className="grid sm:grid-cols-3 gap-3">
            <div><label className="text-xs font-medium mb-1 block">Method</label>
              <Select value={ep.method} onValueChange={v=>onChange({method:v})}>
                <SelectTrigger className="h-9 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>{METHODS.map(m=><SelectItem key={m} value={m} className="text-xs">{m}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="sm:col-span-2"><label className="text-xs font-medium mb-1 block">Path</label>
              <Input className="h-9 text-xs font-mono" placeholder="/api/endpoint" value={ep.path} onChange={e=>onChange({path:e.target.value})}/></div>
          </div>
          <div className="grid sm:grid-cols-3 gap-3">
            <div><label className="text-xs font-medium mb-1 block">Tag / Group</label>
              <Input className="h-8 text-xs" value={ep.tag||""} onChange={e=>onChange({tag:e.target.value})}/></div>
            <div><label className="text-xs font-medium mb-1 block">Authentication</label>
              <Select value={ep.auth} onValueChange={v=>onChange({auth:v})}>
                <SelectTrigger className="h-8 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>{AUTH_TYPES.map(a=><SelectItem key={a} value={a} className="text-xs">{a}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><label className="text-xs font-medium mb-1 block">Summary</label>
              <Input className="h-8 text-xs" value={ep.summary||""} onChange={e=>onChange({summary:e.target.value})}/></div>
          </div>
          <div><label className="text-xs font-medium mb-1 block">Description</label>
            <Textarea className="text-xs" rows={2} value={ep.description||""} onChange={e=>onChange({description:e.target.value})}/></div>

          {/* Parameters */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold">Parameters ({ep.params?.length||0})</label>
              <button onClick={addParam} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Plus className="h-3 w-3"/>Add</button>
            </div>
            {(ep.params||[]).map(p=>(
              <div key={p.id} className="flex gap-2 mb-1.5">
                <Select value={p.in} onValueChange={v=>updParam(p.id,"in",v)}>
                  <SelectTrigger className="h-7 text-xs w-20"><SelectValue/></SelectTrigger>
                  <SelectContent>{["query","path","body","header"].map(loc=><SelectItem key={loc} value={loc} className="text-xs">{loc}</SelectItem>)}</SelectContent>
                </Select>
                <Input className="h-7 text-xs font-mono w-28" placeholder="name" value={p.name} onChange={e=>updParam(p.id,"name",e.target.value)}/>
                <Select value={p.type} onValueChange={v=>updParam(p.id,"type",v)}>
                  <SelectTrigger className="h-7 text-xs w-24"><SelectValue/></SelectTrigger>
                  <SelectContent>{PARAM_TYPES.map(t=><SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>)}</SelectContent>
                </Select>
                <Input className="h-7 text-xs flex-1" placeholder="description" value={p.description||""} onChange={e=>updParam(p.id,"description",e.target.value)}/>
                <label className="flex items-center gap-1 text-[10px] text-[var(--gs-muted)] whitespace-nowrap"><input type="checkbox" checked={!!p.required} onChange={e=>updParam(p.id,"required",e.target.checked)} className="accent-[var(--gs-teal)]"/>Req</label>
                <button onClick={()=>delParam(p.id)} className="text-rose-400"><Trash2 className="h-3 w-3"/></button>
              </div>
            ))}
          </div>

          {/* Responses */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold">Responses</label>
              <button onClick={addResp} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Plus className="h-3 w-3"/>Add</button>
            </div>
            {(ep.responses||[]).map((r,i)=>(
              <div key={i} className="flex gap-2 mb-1.5">
                <Input className="h-7 text-xs w-16 font-mono" placeholder="200" value={r.code} onChange={e=>updResp(i,"code",e.target.value)}/>
                <Input className="h-7 text-xs flex-1" placeholder="Description" value={r.description} onChange={e=>updResp(i,"description",e.target.value)}/>
                <button onClick={()=>delResp(i)} className="text-rose-400"><Trash2 className="h-3 w-3"/></button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function APIBuilder() {
  const [apiInfo, setApiInfo] = useState({ title:"Getszy API", version:"1.0.0", baseUrl:"/api", description:"" });
  const [endpoints, setEndpoints] = useState(DEFAULT_ENDPOINTS);
  const [tab, setTab] = useState("builder");
  const [saved, setSaved] = useState(false);

  const addEndpoint = ()=>setEndpoints(p=>[...p,{id:uid(),method:"GET",path:"/api/",tag:"",summary:"",description:"",auth:"Bearer Token",expanded:true,params:[],responses:[{code:"200",description:"Success"}]}]);
  const updEp = (id,changes)=>setEndpoints(p=>p.map(e=>e.id===id?{...e,...changes}:e));
  const delEp = (id)=>setEndpoints(p=>p.filter(e=>e.id!==id));
  const save = ()=>{setSaved(true);toast.success("API schema saved!");setTimeout(()=>setSaved(false),2000);};

  const grouped = endpoints.reduce((acc,ep)=>{const tag=ep.tag||"Other";(acc[tag]||(acc[tag]=[])).push(ep);return acc;},{});

  const openApiJson = JSON.stringify({
    openapi:"3.0.0",
    info:{title:apiInfo.title,version:apiInfo.version,description:apiInfo.description},
    servers:[{url:apiInfo.baseUrl}],
    paths:endpoints.reduce((acc,ep)=>{
      if(!acc[ep.path])acc[ep.path]={};
      acc[ep.path][ep.method.toLowerCase()]={
        summary:ep.summary,description:ep.description,tags:[ep.tag||"default"],
        parameters:(ep.params||[]).filter(p=>p.in!=="body").map(p=>({name:p.name,in:p.in,required:p.required,description:p.description,schema:{type:p.type}})),
        responses:Object.fromEntries((ep.responses||[]).map(r=>[r.code,{description:r.description}])),
        security:ep.auth!=="None"?[{bearerAuth:[]}]:[],
      };
      return acc;
    },{}),
    components:{securitySchemes:{bearerAuth:{type:"http",scheme:"bearer"}}}
  }, null, 2);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Zap className="h-7 w-7 text-[var(--gs-teal)]"/>API Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{endpoints.length} endpoints · Visual API design + OpenAPI export</p>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-[var(--gs-surface-2)] rounded-lg p-1 gap-1">
            {[["builder","🛠 Builder"],["openapi","📋 OpenAPI"]].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)} className={`text-xs px-3 py-1.5 rounded-md ${tab===t?"bg-white shadow text-[var(--gs-teal)] font-medium":"text-[var(--gs-muted)]"}`}>{l}</button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={addEndpoint}><Plus className="h-3.5 w-3.5 mr-1"/>Add Endpoint</Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save}>
            {saved?<><Check className="h-3.5 w-3.5 mr-1"/>Saved</>:<><Save className="h-3.5 w-3.5 mr-1"/>Save</>}
          </Button>
        </div>
      </div>

      {tab==="builder"&&(
        <div className="space-y-4">
          {/* API Info */}
          <Card className="p-4">
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide mb-3">API Information</p>
            <div className="grid sm:grid-cols-4 gap-3">
              <div><label className="text-xs font-medium mb-1 block">API Title</label><Input className="h-8 text-xs" value={apiInfo.title} onChange={e=>setApiInfo(p=>({...p,title:e.target.value}))}/></div>
              <div><label className="text-xs font-medium mb-1 block">Version</label><Input className="h-8 text-xs" value={apiInfo.version} onChange={e=>setApiInfo(p=>({...p,version:e.target.value}))}/></div>
              <div><label className="text-xs font-medium mb-1 block">Base URL</label><Input className="h-8 text-xs font-mono" value={apiInfo.baseUrl} onChange={e=>setApiInfo(p=>({...p,baseUrl:e.target.value}))}/></div>
              <div><label className="text-xs font-medium mb-1 block">Description</label><Input className="h-8 text-xs" value={apiInfo.description} onChange={e=>setApiInfo(p=>({...p,description:e.target.value}))}/></div>
            </div>
          </Card>

          {/* Endpoints by tag */}
          {Object.entries(grouped).map(([tag,eps])=>(
            <div key={tag}>
              <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide mb-2 flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-[var(--gs-teal)] inline-block"/>{tag} ({eps.length})</p>
              <div className="space-y-2">{eps.map(ep=><EndpointCard key={ep.id} ep={ep} onChange={c=>updEp(ep.id,c)} onDelete={()=>delEp(ep.id)}/>)}</div>
            </div>
          ))}
          {endpoints.length===0&&<Card className="p-12 text-center text-sm text-[var(--gs-muted)]"><Zap className="h-10 w-10 mx-auto mb-3"/>"Add Endpoint" se shuru karo</Card>}
        </div>
      )}

      {tab==="openapi"&&(
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--gs-muted)] font-semibold uppercase tracking-wide">OpenAPI 3.0 JSON</p>
            <button onClick={()=>{navigator.clipboard?.writeText(openApiJson);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy JSON</button>
          </div>
          <pre className="bg-[#0a0a0a] text-yellow-300 text-xs p-4 rounded-xl overflow-auto font-mono max-h-[500px]">{openApiJson}</pre>
        </div>
      )}
    </div>
  );
}
