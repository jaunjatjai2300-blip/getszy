import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Mail, Plus, Trash2, Save, Check, Eye, Code2, Copy, MoveUp, MoveDown } from "lucide-react";
import { toast } from "sonner";

const BLOCK_TYPES = [
  { value:"header", label:"Header / Logo", icon:"🏷️" },
  { value:"hero", label:"Hero Banner", icon:"🖼️" },
  { value:"text", label:"Text Block", icon:"📝" },
  { value:"button", label:"Button / CTA", icon:"🔘" },
  { value:"image", label:"Image", icon:"🌄" },
  { value:"divider", label:"Divider", icon:"➖" },
  { value:"footer", label:"Footer", icon:"📌" },
  { value:"social", label:"Social Links", icon:"📱" },
  { value:"columns", label:"2 Columns", icon:"⬛⬛" },
];

let uid=()=>Math.random().toString(36).slice(2,8);

const DEFAULT_BLOCKS = [
  { id:uid(), type:"header", content:{ brand:"Getszy", tagline:"India's AI Business OS" } },
  { id:uid(), type:"hero", content:{ headline:"Welcome aboard! 🚀", subtext:"Aapka account ready hai." } },
  { id:uid(), type:"text", content:{ text:"Namaste! Getszy mein aapka swagat hai. Yahan se aap apne business ke liye AI tools, websites, aur automation set up kar sakte hain." } },
  { id:uid(), type:"button", content:{ label:"Dashboard Kholo →", url:"https://getszy.com/admin", color:"#00c2b2" } },
  { id:uid(), type:"footer", content:{ address:"Getszy Inc. · India · Unsubscribe" } },
];

function BlockPreview({ block, selected, onSelect, onDelete, onMove, total, index }) {
  const b = block.content||{};
  const rendered = (()=>{
    if (block.type==="header") return <div className="text-center py-4 bg-[var(--gs-surface-2)]"><p className="font-bold text-lg">{b.brand||"Brand"}</p><p className="text-xs text-[var(--gs-muted)]">{b.tagline}</p></div>;
    if (block.type==="hero") return <div className="text-center py-8 bg-gradient-to-r from-[var(--gs-teal)]/10 to-purple-100"><h1 className="text-2xl font-bold">{b.headline||"Headline"}</h1><p className="text-sm text-[var(--gs-muted)] mt-2">{b.subtext}</p></div>;
    if (block.type==="text") return <div className="py-4 px-6 text-sm text-[var(--gs-muted)]">{b.text||"Email content…"}</div>;
    if (block.type==="button") return <div className="text-center py-4"><a href="#" className="inline-block px-6 py-2.5 rounded-lg text-white text-sm font-medium" style={{background:b.color||"#00c2b2"}}>{b.label||"Click Here"}</a></div>;
    if (block.type==="image") return <div className="py-2 px-6"><div className="w-full h-32 bg-[var(--gs-surface-2)] rounded-lg flex items-center justify-center text-2xl">{b.emoji||"🌄"}</div></div>;
    if (block.type==="divider") return <div className="py-2 px-6"><hr className="border-[var(--gs-border)]"/></div>;
    if (block.type==="footer") return <div className="text-center py-4 text-[10px] text-[var(--gs-muted)] bg-[var(--gs-surface-2)]">{b.address||"Company Address · Unsubscribe"}</div>;
    if (block.type==="social") return <div className="text-center py-3 flex justify-center gap-3 text-lg">{["𝕏","📸","💼","▶️"].map((s,i)=><span key={i}>{s}</span>)}</div>;
    if (block.type==="columns") return <div className="flex gap-3 py-3 px-6">{[b.col1||"Left column content",b.col2||"Right column content"].map((c,i)=><div key={i} className="flex-1 p-3 bg-[var(--gs-surface-2)] rounded text-xs text-[var(--gs-muted)]">{c}</div>)}</div>;
    return null;
  })();

  return (
    <div onClick={()=>onSelect(block.id)} className={`relative cursor-pointer ring-2 transition-all rounded ${selected?"ring-[var(--gs-teal)]":"ring-transparent hover:ring-[var(--gs-teal)]/30"}`}>
      {rendered}
      <div className="absolute top-1 right-1 flex gap-1 opacity-0 hover:opacity-100 focus-within:opacity-100" style={{opacity:selected?1:undefined}}>
        {index>0&&<button onClick={e=>{e.stopPropagation();onMove(block.id,-1)}} className="h-5 w-5 bg-white shadow rounded grid place-items-center"><MoveUp className="h-3 w-3"/></button>}
        {index<total-1&&<button onClick={e=>{e.stopPropagation();onMove(block.id,1)}} className="h-5 w-5 bg-white shadow rounded grid place-items-center"><MoveDown className="h-3 w-3"/></button>}
        <button onClick={e=>{e.stopPropagation();onDelete(block.id)}} className="h-5 w-5 bg-rose-500 text-white rounded grid place-items-center"><Trash2 className="h-2.5 w-2.5"/></button>
      </div>
    </div>
  );
}

