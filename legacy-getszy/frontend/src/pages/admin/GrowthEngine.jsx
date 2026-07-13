import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Search, TrendingUp, Mail, Filter, Users, BarChart3, Target,
  Award, Share2, Link2, Megaphone, Plus, RefreshCw, Eye, Play,
  Pause, CheckCircle2, XCircle, ArrowUpRight, ArrowDownRight,
  Trophy, Send, UserPlus, BarChart2, Globe, Gauge, Sparkles
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function ScoreGauge({ value, label }) {
  const pct = Math.min(value || 0, 100);
  const color = pct >= 80 ? "#10B981" : pct >= 50 ? "#F59E0B" : "#EF4444";
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="70" height="70" viewBox="0 0 70 70">
        <circle cx="35" cy="35" r="28" fill="none" stroke="#E7D9CE" strokeWidth="5"/>
        <circle cx="35" cy="35" r="28" fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={2 * Math.PI * 28} strokeDashoffset={2 * Math.PI * 28 - (pct / 100) * 2 * Math.PI * 28}
          strokeLinecap="round" transform="rotate(-90 35 35)" className="transition-all duration-700"/>
        <text x="35" y="35" textAnchor="middle" dominantBaseline="central" className="text-sm font-bold fill-[var(--gs-ink)]">{pct}</text>
      </svg>
      <span className="text-[10px] text-[var(--gs-muted)]">{label}</span>
    </div>
  );
}

