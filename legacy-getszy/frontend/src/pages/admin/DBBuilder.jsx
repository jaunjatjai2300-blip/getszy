import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Database, Plus, Trash2, Save, Check, Copy, Key, Link, AlertCircle, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";

const TYPES = ["VARCHAR(255)","TEXT","INT","BIGINT","FLOAT","DECIMAL(10,2)","BOOLEAN","DATE","DATETIME","TIMESTAMP","JSON","UUID","SERIAL"];
const CONSTRAINTS = ["PRIMARY KEY","NOT NULL","UNIQUE","DEFAULT NULL","AUTO_INCREMENT","INDEXED"];

let uid=()=>Math.random().toString(36).slice(2,8);

const DEFAULT_TABLES = [
  { id:uid(), name:"users", expanded:true, columns:[
    { id:uid(), name:"id", type:"UUID", constraint:"PRIMARY KEY", nullable:false, default_val:"gen_random_uuid()" },
    { id:uid(), name:"email", type:"VARCHAR(255)", constraint:"UNIQUE", nullable:false, default_val:"" },
    { id:uid(), name:"name", type:"VARCHAR(255)", constraint:"NOT NULL", nullable:false, default_val:"" },
    { id:uid(), name:"created_at", type:"TIMESTAMP", constraint:"DEFAULT NULL", nullable:true, default_val:"NOW()" },
  ]},
  { id:uid(), name:"products", expanded:false, columns:[
    { id:uid(), name:"id", type:"UUID", constraint:"PRIMARY KEY", nullable:false, default_val:"gen_random_uuid()" },
    { id:uid(), name:"name", type:"VARCHAR(255)", constraint:"NOT NULL", nullable:false, default_val:"" },
    { id:uid(), name:"price", type:"DECIMAL(10,2)", constraint:"NOT NULL", nullable:false, default_val:"0" },
    { id:uid(), name:"stock", type:"INT", constraint:"DEFAULT NULL", nullable:true, default_val:"0" },
  ]},
];

function TableCard({ table, onChange, onDelete }) {
  const toggle = ()=>onChange({expanded:!table.expanded});
  const addCol = ()=>onChange({columns:[...table.columns,{id:uid(),name:"",type:"VARCHAR(255)",constraint:"DEFAULT NULL",nullable:true,default_val:""}]});
  const updCol = (cid,k,v)=>onChange({columns:table.columns.map(c=>c.id===cid?{...c,[k]:v}:c)});
  const delCol = (cid)=>onChange({columns:table.columns.filter(c=>c.id!==cid)});

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-3 p-3 bg-[var(--gs-surface-2)] cursor-pointer" onClick={toggle}>
        {table.expanded?<ChevronDown className="h-4 w-4 text-[var(--gs-muted)]"/>:<ChevronRight className="h-4 w-4 text-[var(--gs-muted)]"/>}
        <Database className="h-4 w-4 text-[var(--gs-teal)]"/>
        <Input className="h-7 text-sm font-mono font-semibold bg-transparent border-0 p-0 focus-visible:ring-0 flex-1" value={table.name} onChange={e=>{e.stopPropagation();onChange({name:e.target.value});}} onClick={e=>e.stopPropagation()}/>
        <span className="text-[10px] text-[var(--gs-muted)]">{table.columns.length} cols</span>
        <button onClick={e=>{e.stopPropagation();onDelete();}} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-3.5 w-3.5"/></button>
      </div>

      {table.expanded&&(
        <div className="p-3">
          <table className="w-full text-xs mb-2">
            <thead><tr className="text-[var(--gs-muted)]">
              <th className="text-left pb-2 pr-2">Column Name</th>
              <th className="text-left pb-2 pr-2">Type</th>
              <th className="text-left pb-2 pr-2">Constraint</th>
              <th className="text-left pb-2 pr-2">Default</th>
              <th className="text-left pb-2">Nullable</th>
              <th className="pb-2 w-6"/>
            </tr></thead>
            <tbody>{table.columns.map(c=>(
              <tr key={c.id} className="border-t border-[var(--gs-border)]">
                <td className="py-1.5 pr-2">
                  <div className="flex items-center gap-1">
                    {(c.constraint==="PRIMARY KEY"||c.name==="id")&&<Key className="h-3 w-3 text-amber-500 flex-shrink-0"/>}
                    <Input className="h-7 text-xs font-mono border-0 bg-[var(--gs-surface-2)] px-2" value={c.name} onChange={e=>updCol(c.id,"name",e.target.value)}/>
                  </div>
                </td>
                <td className="py-1.5 pr-2">
                  <Select value={c.type} onValueChange={v=>updCol(c.id,"type",v)}>
                    <SelectTrigger className="h-7 text-xs w-36"><SelectValue/></SelectTrigger>
                    <SelectContent>{TYPES.map(t=><SelectItem key={t} value={t} className="text-xs font-mono">{t}</SelectItem>)}</SelectContent>
                  </Select>
                </td>
                <td className="py-1.5 pr-2">
                  <Select value={c.constraint} onValueChange={v=>updCol(c.id,"constraint",v)}>
                    <SelectTrigger className="h-7 text-xs w-36"><SelectValue/></SelectTrigger>
                    <SelectContent>{CONSTRAINTS.map(t=><SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>)}</SelectContent>
                  </Select>
                </td>
                <td className="py-1.5 pr-2"><Input className="h-7 text-xs font-mono w-24" value={c.default_val||""} onChange={e=>updCol(c.id,"default_val",e.target.value)} placeholder="NULL"/></td>
                <td className="py-1.5 text-center"><input type="checkbox" checked={!!c.nullable} onChange={e=>updCol(c.id,"nullable",e.target.checked)} className="accent-[var(--gs-teal)]"/></td>
                <td className="py-1.5"><button onClick={()=>delCol(c.id)} className="text-rose-400 hover:text-rose-600"><Trash2 className="h-3 w-3"/></button></td>
              </tr>
            ))}</tbody>
          </table>
          <button onClick={addCol} className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline"><Plus className="h-3 w-3"/>Add Column</button>
        </div>
      )}
    </Card>
  );
}