export default function EmailBuilder() {
  const [blocks, setBlocks] = useState(DEFAULT_BLOCKS);
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("builder");
  const [meta, setMeta] = useState({ subject:"Welcome to Getszy!", preheader:"Your account is ready" });
  const [saved, setSaved] = useState(false);

  const add = (type)=>{
    const defaults = { header:{brand:"Getszy",tagline:""}, hero:{headline:"Big Headline",subtext:"Supporting text"}, text:{text:"Your email content here…"}, button:{label:"Click Here",url:"#",color:"#00c2b2"}, image:{emoji:"🌄",alt:""}, divider:{}, footer:{address:"© 2025 Getszy · India · Unsubscribe"}, social:{}, columns:{col1:"Column 1",col2:"Column 2"} };
    setBlocks(p=>[...p,{id:uid(),type,content:defaults[type]||{}}]);
  };

  const update = (id,content)=>setBlocks(p=>p.map(b=>b.id===id?{...b,content:{...b.content,...content}}:b));
  const del = (id)=>{setBlocks(p=>p.filter(b=>b.id!==id));if(selected===id)setSelected(null);};
  const move = (id,dir)=>{
    setBlocks(p=>{const i=p.findIndex(b=>b.id===id);if(i<0)return p;const a=[...p];[a[i],a[i+dir]]=[a[i+dir],a[i]];return a;});
  };

  const selBlock = blocks.find(b=>b.id===selected);

  const htmlOutput = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${meta.subject}</title></head><body style="font-family:sans-serif;max-width:600px;margin:0 auto">
<!-- Subject: ${meta.subject} -->
<!-- Preheader: ${meta.preheader} -->
${blocks.map(b=>{
  const c=b.content||{};
  if(b.type==="header")return`<div style="text-align:center;padding:20px;background:#f8f9fa"><h1 style="margin:0">${c.brand}</h1><p style="margin:4px 0 0;color:#888">${c.tagline||""}</p></div>`;
  if(b.type==="hero")return`<div style="text-align:center;padding:40px 20px;background:linear-gradient(135deg,#e0f7f5,#f3e8ff)"><h1>${c.headline||""}</h1><p style="color:#666">${c.subtext||""}</p></div>`;
  if(b.type==="text")return`<p style="padding:16px 24px;color:#444;line-height:1.6">${c.text||""}</p>`;
  if(b.type==="button")return`<div style="text-align:center;padding:16px"><a href="${c.url||"#"}" style="background:${c.color||"#00c2b2"};color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">${c.label||"Click"}</a></div>`;
  if(b.type==="divider")return`<hr style="margin:8px 24px;border:1px solid #eee">`;
  if(b.type==="footer")return`<div style="text-align:center;padding:16px;color:#aaa;font-size:12px">${c.address||""}</div>`;
  return "";
}).join("\n")}
</body></html>`;

  const save = ()=>{setSaved(true);toast.success("Email template saved!");setTimeout(()=>setSaved(false),2000);};

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Mail className="h-7 w-7 text-[var(--gs-teal)]"/>Email Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Drag & drop email templates — export HTML</p>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-[var(--gs-surface-2)] rounded-lg p-1 gap-1">
            {[["builder","🛠 Builder"],["preview","👁 Preview"],["html","</> HTML"]].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)} className={`text-xs px-3 py-1.5 rounded-md transition-all ${tab===t?"bg-white shadow text-[var(--gs-teal)] font-medium":"text-[var(--gs-muted)] hover:text-foreground"}`}>{l}</button>
            ))}
          </div>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save}>
            {saved?<><Check className="h-3.5 w-3.5 mr-1"/>Saved</>:<><Save className="h-3.5 w-3.5 mr-1"/>Save</>}
          </Button>
        </div>
      </div>

      {tab==="builder"&&(
        <div className="grid lg:grid-cols-[220px_1fr_260px] gap-5">
          {/* Palette */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Add Block</p>
            {BLOCK_TYPES.map(t=>(
              <button key={t.value} onClick={()=>add(t.value)}
                className="w-full flex items-center gap-2.5 p-2.5 rounded-xl bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] hover:text-[var(--gs-teal)] text-xs text-left transition-colors">
                <span className="text-base">{t.icon}</span>{t.label}
              </button>
            ))}
          </div>

          {/* Canvas */}
          <div>
            <div className="space-y-2 mb-3">
              <Input className="h-9 text-sm" placeholder="Email Subject Line" value={meta.subject} onChange={e=>setMeta(p=>({...p,subject:e.target.value}))}/>
              <Input className="h-8 text-xs" placeholder="Preheader text (preview in inbox)" value={meta.preheader} onChange={e=>setMeta(p=>({...p,preheader:e.target.value}))}/>
            </div>
            <div className="border border-[var(--gs-border)] rounded-xl overflow-hidden bg-white" style={{maxWidth:"600px",margin:"0 auto"}}>
              {blocks.map((b,i)=><BlockPreview key={b.id} block={b} selected={selected===b.id} onSelect={setSelected} onDelete={del} onMove={move} index={i} total={blocks.length}/>)}
              {blocks.length===0&&<div className="p-12 text-center text-sm text-[var(--gs-muted)]">← Block add karo</div>}
            </div>
          </div>

          {/* Properties */}
          <div>
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide mb-3">Properties</p>
            {!selBlock?<Card className="p-6 text-center text-xs text-[var(--gs-muted)]">Block select karo to edit karein</Card>:(
              <Card className="p-4 space-y-3">
                <p className="text-xs font-semibold capitalize">{selBlock.type} Block</p>
                {selBlock.type==="header"&&<><Input className="h-8 text-xs" placeholder="Brand name" value={selBlock.content?.brand||""} onChange={e=>update(selBlock.id,{brand:e.target.value})}/><Input className="h-8 text-xs" placeholder="Tagline" value={selBlock.content?.tagline||""} onChange={e=>update(selBlock.id,{tagline:e.target.value})}/></>}
                {selBlock.type==="hero"&&<><Input className="h-8 text-xs" placeholder="Headline" value={selBlock.content?.headline||""} onChange={e=>update(selBlock.id,{headline:e.target.value})}/><Input className="h-8 text-xs" placeholder="Subtext" value={selBlock.content?.subtext||""} onChange={e=>update(selBlock.id,{subtext:e.target.value})}/></>}
                {selBlock.type==="text"&&<Textarea className="text-xs" rows={5} value={selBlock.content?.text||""} onChange={e=>update(selBlock.id,{text:e.target.value})}/>}
                {selBlock.type==="button"&&<><Input className="h-8 text-xs" placeholder="Button Label" value={selBlock.content?.label||""} onChange={e=>update(selBlock.id,{label:e.target.value})}/><Input className="h-8 text-xs" placeholder="URL" value={selBlock.content?.url||""} onChange={e=>update(selBlock.id,{url:e.target.value})}/><Input type="color" className="h-8 w-full" value={selBlock.content?.color||"#00c2b2"} onChange={e=>update(selBlock.id,{color:e.target.value})}/></>}
                {selBlock.type==="footer"&&<Textarea className="text-xs" rows={3} value={selBlock.content?.address||""} onChange={e=>update(selBlock.id,{address:e.target.value})}/>}
                {selBlock.type==="columns"&&<><Textarea className="text-xs" rows={3} placeholder="Left column" value={selBlock.content?.col1||""} onChange={e=>update(selBlock.id,{col1:e.target.value})}/><Textarea className="text-xs" rows={3} placeholder="Right column" value={selBlock.content?.col2||""} onChange={e=>update(selBlock.id,{col2:e.target.value})}/></>}
                <Button size="sm" variant="destructive" className="w-full h-8 text-xs" onClick={()=>del(selBlock.id)}><Trash2 className="h-3 w-3 mr-1"/>Remove</Button>
              </Card>
            )}
          </div>
        </div>
      )}

      {tab==="preview"&&(
        <div className="max-w-[600px] mx-auto border border-[var(--gs-border)] rounded-xl overflow-hidden bg-white">
          {blocks.map((b,i)=><BlockPreview key={b.id} block={b} selected={false} onSelect={()=>{}} onDelete={()=>{}} onMove={()=>{}} index={i} total={blocks.length}/>)}
        </div>
      )}

      {tab==="html"&&(
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">HTML Output</p>
            <button onClick={()=>{navigator.clipboard?.writeText(htmlOutput);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy HTML</button>
          </div>
          <pre className="bg-[#0a0a0a] text-green-400 text-xs p-4 rounded-xl overflow-x-auto font-mono max-h-96 whitespace-pre-wrap">{htmlOutput}</pre>
        </div>
      )}
    </div>
  );
}