export default function GrowthEngine() {
  const [tab, setTab] = useState("seo");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // SEO
  const [seoUrl, setSeoUrl] = useState("");
  const [seoResults, setSeoResults] = useState(null);
  const [seoAnalyzing, setSeoAnalyzing] = useState(false);

  // Email
  const [campaigns, setCampaigns] = useState([]);
  const [showCampaignForm, setShowCampaignForm] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ subject: "", body: "", audience: "all" });

  // Funnels
  const [funnels, setFunnels] = useState([]);

  // AB Tests
  const [abTests, setAbTests] = useState([]);

  // Referrals
  const [referralStats, setReferralStats] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);

  const load = async () => {
    setError(false);
    try {
      const [c, f, ab, r, lb] = await Promise.all([
        api.get("/admin/growth/email-campaigns").catch(() => ({ data: { items: [] } })),
        api.get("/admin/growth/funnels").catch(() => ({ data: { items: [] } })),
        api.get("/admin/growth/ab-tests").catch(() => ({ data: { items: [] } })),
        api.get("/admin/growth/referral-stats").catch(() => ({ data: null })),
        api.get("/admin/growth/referral-leaderboard").catch(() => ({ data: { items: [] } })),
      ]);
      setCampaigns(c.data?.items || []);
      setFunnels(f.data?.items || []);
      setAbTests(ab.data?.items || []);
      setReferralStats(r.data);
      setLeaderboard(lb.data?.items || []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const analyzeSeo = async () => {
    if (!seoUrl.trim()) return;
    setSeoAnalyzing(true);
    try {
      const r = await api.post("/admin/growth/seo-analyze", { url: seoUrl });
      setSeoResults(r.data);
    } catch { /* silent */ }
    setSeoAnalyzing(false);
  };

  const createCampaign = async () => {
    if (!newCampaign.subject.trim()) return;
    try {
      const r = await api.post("/admin/growth/email-campaigns", newCampaign);
      setCampaigns(prev => [...prev, r.data?.item].filter(Boolean));
      setNewCampaign({ subject: "", body: "", audience: "all" });
      setShowCampaignForm(false);
    } catch { /* silent */ }
  };

  if (error) return (
    <div className="p-6 text-center text-[var(--gs-muted)]">
      Data load nahi ho saki. <button onClick={load} className="underline">Retry</button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Growth Engine</h1>
          <p className="text-sm text-[var(--gs-muted)] mt-0.5">SEO, email campaigns, funnels, A/B tests & referrals</p>
        </div>
        <Button variant="outline" size="sm" className="h-8" onClick={load}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}/>
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="seo"><Search className="h-3 w-3 mr-1 inline"/>SEO</TabsTrigger>
          <TabsTrigger value="email"><Mail className="h-3 w-3 mr-1 inline"/>Email</TabsTrigger>
          <TabsTrigger value="funnels"><Filter className="h-3 w-3 mr-1 inline"/>Funnels</TabsTrigger>
          <TabsTrigger value="abtests"><BarChart3 className="h-3 w-3 mr-1 inline"/>A/B Tests</TabsTrigger>
          <TabsTrigger value="referrals"><Share2 className="h-3 w-3 mr-1 inline"/>Referrals</TabsTrigger>
        </TabsList>

        {/* SEO */}
        <TabsContent value="seo" className="mt-4 space-y-4">
          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Search className="h-4 w-4 text-[var(--gs-teal)]"/>SEO Analyzer
            </h3>
            <div className="flex items-center gap-2">
              <Input placeholder="https://example.com" value={seoUrl} onChange={e => setSeoUrl(e.target.value)} className="flex-1 text-xs"/>
              <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={analyzeSeo} disabled={seoAnalyzing}>
                {seoAnalyzing ? "Analyzing…" : "Analyze"}
              </Button>
            </div>
          </Card>

          {seoResults && (
            <div className="grid md:grid-cols-2 gap-4">
              <Card className="p-5">
                <h3 className="font-semibold text-sm mb-4">SEO Score</h3>
                <div className="flex items-center justify-center gap-6">
                  <ScoreGauge value={seoResults.score} label="Overall"/>
                  <ScoreGauge value={seoResults.performance} label="Performance"/>
                  <ScoreGauge value={seoResults.seo} label="SEO"/>
                </div>
              </Card>
              <Card className="p-5">
                <h3 className="font-semibold text-sm mb-3">Meta Generator</h3>
                <div className="space-y-2">
                  <Input className="text-xs" placeholder="Title" defaultValue={seoResults.title || ""}/>
                  <Textarea className="text-xs" placeholder="Meta description" defaultValue={seoResults.description || ""} rows={3}/>
                  <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]">Save Meta Tags</Button>
                </div>
              </Card>
              {seoResults.issues && (
                <Card className="p-5 md:col-span-2">
                  <h3 className="font-semibold text-sm mb-3">Issues Found</h3>
                  <div className="space-y-2">
                    {seoResults.issues.map((issue, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-[var(--gs-surface-2)]">
                        {issue.severity === "error" ? <XCircle className="h-3.5 w-3.5 text-rose-500"/> :
                         <AlertTriangle className="h-3.5 w-3.5 text-amber-500"/>}
                        <span className="text-xs flex-1">{issue.message}</span>
                        <Badge variant="outline" className="text-[9px]">{issue.severity}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </TabsContent>

        {/* Email Campaigns */}
        <TabsContent value="email" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">Email Campaigns ({campaigns.length})</h3>
            <Button size="sm" className="h-8 bg-[var(--gs-teal)]" onClick={() => setShowCampaignForm(!showCampaignForm)}>
              <Plus className="h-3.5 w-3.5 mr-1"/>Create
            </Button>
          </div>

          {showCampaignForm && (
            <Card className="p-5 space-y-3">
              <Input placeholder="Subject" value={newCampaign.subject} onChange={e => setNewCampaign(p => ({ ...p, subject: e.target.value }))} className="text-xs"/>
              <Textarea placeholder="Body (HTML supported)" value={newCampaign.body} onChange={e => setNewCampaign(p => ({ ...p, body: e.target.value }))} className="text-xs" rows={4}/>
              <Select value={newCampaign.audience} onValueChange={v => setNewCampaign(p => ({ ...p, audience: v }))}>
                <SelectTrigger className="w-40 h-8 text-xs"><SelectValue/></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem>
                  <SelectItem value="subscribers">Subscribers</SelectItem>
                  <SelectItem value="free">Free Users</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex gap-2">
                <Button size="sm" className="h-7 text-[10px] bg-[var(--gs-teal)]" onClick={createCampaign}>Send Campaign</Button>
                <Button size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setShowCampaignForm(false)}>Cancel</Button>
              </div>
            </Card>
          )}

          {campaigns.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Mail className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi campaigns nahi
            </div>
          ) : (
            <div className="space-y-2">
              {campaigns.map((c, i) => (
                <Card key={c.id || i} className="p-4">
                  <div className="flex items-center gap-3">
                    <Mail className="h-4 w-4 text-[var(--gs-teal)]"/>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold">{c.subject}</div>
                      <div className="text-[11px] text-[var(--gs-muted)]">{c.audience} · {c.sent_at || c.created_at}</div>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="flex items-center gap-1 text-[var(--gs-muted)]"><Send className="h-3 w-3"/>{c.sent || 0}</span>
                      <span className="flex items-center gap-1 text-[var(--gs-muted)]"><Eye className="h-3 w-3"/>{c.opened || 0}</span>
                      <Badge variant="outline" className={`text-[10px] ${c.status === "sent" ? "text-emerald-600" : c.status === "draft" ? "text-[var(--gs-muted)]" : "text-amber-600"}`}>
                        {c.status}
                      </Badge>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Funnels */}
        <TabsContent value="funnels" className="mt-4 space-y-4">
          {funnels.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <Filter className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi funnels nahi
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {funnels.map((f, i) => (
                <Card key={f.id || i} className="p-5">
                  <h3 className="font-semibold text-sm mb-4">{f.name}</h3>
                  {f.steps && (
                    <div className="space-y-3">
                      {f.steps.map((s, si) => {
                        const dropoff = si > 0 && f.steps[si - 1].count > 0
                          ? ((1 - s.count / f.steps[si - 1].count) * 100).toFixed(1)
                          : 0;
                        return (
                          <div key={si}>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-[var(--gs-muted)]">{s.label}</span>
                              <span className="font-semibold">{s.count} ({s.count > 0 ? ((s.count / (f.steps[0]?.count || 1)) * 100).toFixed(1) : 0}%)</span>
                            </div>
                            <div className="h-6 rounded bg-[var(--gs-surface-2)] overflow-hidden">
                              <div className="h-full rounded bg-[var(--gs-teal)] transition-all" style={{ width: `${Math.min((s.count / (f.steps[0]?.count || 1)) * 100, 100)}%` }}/>
                            </div>
                            {si > 0 && parseFloat(dropoff) > 0 && (
                              <div className="text-[10px] text-rose-500 mt-0.5 flex items-center gap-1">
                                <ArrowDownRight className="h-2.5 w-2.5"/>{dropoff}% dropoff
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* A/B Tests */}
        <TabsContent value="abtests" className="mt-4 space-y-4">
          {abTests.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)] text-sm">
              <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-30"/>Koi A/B tests nahi
            </div>
          ) : (
            <div className="space-y-3">
              {abTests.map((t, i) => (
                <Card key={t.id || i} className="p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-sm">{t.name}</h3>
                    <Badge variant="outline" className={`text-[10px] ${
                      t.status === "running" ? "text-blue-600" :
                      t.status === "completed" ? "text-emerald-600" : "text-[var(--gs-muted)]"
                    }`}>{t.status}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {t.variants?.map((v, vi) => (
                      <div key={vi} className="p-3 rounded-lg bg-[var(--gs-surface-2)]">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold">{v.name}</span>
                          {t.winner === vi && <Trophy className="h-3.5 w-3.5 text-amber-500"/>}
                        </div>
                        <div className="text-lg font-display">{v.conversion_rate}%</div>
                        <div className="text-[10px] text-[var(--gs-muted)]">{v.visits} visits · {v.conversions} conversions</div>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Referrals */}
        <TabsContent value="referrals" className="mt-4 space-y-4">
          {referralStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Total Referrals", value: referralStats.total_referrals, icon: UserPlus },
                { label: "Active Referrers", value: referralStats.active_referrers, icon: Users },
                { label: "Conversion Rate", value: `${referralStats.conversion_rate || 0}%`, icon: Target },
                { label: "Rewards Given", value: referralStats.rewards_given, icon: Award },
              ].map(s => (
                <Card key={s.label} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--gs-muted)] font-semibold">{s.label}</span>
                    <s.icon className="h-4 w-4 text-[var(--gs-teal)]"/>
                  </div>
                  <div className="text-xl font-display">{s.value ?? "—"}</div>
                </Card>
              ))}
            </div>
          )}

          <Card className="p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500"/>Referral Leaderboard
            </h3>
            {leaderboard.length === 0 ? (
              <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Koi referrals nahi abhi</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Rank</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Referrals</TableHead>
                      <TableHead>Conversions</TableHead>
                      <TableHead>Reward</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leaderboard.map((l, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <span className={`text-sm font-bold ${i === 0 ? "text-amber-500" : i === 1 ? "text-slate-400" : i === 2 ? "text-amber-700" : "text-[var(--gs-muted)]"}`}>
                            #{i + 1}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs font-semibold">{l.user_name || l.email}</TableCell>
                        <TableCell className="text-xs">{l.referrals}</TableCell>
                        <TableCell className="text-xs">{l.conversions}</TableCell>
                        <TableCell className="text-xs font-semibold text-emerald-600">{l.reward}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
