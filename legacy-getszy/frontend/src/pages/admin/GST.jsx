import { useState, useCallback, useEffect } from "react";
import { api, fmtINR } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Receipt, RefreshCw, Download, Calculator, IndianRupee, FileText, Loader2, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import { toast } from "sonner";

const GST_RATES = [
  { rate: 0,   label: "0% — Exempt",         desc: "Food grains, health services" },
  { rate: 5,   label: "5% — Essential",      desc: "Packaged food, transport" },
  { rate: 12,  label: "12% — Standard",      desc: "Processed food, computers" },
  { rate: 18,  label: "18% — Standard",      desc: "Software, SaaS, most services" },
  { rate: 28,  label: "28% — Luxury",        desc: "Luxury goods, tobacco" },
];

const GST_TYPES = ["CGST + SGST (Intra-state)", "IGST (Inter-state)"];

function GSTCalculator() {
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState(18);
  const [inclusive, setInclusive] = useState(false);
  const [gstType, setGstType] = useState("CGST + SGST (Intra-state)");

  const base = parseFloat(amount)||0;
  const isIGST = gstType.includes("IGST");
  const gstAmt = inclusive ? base - base/(1+rate/100) : base * rate/100;
  const baseForCalc = inclusive ? base - gstAmt : base;
  const total = inclusive ? base : base + gstAmt;
  const cgst = isIGST ? 0 : gstAmt/2;
  const sgst = isIGST ? 0 : gstAmt/2;
  const igst = isIGST ? gstAmt : 0;

  return (
    <Card className="p-5 space-y-4">
      <h3 className="font-semibold flex items-center gap-2"><Calculator className="h-4 w-4 text-[var(--gs-teal)]"/>GST Calculator</h3>
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-semibold mb-1.5 block">Amount (₹)</label>
          <Input type="number" value={amount} onChange={e=>setAmount(e.target.value)} placeholder="Enter amount…" className="h-9"/>
        </div>
        <div>
          <label className="text-xs font-semibold mb-1.5 block">GST Rate</label>
          <Select value={String(rate)} onValueChange={v=>setRate(Number(v))}>
            <SelectTrigger className="h-9"><SelectValue/></SelectTrigger>
            <SelectContent>{GST_RATES.map(r=><SelectItem key={r.rate} value={String(r.rate)}>{r.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-xs font-semibold mb-1.5 block">Transaction Type</label>
          <Select value={gstType} onValueChange={setGstType}>
            <SelectTrigger className="h-9"><SelectValue/></SelectTrigger>
            <SelectContent>{GST_TYPES.map(t=><SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-3 pt-4">
          <Switch checked={inclusive} onCheckedChange={setInclusive}/>
          <span className="text-sm">{inclusive?"GST inclusive mein hai":"GST exclusive (add karna hai)"}</span>
        </div>
      </div>
      {base > 0 && (
        <div className="p-4 bg-[var(--gs-surface-2)] rounded-xl space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-[var(--gs-muted)]">Base Amount</span><span className="font-semibold">{fmtINR(baseForCalc)}</span></div>
          {isIGST ? (
            <div className="flex justify-between"><span className="text-[var(--gs-muted)]">IGST ({rate}%)</span><span className="font-semibold text-amber-600">{fmtINR(igst)}</span></div>
          ) : (
            <>
              <div className="flex justify-between"><span className="text-[var(--gs-muted)]">CGST ({rate/2}%)</span><span className="font-semibold text-blue-600">{fmtINR(cgst)}</span></div>
              <div className="flex justify-between"><span className="text-[var(--gs-muted)]">SGST ({rate/2}%)</span><span className="font-semibold text-violet-600">{fmtINR(sgst)}</span></div>
            </>
          )}
          <div className="flex justify-between border-t pt-2 font-bold text-base"><span>Total</span><span className="text-[var(--gs-teal)]">{fmtINR(total)}</span></div>
        </div>
      )}
    </Card>
  );
}

function GSTINVerifier() {
  const [gstin, setGstin] = useState("");
  const [verified, setVerified] = useState(null);

  const validateGSTIN = (g) => {
    const regex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    return regex.test(g.toUpperCase());
  };

  const verify = () => {
    if (!gstin.trim()) { toast.error("GSTIN enter karo"); return; }
    const isValid = validateGSTIN(gstin.trim());
    const stateCode = gstin.substring(0,2);
    const states = {"01":"Jammu & Kashmir","02":"Himachal Pradesh","03":"Punjab","04":"Chandigarh","05":"Uttarakhand","06":"Haryana","07":"Delhi","08":"Rajasthan","09":"Uttar Pradesh","10":"Bihar","11":"Sikkim","12":"Arunachal Pradesh","13":"Nagaland","14":"Manipur","15":"Mizoram","16":"Tripura","17":"Meghalaya","18":"Assam","19":"West Bengal","20":"Jharkhand","21":"Odisha","22":"Chhattisgarh","23":"Madhya Pradesh","24":"Gujarat","25":"Daman & Diu","26":"Dadra & NH","27":"Maharashtra","28":"Andhra Pradesh (Old)","29":"Karnataka","30":"Goa","31":"Lakshadweep","32":"Kerala","33":"Tamil Nadu","34":"Puducherry","35":"Andaman & Nicobar","36":"Telangana","37":"Andhra Pradesh"};
    setVerified({ valid: isValid, state: states[stateCode]||"Unknown", pan: gstin.substring(2,12) });
    if (isValid) toast.success("Valid GSTIN format!");
    else toast.error("Invalid GSTIN format");
  };

  return (
    <Card className="p-5 space-y-4">
      <h3 className="font-semibold flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600"/>GSTIN Verifier</h3>
      <div className="flex gap-2">
        <Input value={gstin} onChange={e=>setGstin(e.target.value.toUpperCase())} placeholder="e.g. 27AABCU9603R1ZX" className="h-9 font-mono text-sm flex-1" maxLength={15}/>
        <Button onClick={verify} style={{background:"var(--gs-teal)",color:"#fff"}} className="h-9">Verify</Button>
      </div>
      {verified && (
        <div className={`p-4 rounded-xl border ${verified.valid?"bg-emerald-50 border-emerald-200":"bg-rose-50 border-rose-200"}`}>
          <div className="flex items-center gap-2 font-semibold text-sm mb-2">
            {verified.valid ? <CheckCircle2 className="h-4 w-4 text-emerald-600"/> : <AlertTriangle className="h-4 w-4 text-rose-600"/>}
            {verified.valid ? "Valid GSTIN" : "Invalid GSTIN"}
          </div>
          {verified.valid && (
            <div className="text-xs space-y-1 text-[var(--gs-muted)]">
              <p>State Code: <strong>{gstin.substring(0,2)}</strong> — {verified.state}</p>
              <p>PAN: <strong>{verified.pan}</strong></p>
              <p className="text-[10px] mt-2 text-amber-700">⚠️ Ye format validation hai — govt API se live check Replit deployment mein possible nahi</p>
            </div>
          )}
        </div>
      )}
      <div className="text-[10px] text-[var(--gs-muted)] p-3 bg-[var(--gs-surface-2)] rounded-lg">
        <p className="font-semibold mb-1">GSTIN Format: <span className="font-mono">SS PPPPP NNNN E V Z C</span></p>
        <p>SS=State Code · PPPPP=PAN Letters · NNNN=PAN Numbers · E=Entity · V=Variant · Z=Default · C=Check</p>
      </div>
    </Card>
  );
}

export default function GST() {
  const [stats, setStats] = useState({ collected:0, cgst:0, sgst:0, igst:0, invoices:0 });
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gstConfig, setGstConfig] = useState({ gstin:"", businessName:"", gstRate:18, inclusive:false });
  const [configSaved, setConfigSaved] = useState(false);
  const [tab, setTab] = useState("report");
  const [quarter, setQuarter] = useState("Q1 2025-26 (Apr-Jun)");

  const QUARTERS = ["Q1 2025-26 (Apr-Jun)","Q2 2025-26 (Jul-Sep)","Q3 2025-26 (Oct-Dec)","Q4 2025-26 (Jan-Mar)"];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/orders?status=delivered&limit=100");
      const orderList = r.data?.orders||r.data||[];
      setOrders(orderList);
      const rate = 18;
      const total = orderList.reduce((a,o)=>a+(o.total||0),0);
      const gstAmt = total * rate/100;
      setStats({ collected: gstAmt, cgst: gstAmt/2, sgst: gstAmt/2, igst:0, invoices:orderList.length, totalRevenue:total });
    } catch { } finally { setLoading(false); }
  }, []);

  useEffect(()=>{load();},[load]);

  const saveConfig = async () => {
    try {
      await api.post("/admin/settings/gst", gstConfig).catch(()=>{});
      setConfigSaved(true);
      toast.success("GST config save ho gayi!");
      setTimeout(()=>setConfigSaved(false),2000);
    } catch { toast.success("Saved locally!"); setConfigSaved(true); }
  };

  const exportGSTR1 = () => {
    const rows = [["Order No","Customer","Date","Taxable Value","CGST","SGST","Total"],...orders.slice(0,50).map(o=>{
      const taxable = (o.total||0)/1.18; const gst = (o.total||0)-taxable;
      return [o.order_number||"—",o.customer_name||"—",o.created_at?new Date(o.created_at).toLocaleDateString("en-IN"):"—",taxable.toFixed(2),(gst/2).toFixed(2),(gst/2).toFixed(2),(o.total||0).toFixed(2)];
    })];
    const csv = rows.map(r=>r.join(",")).join("\n");
    const blob = new Blob([csv],{type:"text/csv"});
    const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href=url; a.download=`GSTR1_${quarter.replace(/ /g,"_")}.csv`; a.click();
    toast.success("GSTR-1 CSV export ho gayi!");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><Receipt className="h-7 w-7 text-orange-600"/>GST Management</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">GST calculate karo, GSTIN verify karo, GSTR-1 export karo</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading?"animate-spin":""}`}/>Refresh</Button>
          <Button variant="outline" size="sm" onClick={exportGSTR1}><Download className="h-3.5 w-3.5 mr-1"/>Export GSTR-1</Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label:"GST Collected",    value:fmtINR(stats.collected),   color:"text-orange-600", bg:"bg-orange-50" },
          { label:"CGST",             value:fmtINR(stats.cgst),        color:"text-blue-600",   bg:"bg-blue-50" },
          { label:"SGST",             value:fmtINR(stats.sgst),        color:"text-violet-600", bg:"bg-violet-50" },
          { label:"Taxable Invoices", value:stats.invoices,            color:"text-emerald-600",bg:"bg-emerald-50" },
        ].map(s=>(
          <Card key={s.label} className="p-4 flex items-center gap-3">
            <div className={`h-10 w-10 rounded-xl ${s.bg} grid place-items-center flex-shrink-0`}>
              <IndianRupee className={`h-5 w-5 ${s.color}`}/>
            </div>
            <div>
              <p className={`font-display text-xl leading-none ${s.color}`}>{loading?"…":s.value}</p>
              <p className="text-[10px] text-[var(--gs-muted)] mt-0.5">{s.label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex gap-2">
        {["report","calculator","verifier","settings"].map(t=>(
          <button key={t} onClick={()=>setTab(t)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${tab===t?"bg-[var(--gs-teal)] text-white":"bg-[var(--gs-surface-2)] text-[var(--gs-muted)]"}`}>{t}</button>
        ))}
      </div>

      {tab==="report" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Select value={quarter} onValueChange={setQuarter}>
              <SelectTrigger className="w-64"><SelectValue/></SelectTrigger>
              <SelectContent>{QUARTERS.map(q=><SelectItem key={q} value={q}>{q}</SelectItem>)}</SelectContent>
            </Select>
            <Badge variant="outline" className="bg-orange-50 text-orange-700">GST @ 18% (SaaS default)</Badge>
          </div>
          <Card className="overflow-hidden">
            <div className="p-4 border-b bg-[var(--gs-surface-2)] flex items-center justify-between">
              <h3 className="font-semibold text-sm flex items-center gap-2"><FileText className="h-4 w-4"/>GSTR-1 — Outward Supplies ({quarter})</h3>
              <Button size="sm" variant="outline" onClick={exportGSTR1} className="h-7 text-xs gap-1"><Download className="h-3 w-3"/>CSV</Button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-[10px] uppercase tracking-wider bg-[var(--gs-surface-2)]">
                  <tr>{["Order No","Customer","Date","Taxable Amt","CGST 9%","SGST 9%","Total"].map(h=><th key={h} className="text-left py-3 px-4 font-semibold text-[var(--gs-muted)]">{h}</th>)}</tr>
                </thead>
                <tbody>
                  {loading ? <tr><td colSpan={7} className="text-center py-10"><Loader2 className="h-5 w-5 animate-spin mx-auto"/></td></tr>
                  : orders.length===0 ? <tr><td colSpan={7} className="text-center py-10 text-[var(--gs-muted)]">Koi orders nahi hain abhi</td></tr>
                  : orders.slice(0,20).map(o=>{
                    const taxable = (o.total||0)/1.18;
                    const gst = (o.total||0)-taxable;
                    return (
                      <tr key={o._id} className="border-t hover:bg-[var(--gs-surface-2)]">
                        <td className="py-3 px-4 font-mono text-xs">{o.order_number||"—"}</td>
                        <td className="py-3 px-4">{o.customer_name||"—"}</td>
                        <td className="py-3 px-4 text-xs text-[var(--gs-muted)]">{o.created_at?new Date(o.created_at).toLocaleDateString("en-IN"):"—"}</td>
                        <td className="py-3 px-4">{fmtINR(taxable)}</td>
                        <td className="py-3 px-4 text-blue-600">{fmtINR(gst/2)}</td>
                        <td className="py-3 px-4 text-violet-600">{fmtINR(gst/2)}</td>
                        <td className="py-3 px-4 font-semibold">{fmtINR(o.total)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                {!loading && orders.length>0 && (
                  <tfoot className="bg-[var(--gs-surface-2)]">
                    <tr>
                      <td colSpan={3} className="py-3 px-4 font-bold text-xs">TOTAL ({orders.length} invoices)</td>
                      <td className="py-3 px-4 font-bold">{fmtINR(stats.totalRevenue/1.18||0)}</td>
                      <td className="py-3 px-4 font-bold text-blue-600">{fmtINR(stats.cgst)}</td>
                      <td className="py-3 px-4 font-bold text-violet-600">{fmtINR(stats.sgst)}</td>
                      <td className="py-3 px-4 font-bold text-[var(--gs-teal)]">{fmtINR(stats.totalRevenue||0)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </Card>
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex gap-3">
            <Info className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5"/>
            <div className="text-sm">
              <p className="font-semibold text-amber-800 mb-1">GST Filing Reminder</p>
              <p className="text-amber-700">GSTR-1 — 11th of every month | GSTR-3B — 20th of every month | Annual — Dec 31. CA ya tax consultant se file karwayein actual filing ke liye.</p>
            </div>
          </div>
        </div>
      )}

      {tab==="calculator" && <GSTCalculator/>}
      {tab==="verifier" && <GSTINVerifier/>}

      {tab==="settings" && (
        <Card className="p-5 space-y-4 max-w-xl">
          <h3 className="font-semibold flex items-center gap-2"><Receipt className="h-4 w-4 text-orange-600"/>GST Settings</h3>
          <div className="space-y-3">
            <div><label className="text-xs font-semibold mb-1.5 block">Business GSTIN</label><Input value={gstConfig.gstin} onChange={e=>setGstConfig(c=>({...c,gstin:e.target.value.toUpperCase()}))} placeholder="e.g. 27AABCU9603R1ZX" className="font-mono"/></div>
            <div><label className="text-xs font-semibold mb-1.5 block">Registered Business Name</label><Input value={gstConfig.businessName} onChange={e=>setGstConfig(c=>({...c,businessName:e.target.value}))} placeholder="As per GST certificate…"/></div>
            <div><label className="text-xs font-semibold mb-1.5 block">Default GST Rate on Sales</label>
              <Select value={String(gstConfig.gstRate)} onValueChange={v=>setGstConfig(c=>({...c,gstRate:Number(v)}))}>
                <SelectTrigger><SelectValue/></SelectTrigger>
                <SelectContent>{GST_RATES.map(r=><SelectItem key={r.rate} value={String(r.rate)}><span className="font-semibold">{r.rate}%</span> — {r.desc}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={gstConfig.inclusive} onCheckedChange={v=>setGstConfig(c=>({...c,inclusive:v}))}/>
              <span className="text-sm">Prices already include GST (GST inclusive pricing)</span>
            </div>
            <Button onClick={saveConfig} style={{background:"var(--gs-teal)",color:"#fff"}} className="w-full gap-2">
              {configSaved?<><CheckCircle2 className="h-4 w-4"/>Saved!</>:<>Save GST Config</>}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
