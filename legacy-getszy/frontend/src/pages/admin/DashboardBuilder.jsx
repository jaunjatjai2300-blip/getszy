import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { LayoutDashboard, Plus, Trash2, Save, Check, GripVertical, BarChart2, TrendingUp, PieChart, Activity, Hash } from "lucide-react";
import { toast } from "sonner";

const WIDGET_TYPES = [
  { value:"stat", label:"Stat Card", icon:<Hash className="h-4 w-4"/>, preview: (w)=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl"><p className="text-xs text-[var(--gs-muted)]">{w.title||"Metric"}</p><p className="text-3xl font-bold mt-1">{w.value||"0"}</p>{w.change&&<p className={`text-xs mt-1 ${w.change>0?"text-emerald-500":"text-rose-500"}`}>{w.change>0?"↑":"↓"} {Math.abs(w.change)}%</p>}</div> },
  { value:"line", label:"Line Chart", icon:<TrendingUp className="h-4 w-4"/>, preview: ()=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl h-32 flex items-center justify-center text-[var(--gs-muted)]"><TrendingUp className="h-8 w-8"/></div> },
  { value:"bar", label:"Bar Chart", icon:<BarChart2 className="h-4 w-4"/>, preview: ()=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl h-32 flex items-center justify-center text-[var(--gs-muted)]"><BarChart2 className="h-8 w-8"/></div> },
  { value:"pie", label:"Pie Chart", icon:<PieChart className="h-4 w-4"/>, preview: ()=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl h-32 flex items-center justify-center text-[var(--gs-muted)]"><PieChart className="h-8 w-8"/></div> },
  { value:"activity", label:"Activity Feed", icon:<Activity className="h-4 w-4"/>, preview: ()=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl space-y-2">{[1,2,3].map(i=><div key={i} className="flex gap-2 items-center"><div className="h-2 w-2 rounded-full bg-[var(--gs-teal)]"/><div className="h-2 rounded bg-[var(--gs-border)] flex-1"/></div>)}</div> },
  { value:"table", label:"Data Table", icon:<LayoutDashboard className="h-4 w-4"/>, preview: ()=><div className="p-4 bg-[var(--gs-surface-2)] rounded-xl space-y-1">{[1,2,3].map(i=><div key={i} className="flex gap-2"><div className="h-3 rounded bg-[var(--gs-border)] flex-1"/><div className="h-3 rounded bg-[var(--gs-border)] w-16"/></div>)}</div> },
];

const SIZE_OPTS = [{ value:"1", label:"1 col (25%)" },{ value:"2", label:"2 cols (50%)" },{ value:"3", label:"3 cols (75%)" },{ value:"4", label:"4 cols (100%)" }];

let uid = ()=>Math.random().toString(36).slice(2,8);

export default function DashboardBuilder() {
  const [title, setTitle] = useState("My Dashboard");
  const [widgets, setWidgets] = useState([
    { id:uid(), type:"stat", title:"Total Revenue", value:"₹12,430", change:8, size:"1" },
    { id:uid(), type:"stat", title:"Active Users", value:"1,204", change:12, size:"1" },
    { id:uid(), type:"stat", title:"Orders", value:"342", change:-3, size:"1" },
    { id:uid(), type:"line", title:"Revenue Trend", size:"3" },
  ]);
  const [selected, setSelected] = useState(null);
  const [saved, setSaved] = useState(false);

  const add = (type)=>setWidgets(p=>[...p,{ id:uid(), type, title:WIDGET_TYPES.find(t=>t.value===type)?.label||"Widget", value:"0", size:"2" }]);
  const update = (id,k,v)=>setWidgets(p=>p.map(w=>w.id===id?{...w,[k]:v}:w));
  const del = (id)=>{ setWidgets(p=>p.filter(w=>w.id!==id)); if(selected===id)setSelected(null); };
  const save = ()=>{ setSaved(true); toast.success("Dashboard saved!"); setTimeout(()=>setSaved(false),2000); };

  const sel = widgets.find(w=>w.id===selected);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><LayoutDashboard className="h-7 w-7 text-[var(--gs-teal)]"/>Dashboard Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">Custom metrics dashboards banao — drag & drop</p>
        </div>
        <div className="flex gap-2">
          <Input className="h-9 w-48 text-sm font-semibold" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Dashboard Title"/>
          <Button size="sm" className="bg-[var(--gs-teal)]" onClick={save}>
            {saved?<><Check className="h-3.5 w-3.5 mr-1"/>Saved</>:<><Save className="h-3.5 w-3.5 mr-1"/>Save</>}
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[240px_1fr_240px] gap-5">
        {/* Widget Palette */}
        <div className="space-y-3">
          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Add Widget</p>
          {WIDGET_TYPES.map(t=>(
            <button key={t.value} onClick={()=>add(t.value)}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-[var(--gs-surface-2)] hover:bg-[var(--gs-surface-3)] hover:text-[var(--gs-teal)] transition-colors text-sm text-left">
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {/* Canvas */}
        <div>
          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide mb-3">{widgets.length} Widgets</p>
          <div className="grid grid-cols-4 gap-3">
            {widgets.map(w=>{
              const wt = WIDGET_TYPES.find(t=>t.value===w.type);
              return (
                <div key={w.id} onClick={()=>setSelected(w.id)}
                  className={`col-span-${w.size||2} cursor-pointer rounded-xl ring-2 transition-all ${selected===w.id?"ring-[var(--gs-teal)]":"ring-transparent hover:ring-[var(--gs-teal)]/30"}`}>
                  <div className="relative">
                    {wt?.preview(w)}
                    <div className="absolute top-2 right-2 flex gap-1">
                      <button onClick={e=>{e.stopPropagation();del(w.id);}} className="h-5 w-5 rounded bg-rose-500 text-white grid place-items-center opacity-0 group-hover:opacity-100 hover:opacity-100"><Trash2 className="h-3 w-3"/></button>
                    </div>
                    <div className="absolute top-2 left-2 text-[var(--gs-muted)] opacity-40 hover:opacity-100"><GripVertical className="h-4 w-4"/></div>
                    <p className="text-[10px] text-center text-[var(--gs-muted)] mt-1 mb-1">{w.title}</p>
                  </div>
                </div>
              );
            })}
          </div>
          {widgets.length===0&&<Card className="p-12 text-center text-sm text-[var(--gs-muted)]">← Left se widget add karo</Card>}
        </div>

        {/* Properties Panel */}
        <div className="space-y-3">
          <p className="text-xs font-semibold text-[var(--gs-muted)] uppercase tracking-wide">Properties</p>
          {!sel?<Card className="p-6 text-center text-xs text-[var(--gs-muted)]">Widget select karo to edit karein</Card>:(
            <Card className="p-4 space-y-3">
              <div><label className="text-xs font-medium mb-1 block">Title</label>
                <Input className="h-8 text-xs" value={sel.title||""} onChange={e=>update(sel.id,"title",e.target.value)}/></div>
              {sel.type==="stat"&&<>
                <div><label className="text-xs font-medium mb-1 block">Value</label>
                  <Input className="h-8 text-xs" value={sel.value||""} onChange={e=>update(sel.id,"value",e.target.value)}/></div>
                <div><label className="text-xs font-medium mb-1 block">Change % (+/-)</label>
                  <Input type="number" className="h-8 text-xs" value={sel.change||0} onChange={e=>update(sel.id,"change",parseFloat(e.target.value))}/></div>
              </>}
              <div><label className="text-xs font-medium mb-1 block">Width</label>
                <Select value={sel.size||"2"} onValueChange={v=>update(sel.id,"size",v)}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue/></SelectTrigger>
                  <SelectContent>{SIZE_OPTS.map(s=><SelectItem key={s.value} value={s.value} className="text-xs">{s.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><label className="text-xs font-medium mb-1 block">Data Source</label>
                <Select><SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Manual / API"/></SelectTrigger>
                  <SelectContent><SelectItem value="manual" className="text-xs">Manual Value</SelectItem><SelectItem value="api" className="text-xs">API Endpoint</SelectItem><SelectItem value="db" className="text-xs">Database Query</SelectItem></SelectContent>
                </Select>
              </div>
              <Button size="sm" variant="destructive" className="w-full h-8 text-xs" onClick={()=>del(sel.id)}><Trash2 className="h-3 w-3 mr-1"/>Remove Widget</Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