export default function DBBuilder() {
  const [tables, setTables] = useState(DEFAULT_TABLES);
  const [tab, setTab] = useState("visual");
  const [saved, setSaved] = useState(false);

  const addTable = ()=>setTables(p=>[...p,{id:uid(),name:"new_table",expanded:true,columns:[{id:uid(),name:"id",type:"UUID",constraint:"PRIMARY KEY",nullable:false,default_val:"gen_random_uuid()"}]}]);
  const updTable = (id,changes)=>setTables(p=>p.map(t=>t.id===id?{...t,...changes}:t));
  const delTable = (id)=>setTables(p=>p.filter(t=>t.id!==id));
  const save = ()=>{setSaved(true);toast.success("Schema saved!");setTimeout(()=>setSaved(false),2000);};

  const sqlOutput = tables.map(t=>{
    const cols = t.columns.map(c=>{
      let def = `  ${c.name} ${c.type}`;
      if (c.constraint&&c.constraint!=="DEFAULT NULL") def+=` ${c.constraint}`;
      if (c.default_val) def+=` DEFAULT ${c.default_val}`;
      if (!c.nullable&&c.constraint!=="PRIMARY KEY") def+=` NOT NULL`;
      return def;
    }).join(",\n");
    return `CREATE TABLE ${t.name} (\n${cols}\n);`;
  }).join("\n\n");

  const prismaOutput = tables.map(t=>{
    const cols = t.columns.map(c=>{
      const ptype = c.type.startsWith("VARCHAR")||c.type==="TEXT"?"String":c.type==="BOOLEAN"?"Boolean":c.type.includes("INT")||c.type==="SERIAL"?"Int":c.type.includes("FLOAT")||c.type.includes("DECIMAL")?"Float":c.type.includes("DATE")||c.type.includes("TIMESTAMP")?"DateTime":"String";
      const opts = c.constraint==="PRIMARY KEY"?"  @id":c.constraint==="UNIQUE"?"  @unique":"";
      const defVal = c.default_val?`  @default(${c.default_val.includes("()")?c.default_val.toLowerCase().replace("gen_random_uuid()","uuid()").replace("now()","now()"):JSON.stringify(c.default_val)})`:c.nullable?"?":"";
      return `  ${c.name} ${ptype}${c.nullable?"?":""}${opts}${c.default_val?` @default(${c.default_val.toLowerCase().replace("gen_random_uuid()","uuid()").replace("now()","now()")})`:""}\n`;
    }).join("");
    return `model ${t.name.replace(/_([a-z])/g,(m,l)=>l.toUpperCase()).replace(/^\w/,c=>c.toUpperCase())} {\n${cols}}`;
  }).join("\n\n");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Database className="h-7 w-7 text-[var(--gs-teal)]"/>DB Schema Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{tables.length} tables · Visual database schema designer</p>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-[var(--gs-surface-2)] rounded-lg p-1 gap-1">
            {[["visual","🗄 Visual"],["sql","SQL"],["prisma","Prisma"]].map(([t,l])=>(
              <button key={t} onClick={()=>setTab(t)} className={`text-xs px-3 py-1.5 rounded-md ${tab===t?"bg-white shadow text-[var(--gs-teal)] font-medium":"text-[var(--gs-muted)]"}`}>{l}</button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={addTable}><Plus className="h-3.5 w-3.5 mr-1"/>Add Table</Button>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save}>
            {saved?<><Check className="h-3.5 w-3.5 mr-1"/>Saved</>:<><Save className="h-3.5 w-3.5 mr-1"/>Save</>}
          </Button>
        </div>
      </div>

      {tab==="visual"&&(
        <div className="space-y-3">
          {tables.length===0?<Card className="p-12 text-center text-sm text-[var(--gs-muted)]"><Database className="h-10 w-10 mx-auto mb-3"/>"Add Table" se shuru karo</Card>:tables.map(t=><TableCard key={t.id} table={t} onChange={c=>updTable(t.id,c)} onDelete={()=>delTable(t.id)}/>)}
        </div>
      )}

      {tab==="sql"&&(
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--gs-muted)] font-semibold uppercase tracking-wide">SQL CREATE Statements</p>
            <button onClick={()=>{navigator.clipboard?.writeText(sqlOutput);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy</button>
          </div>
          <pre className="bg-[#0a0a0a] text-blue-300 text-xs p-4 rounded-xl overflow-x-auto font-mono max-h-[500px]">{sqlOutput}</pre>
        </div>
      )}

      {tab==="prisma"&&(
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--gs-muted)] font-semibold uppercase tracking-wide">Prisma Schema</p>
            <button onClick={()=>{navigator.clipboard?.writeText(prismaOutput);toast.success("Copied!");}} className="text-xs text-[var(--gs-teal)] flex items-center gap-1"><Copy className="h-3 w-3"/>Copy</button>
          </div>
          <pre className="bg-[#0a0a0a] text-purple-300 text-xs p-4 rounded-xl overflow-x-auto font-mono max-h-[500px]">{prismaOutput}</pre>
        </div>
      )}
    </div>
  );
}
