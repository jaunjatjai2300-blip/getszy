import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Star, RefreshCw, Loader2, CheckCircle2, XCircle, Trash2, MessageSquare } from "lucide-react";
import { toast } from "sonner";

function Stars({ rating }) {
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i=>(
        <Star key={i} className={`h-3.5 w-3.5 ${i<=rating?"fill-amber-400 text-amber-400":"text-gray-300"}`}/>
      ))}
    </div>
  );
}

const STATUS_BADGE = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
};

export default function Reviews() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const load = useCallback(async()=>{
    setLoading(true);
    try { const r=await api.get(`/admin/reviews?status=${statusFilter}`); setItems(r.data.items||[]); }
    catch { toast.error("Load failed"); } finally { setLoading(false); }
  },[statusFilter]);
  useEffect(()=>{ load(); },[load]);

  const moderate = async(id, status)=>{
    try { await api.put(`/admin/reviews/${id}`,{status}); await load(); toast.success(status==="approved"?"Approved!":"Rejected"); } catch { toast.error("Error"); }
  };

  const del = async(id)=>{
    if (!window.confirm("Delete this review?")) return;
    try { await api.delete(`/admin/reviews/${id}`); await load(); toast.success("Deleted"); } catch { toast.error("Error"); }
  };

  const filtered = items.filter(i=>!search||(i.comment||"").toLowerCase().includes(search.toLowerCase())||(i.user_name||"").toLowerCase().includes(search.toLowerCase()));

  const avgRating = filtered.length ? (filtered.reduce((s,r)=>s+r.rating,0)/filtered.length).toFixed(1) : 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl flex items-center gap-2"><MessageSquare className="h-7 w-7 text-[var(--gs-teal)]"/>Reviews</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-1">{items.filter(i=>i.status==="pending").length} pending moderation · Avg ⭐ {avgRating}</p>
        </div>
        <div className="flex gap-2">
          <Input className="h-9 w-44 text-xs" placeholder="Search…" value={search} onChange={e=>setSearch(e.target.value)}/>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-9 text-xs w-32"><SelectValue/></SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="text-xs">All</SelectItem>
              <SelectItem value="pending" className="text-xs">Pending</SelectItem>
              <SelectItem value="approved" className="text-xs">Approved</SelectItem>
              <SelectItem value="rejected" className="text-xs">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className={`h-3.5 w-3.5 ${loading?"animate-spin":""}`}/></Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        {[["Total",items.length,"📊"],["Pending",items.filter(i=>i.status==="pending").length,"⏳"],["Approved",items.filter(i=>i.status==="approved").length,"✅"],["Avg Rating",avgRating,"⭐"]].map(([k,v,ic])=>(
          <Card key={k} className="p-3"><p className="text-[10px] text-[var(--gs-muted)]">{ic} {k}</p><p className="text-xl font-bold mt-0.5">{v}</p></Card>
        ))}
      </div>

      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[var(--gs-muted)]"/></div> : (
        <div className="space-y-3">
          {filtered.length===0 ? (
            <Card className="p-12 text-center"><MessageSquare className="h-10 w-10 mx-auto mb-3 text-[var(--gs-muted)]"/><p className="text-sm text-[var(--gs-muted)]">Koi reviews nahi</p></Card>
          ) : filtered.map(r=>(
            <Card key={r.id} className="p-4">
              <div className="flex items-start gap-4">
                <div className="h-9 w-9 rounded-full bg-[var(--gs-teal-soft)] grid place-items-center text-sm font-bold text-[var(--gs-teal)] flex-shrink-0">
                  {(r.user_name||"U")[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-semibold text-sm">{r.user_name||"Anonymous"}</span>
                    <Stars rating={r.rating}/>
                    <Badge className={`text-[10px] ${STATUS_BADGE[r.status]||""}`}>{r.status}</Badge>
                    <span className="text-[10px] text-[var(--gs-muted)] ml-auto">{r.created_at?new Date(r.created_at).toLocaleDateString("en-IN"):""}</span>
                  </div>
                  {r.title&&<p className="text-sm font-medium mt-1">{r.title}</p>}
                  <p className="text-sm text-[var(--gs-muted)] mt-1">{r.comment||"No comment"}</p>
                  <p className="text-[10px] text-[var(--gs-muted)] mt-1">Product ID: <code className="font-mono">{r.product_id}</code></p>
                </div>
                <div className="flex gap-1.5 flex-shrink-0">
                  {r.status!=="approved"&&(
                    <Button size="sm" variant="outline" className="h-7 px-2 text-emerald-600 border-emerald-200 hover:bg-emerald-50" onClick={()=>moderate(r.id,"approved")}>
                      <CheckCircle2 className="h-3.5 w-3.5"/>
                    </Button>
                  )}
                  {r.status!=="rejected"&&(
                    <Button size="sm" variant="outline" className="h-7 px-2 text-rose-500 border-rose-200 hover:bg-rose-50" onClick={()=>moderate(r.id,"rejected")}>
                      <XCircle className="h-3.5 w-3.5"/>
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500" onClick={()=>del(r.id)}>
                    <Trash2 className="h-3.5 w-3.5"/>
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
