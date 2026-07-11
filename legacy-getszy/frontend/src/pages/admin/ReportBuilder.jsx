import { useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { BarChart3, Plus, Trash2, Download, RefreshCw, Loader2, Table, TrendingUp, PieChart as PieIcon } from "lucide-react";
import { toast } from "sonner";
import { api, fmtINR } from "@/lib/api";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";

const METRICS = ["Revenue","Orders","New Users","AI Jobs","Credits Used","Products Sold","Refunds","Subscriptions"];
const CHART_TYPES = ["Bar Chart","Line Chart","Area Chart","Pie Chart","Table"];
const DATE_RANGES = ["Last 7 days","Last 30 days","Last 90 days","This month","This year","All time"];
const COLORS = ["#2F7E7A","#C58B7A","#7C3AED","#F59E0B","#EC4899","#06B6D4"];

let _id = () => Math.random().toString(36).slice(2,8);

function ChartWidget({ widget, data, loading }) {
  const d = data || [];
  if (loading) return <div className="h-48 animate-pulse bg-[var(--gs-surface-2)] rounded-xl"/>;
  if (d.length===0) return <div className="h-48 flex items-center justify-center text-sm text-[var(--gs-muted)]">Data nahi hai abhi</div>;

  if (widget.chartType==="Bar Chart") return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={d}><CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
        <XAxis dataKey="date" fontSize={10}/><YAxis fontSize={10}/>
        <Tooltip contentStyle={{fontSize:11}}/><Bar dataKey={widget.metric?.toLowerCase().replace(/ /g,"_")||"value"} fill={COLORS[0]} radius={[4,4,0,0]}/></BarChart>
    </ResponsiveContainer>
  );
  if (widget.chartType==="Line Chart") return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={d}><CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
        <XAxis dataKey="date" fontSize={10}/><YAxis fontSize={10}/>
        <Tooltip contentStyle={{fontSize:11}}/><Line type="monotone" dataKey={widget.metric?.toLowerCase().replace(/ /g,"_")||"value"} stroke={COLORS[0]} strokeWidth={2}/></LineChart>
    </ResponsiveContainer>
  );
  if (widget.chartType==="Area Chart") return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={d}><defs><linearGradient id={`g${widget.id}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={COLORS[0]} stopOpacity={0.4}/><stop offset="100%" stopColor={COLORS[0]} stopOpacity={0}/>
      </linearGradient></defs>
        <CartesianGrid stroke="#E7D9CE" strokeDasharray="3 3"/>
        <XAxis dataKey="date" fontSize={10}/><YAxis fontSize={10}/>
        <Tooltip contentStyle={{fontSize:11}}/><Area type="monotone" dataKey={widget.metric?.toLowerCase().replace(/ /g,"_")||"value"} stroke={COLORS[0]} fill={`url(#g${widget.id})`}/></AreaChart>
    </ResponsiveContainer>
  );
  if (widget.chartType==="Pie Chart") return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart><Pie data={d.slice(0,6)} cx="50%" cy="50%" outerRadius={70} dataKey="value" label={({name,value})=>`${name}: ${value}`}>
        {d.slice(0,6).map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
      </Pie><Tooltip/></PieChart>
    </ResponsiveContainer>
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b">{Object.keys(d[0]||{}).map(k=><th key={k} className="text-left py-1.5 px-2 font-semibold text-[var(--gs-muted)]">{k}</th>)}</tr></thead>
        <tbody>{d.slice(0,10).map((row,i)=><tr key={i} className="border-b last:border-0">{Object.values(row).map((v,j)=><td key={j} className="py-1.5 px-2">{typeof v==="number"?v.toLocaleString("en-IN"):v}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export default function ReportBuilder() {
  const [title, setTitle] = useState("My Report");
  const [widgets, setWidgets] = useState([
    { id:_id(), name:"Revenue Trend",    metric:"Revenue",   chartType:"Area Chart", range:"Last 30 days" },
    { id:_id(), name:"Daily Orders",     metric:"Orders",    chartType:"Bar Chart",  range:"Last 7 days" },
    { id:_id(), name:"User Growth",      metric:"New Users", chartType:"Line Chart", range:"Last 30 days" },
  ]);
  const [seriesData, setSeriesData] = useState([]);
  const [founderData, setFounderData] = useState({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ser, found] = await Promise.allSettled([
        api.get("/admin/analytics/series?days=30"),
        api.get("/admin/founder-stats"),
      ]);
      if (ser.status==="fulfilled") setSeriesData(ser.value.data?.series||[]);
      if (found.status==="fulfilled") setFounderData(found.value.data||{});
    } finally { setLoading(false); }
  }, []);

  useEffect(()=>{load();},[load]);

  const addWidget = () => setWidgets(w=>[...w,{ id:_id(), name:`Widget ${w.length+1}`, metric:"Revenue", chartType:"Bar Chart", range:"Last 7 days" }]);
  const updateWidget = (id,data) => setWidgets(w=>w.map(x=>x.id===id?data:x));
  const deleteWidget = id => setWidgets(w=>w.filter(x=>x.id!==id));

  const getWidgetData = (widget) => {
    const key = widget.metric?.toLowerCase().replace(/ /g,"_");
    if (widget.metric==="Revenue"||widget.metric==="Orders") return seriesData;
    if (widget.metric==="New Users") return seriesData;
    if (widget.metric==="AI Jobs") return seriesData.map(d=>({...d, value: d.ai_jobs||0}));
    return seriesData;
  };

  const exportCSV = () => {
    const rows = [["Date","Revenue","Orders","New Users","AI Jobs"],...seriesData.map(d=>[d.date,d.revenue||0,d.orders||0,d.new_users||0,d.ai_jobs||0])];
    const csv = rows.map(r=>r.join(",")).join("\n");
    const blob = new Blob([csv],{type:"text/csv"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download=`${title}.csv`; a.click();
    toast.success("Report CSV download ho gayi!");
  };

  const summaryStats = [
    { label:"Total Revenue", value: fmtINR(seriesData.reduce((a,d)=>a+(d.revenue||0),0)) },
    { label:"Total Orders",  value: seriesData.reduce((a,d)=>a+(d.orders||0),0) },
    { label:"New Users",     value: seriesData.reduce((a,d)=>a+(d.new_users||0),0) },
    { label:"AI Jobs",       value: (founderData.total_videos||0)+(founderData.total_images||0) },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><BarChart3 className="h-7 w-7 text-cyan-600"/>Report Builder</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">Custom reports aur dashboards banao</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading?"animate-spin":""}`}/>Refresh</Button>
          <Button variant="outline" size="sm" onClick={exportCSV}><Download className="h-3.5 w-3.5 mr-1"/>Export CSV</Button>
        </div>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <Input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Report title…" className="h-8 w-64"/>
          <div className="flex gap-3">
            {summaryStats.map(s=>(
              <div key={s.label} className="text-center">
                <p className="font-display text-lg leading-none">{loading?"…":s.value}</p>
                <p className="text-[9px] text-[var(--gs-muted)] mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {widgets.map(w => (
          <Card key={w.id} className="p-4 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <Input value={w.name} onChange={e=>updateWidget(w.id,{...w,name:e.target.value})} className="h-7 text-xs font-semibold flex-1"/>
              <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-400 flex-shrink-0" onClick={()=>deleteWidget(w.id)}><Trash2 className="h-3.5 w-3.5"/></Button>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              <Select value={w.metric} onValueChange={v=>updateWidget(w.id,{...w,metric:v})}>
                <SelectTrigger className="h-7 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>{METRICS.map(m=><SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={w.chartType} onValueChange={v=>updateWidget(w.id,{...w,chartType:v})}>
                <SelectTrigger className="h-7 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>{CHART_TYPES.map(c=><SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <ChartWidget widget={w} data={getWidgetData(w)} loading={loading}/>
          </Card>
        ))}
        <button onClick={addWidget} className="border-2 border-dashed border-[var(--gs-border)] rounded-xl flex flex-col items-center justify-center gap-2 p-8 text-[var(--gs-muted)] hover:border-[var(--gs-teal)] hover:text-[var(--gs-teal)] transition-colors min-h-[200px]">
          <Plus className="h-8 w-8"/>
          <span className="text-sm font-medium">Widget Add Karo</span>
        </button>
      </div>
    </div>
  );
}
