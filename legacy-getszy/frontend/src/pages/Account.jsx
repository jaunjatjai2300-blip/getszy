import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, fmtINR } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Package, GraduationCap, Coins, Gift, ArrowRight, Crown,
  Sparkles, ShoppingBag, BookOpen, Copy, Check, ExternalLink,
  Award, MessageSquare, Pencil, Save, Lock, Loader2,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const STATUS_COLORS = {
  pending: "bg-amber-100 text-amber-800", forwarded: "bg-sky-100 text-sky-800",
  shipped: "bg-blue-100 text-blue-800", delivered: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-rose-100 text-rose-800",
};

const escapeHtml = (value) => String(value ?? "")
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

async function openCertificate(courseSlug) {
  const popup = window.open("", "_blank");
  if (!popup) {
    toast.error("Please allow pop-ups to view your certificate");
    return;
  }
  popup.document.title = "Getszy Certificate";
  popup.document.body.innerHTML = "<p style=\"font-family:system-ui;padding:2rem\">Loading certificate…</p>";
  try {
    const response = await api.get(`/me/courses/${encodeURIComponent(courseSlug)}/certificate`);
    const certificate = response.data;
    const html = `<!doctype html><html><head><meta charset=\"utf-8\"><title>Getszy Certificate</title><style>body{margin:0;background:#f7f5f2;color:#183c3c;font-family:Georgia,serif;display:grid;place-items:center;min-height:100vh}.certificate{box-sizing:border-box;width:min(900px,calc(100% - 32px));padding:72px 64px;border:12px solid #1e8e8e;background:#fff;text-align:center}.brand{font:700 18px system-ui;letter-spacing:.18em;text-transform:uppercase;color:#1e8e8e}.label{margin-top:42px;font:600 13px system-ui;letter-spacing:.14em;text-transform:uppercase;color:#6b7280}.name{margin:18px 0 8px;font-size:46px;color:#183c3c}.course{font-size:25px;color:#1e8e8e}.meta{margin-top:44px;font:14px system-ui;color:#4b5563}.print{margin-top:30px;padding:10px 18px;border:0;border-radius:8px;background:#1e8e8e;color:#fff;cursor:pointer}@media print{body{background:#fff}.certificate{width:100%;border-width:8px}.print{display:none}}</style></head><body><main class=\"certificate\"><div class=\"brand\">getszy</div><div class=\"label\">Certificate of completion</div><div class=\"name\">${escapeHtml(certificate.student_name)}</div><div>has successfully completed</div><div class=\"course\">${escapeHtml(certificate.course_title)}</div><div class=\"meta\">${escapeHtml(certificate.course_level)} · Issued ${escapeHtml(certificate.completed_at ? new Date(certificate.completed_at).toLocaleDateString("en-IN") : "") } · ID ${escapeHtml(certificate.certificate_id)}</div><div class=\"meta\">Instructor: ${escapeHtml(certificate.instructor)}</div><button class=\"print\" onclick=\"window.print()\">Print / Save PDF</button></main></body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    popup.location.href = url;
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    popup.close();
    toast.error(error?.response?.data?.detail || "Certificate unavailable — please retry");
  }
}

export default function Account() {
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [sub, setSub] = useState(null);
  const [refs, setRefs] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [busy, setBusy] = useState(true);
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pwBusy, setPwBusy] = useState(false);
  const [nameField, setNameField] = useState("");
  const [phoneField, setPhoneField] = useState("");
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });

  useEffect(() => {
    if (!loading && !user) navigate("/login");
    if (user) {
      setNameField(user.name || "");
      setPhoneField(user.phone || "");
      Promise.allSettled([
        api.get("/orders/mine"),
        api.get("/me/enrollments"),
        api.get("/me/subscription"),
        api.get("/auth/referrals"),
        api.get("/agents/sessions"),
      ]).then(([o, e, s, r, a]) => {
        if (o.status === "fulfilled") setOrders(o.value.data || []);
        if (e.status === "fulfilled") setEnrollments(e.value.data || []);
        if (s.status === "fulfilled") setSub(s.value.data);
        if (r.status === "fulfilled") setRefs(r.value.data);
        if (a.status === "fulfilled") setSessions(a.value.data?.sessions || []);
        setBusy(false);
      });
    }
  }, [user, loading, navigate]);

  const certificates = enrollments.filter((e) => (e.progress || 0) >= 1);

  const saveProfile = async () => {
    setSaving(true);
    try {
      await api.put("/auth/me", { name: nameField, phone: phoneField });
      await refresh();
      toast.success("Profile updated");
    } catch {
      toast.error("Could not update profile");
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async () => {
    if (pw.next !== pw.confirm) { toast.error("New passwords don't match"); return; }
    setPwBusy(true);
    try {
      await api.post("/auth/me/password", { current_password: pw.current, new_password: pw.next });
      toast.success("Password changed");
      setPw({ current: "", next: "", confirm: "" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not change password");
    } finally {
      setPwBusy(false);
    }
  };

  const cancelSub = async () => {
    if (!window.confirm("Cancel subscription? You'll keep access until period end.")) return;
    await api.post("/me/subscription/cancel");
    const { data } = await api.get("/me/subscription"); setSub(data);
    toast.success("Subscription cancelled");
  };

  const copyRef = async () => {
    if (!refs?.referral_link) return;
    try { await navigator.clipboard.writeText(refs.referral_link); setCopied(true); setTimeout(() => setCopied(false), 1800); }
    catch { setCopied(false); }
  };

  if (!user) return null;

  const credits = user.credits ?? 0;
  const coursesInProgress = enrollments.filter((e) => (e.progress || 0) < 1).length;
  const stats = [
    { label: "Orders", value: orders.length, icon: Package, color: "#0ea5e9" },
    { label: "Courses", value: coursesInProgress, icon: GraduationCap, color: "#7c3aed" },
    { label: "Credits", value: credits, icon: Coins, color: "#f59e0b" },
    { label: "Referral earned", value: refs?.rewards_earned ?? 0, icon: Gift, color: "#16a34a" },
  ];

  return (
    <div className="gs-container gs-section" data-testid="account-page">
      {/* Hero */}
      <div className="rounded-2xl p-6 mb-6" style={{ background: "linear-gradient(135deg, var(--gs-teal-soft), white)", border: "1px solid var(--gs-border)" }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="text-sm text-[var(--gs-muted)]">Welcome back</div>
            <h1 className="font-display text-3xl">{user.name.split(" ")[0] || "there"} 👋</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-white" style={{ color: "var(--gs-teal)" }}>
              <Coins className="h-3.5 w-3.5" /> {credits} credits
            </span>
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-white capitalize" style={{ color: "var(--gs-ink)" }}>
              <Crown className="h-3.5 w-3.5 text-[var(--gs-teal)]" /> {(sub?.plan) || "free"}
            </span>
          </div>
        </div>
      </div>

      {busy ? (
        <div className="py-20 text-center text-[var(--gs-muted)]">Loading your dashboard…</div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {stats.map((s) => (
              <div key={s.label} className="gs-card p-5 flex items-center gap-3">
                <span className="h-10 w-10 rounded-xl flex items-center justify-center text-white" style={{ background: s.color }}>
                  <s.icon className="h-5 w-5" />
                </span>
                <div>
                  <div className="text-2xl font-display leading-none">{s.value}</div>
                  <div className="text-xs text-[var(--gs-muted)] mt-1">{s.label}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
            {/* Left: orders + learning */}
            <div className="space-y-6">
              <section className="gs-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-display text-lg flex items-center gap-2"><Package className="h-4 w-4 text-[var(--gs-teal)]" /> Recent Orders</h2>
                  <Link to="/shop" className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline">Shop more <ArrowRight className="h-3 w-3" /></Link>
                </div>
                {orders.length === 0 ? (
                  <div className="text-center py-8 text-[var(--gs-muted)] text-sm">No orders yet — your first order is just a click away.</div>
                ) : (
                  <div className="space-y-3">
                    {orders.slice(0, 5).map((o) => (
                      <div key={o.id} className="flex flex-wrap items-center gap-3 p-3 rounded-xl" style={{ background: "var(--gs-bg, #f8fafc)" }}>
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-sm">{o.order_number}</div>
                          <div className="text-xs text-[var(--gs-muted)]">{new Date(o.created_at).toLocaleDateString()} · {o.items?.length || 0} item(s)</div>
                          {o.tracking_number && <div className="text-xs mt-0.5">Tracking: <span className="font-mono">{o.tracking_number}</span></div>}
                        </div>
                        <Badge className={`${STATUS_COLORS[o.status] || ""} hover:opacity-100 capitalize`}>{o.status}</Badge>
                        <div className="font-semibold text-sm">{fmtINR(o.total)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="gs-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-display text-lg flex items-center gap-2"><GraduationCap className="h-4 w-4 text-[var(--gs-teal)]" /> Continue Learning</h2>
                  <Link to="/academy" className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline">Browse <ArrowRight className="h-3 w-3" /></Link>
                </div>
                {enrollments.length === 0 ? (
                  <div className="text-center py-8 text-[var(--gs-muted)] text-sm">No courses yet — start learning AI for free.</div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-3">
                    {enrollments.slice(0, 4).map((e) => (
                      <Link key={e.id} to={`/academy/${e.course_slug}/learn`} className="gs-card gs-card-hover overflow-hidden">
                        {e.course?.thumbnail && <img src={e.course.thumbnail} alt="" className="w-full h-28 object-cover" />}
                        <div className="p-3">
                          <div className="font-semibold text-sm mb-1 truncate">{e.course?.title || e.course_slug}</div>
                          <Progress value={(e.progress || 0) * 100} className="h-1.5 mb-1" />
                          <div className="text-xs text-[var(--gs-muted)]">{Math.round((e.progress || 0) * 100)}% complete</div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </section>

              <section className="gs-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-display text-lg flex items-center gap-2"><Award className="h-4 w-4 text-[var(--gs-teal)]" /> Certificates</h2>
                  <Link to="/academy" className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline">Academy <ArrowRight className="h-3 w-3" /></Link>
                </div>
                {certificates.length === 0 ? (
                  <div className="text-center py-8 text-[var(--gs-muted)] text-sm">Complete a course to earn your first certificate.</div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-3">
                    {certificates.slice(0, 4).map((e) => (
                      <button key={e.id} type="button" onClick={() => openCertificate(e.course_slug)} className="w-full text-left gs-card gs-card-hover p-3 flex items-center gap-3">
                        <span className="h-9 w-9 rounded-lg bg-emerald-100 text-emerald-700 grid place-items-center"><Award className="h-4 w-4" /></span>
                        <div className="min-w-0">
                          <div className="font-semibold text-sm truncate">{e.course?.title || e.course_slug}</div>
                          <div className="text-xs text-[var(--gs-muted)]">100% complete · View certificate</div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </section>

              <section className="gs-card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-display text-lg flex items-center gap-2"><MessageSquare className="h-4 w-4 text-[var(--gs-teal)]" /> Recent AI Chats</h2>
                  <Link to="/ai-agents" className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline">All agents <ArrowRight className="h-3 w-3" /></Link>
                </div>
                {sessions.length === 0 ? (
                  <div className="text-center py-8 text-[var(--gs-muted)] text-sm">No AI chats yet — try Neo or an AI agent.</div>
                ) : (
                  <div className="space-y-2">
                    {sessions.slice(0, 5).map((s) => (
                      <Link key={s.session_id} to="/ai-agents" className="flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--gs-bg,#f8fafc)]" style={{ border: "1px solid var(--gs-border)" }}>
                        <span className="h-9 w-9 rounded-lg bg-[var(--gs-teal-bg,#e6fffb)] grid place-items-center text-lg shrink-0">{s.agent_avatar || "🤖"}</span>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium truncate">{s.agent_name || "AI Agent"}</div>
                          <div className="text-xs text-[var(--gs-muted)] truncate">{s.last_message || "Continue conversation"}</div>
                        </div>
                        <span className="text-xs text-[var(--gs-muted)] shrink-0">{s.created_at ? new Date(s.created_at).toLocaleDateString() : ""}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </section>

            </div>

            {/* Right: referral + plan + quick links */}
            <div className="space-y-6">
              <section className="gs-card p-5">
                <div className="flex items-center gap-2 mb-2"><Gift className="h-4 w-4 text-[var(--gs-teal)]" /><h2 className="font-display text-lg">Refer & Earn</h2></div>
                <p className="text-xs text-[var(--gs-muted)] mb-3">You've earned <b className="text-[var(--gs-ink)]">{refs?.rewards_earned ?? 0}</b> credits from <b className="text-[var(--gs-ink)]">{refs?.total_referred ?? 0}</b> friends.</p>
                <div className="flex gap-2 mb-3">
                  <input readOnly value={refs?.referral_link || ""} className="flex-1 px-2 py-1.5 rounded-lg border text-xs bg-[var(--gs-surface)] truncate" style={{ borderColor: "var(--gs-border)" }} />
                  <button onClick={copyRef} className="px-2.5 py-1.5 rounded-lg bg-[var(--gs-teal)] text-white text-xs flex items-center gap-1">
                    {copied ? <><Check className="h-3.5 w-3.5" /> Copied</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
                  </button>
                </div>
                <Link to="/referrals" className="text-xs text-[var(--gs-teal)] flex items-center gap-1 hover:underline">Manage referrals <ExternalLink className="h-3 w-3" /></Link>
              </section>

              <section className="gs-card p-5">
                <div className="flex items-center gap-2 mb-2"><Crown className="h-4 w-4 text-[var(--gs-teal)]" /><h2 className="font-display text-lg">Your Plan</h2></div>
                {sub ? (
                  <>
                    <div className="text-sm mb-1">Plan: <span className="font-semibold capitalize">{sub.plan}</span> · <span className="capitalize text-[var(--gs-muted)]">{sub.status}</span></div>
                    {sub.current_period_end && <div className="text-xs text-[var(--gs-muted)] mb-3">Renews: {new Date(sub.current_period_end).toLocaleDateString()}</div>}
                    <div className="flex gap-2">
                      {sub.plan === "free" ? (
                        <Link to="/pricing"><Button className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90 text-sm">Upgrade <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
                      ) : (
                        <Button variant="outline" onClick={cancelSub} className="text-rose-600 text-sm">Cancel plan</Button>
                      )}
                    </div>
                  </>
                ) : <div className="text-sm text-[var(--gs-muted)]">Free plan</div>}
              </section>

              <section className="gs-card p-5">
                <div className="flex items-center gap-2 mb-3"><Sparkles className="h-4 w-4 text-[var(--gs-teal)]" /><h2 className="font-display text-lg">Quick Actions</h2></div>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => navigate("/shop")} className="flex items-center gap-2 p-3 rounded-xl text-sm hover:bg-[var(--gs-bg,#f8fafc)]" style={{ border: "1px solid var(--gs-border)" }}><ShoppingBag className="h-4 w-4 text-[var(--gs-teal)]" /> Shop</button>
                  <button onClick={() => navigate("/ai-agents")} className="flex items-center gap-2 p-3 rounded-xl text-sm hover:bg-[var(--gs-bg,#f8fafc)]" style={{ border: "1px solid var(--gs-border)" }}><Sparkles className="h-4 w-4 text-[var(--gs-teal)]" /> AI Agents</button>
                  <button onClick={() => navigate("/academy")} className="flex items-center gap-2 p-3 rounded-xl text-sm hover:bg-[var(--gs-bg,#f8fafc)]" style={{ border: "1px solid var(--gs-border)" }}><BookOpen className="h-4 w-4 text-[var(--gs-teal)]" /> Academy</button>
                  <button onClick={() => navigate("/support")} className="flex items-center gap-2 p-3 rounded-xl text-sm hover:bg-[var(--gs-bg,#f8fafc)]" style={{ border: "1px solid var(--gs-border)" }}><Package className="h-4 w-4 text-[var(--gs-teal)]" /> Support</button>
                </div>
              </section>
            </div>
          </div>

          {/* Profile (kept accessible) */}
          <Tabs defaultValue="profile" className="mt-6">
            <TabsList>
              <TabsTrigger value="profile">Profile</TabsTrigger>
            </TabsList>
            <TabsContent value="profile" className="mt-4">
              <div className="grid md:grid-cols-2 gap-6">
                <div className="gs-card p-6">
                  <div className="flex items-center gap-2 mb-4"><Pencil className="h-4 w-4 text-[var(--gs-teal)]" /><h3 className="font-display text-lg">Profile details</h3></div>
                  <label className="block text-sm text-[var(--gs-muted)] mb-1">Name</label>
                  <input value={nameField} onChange={(e) => setNameField(e.target.value)} className="w-full px-3 py-2 rounded-lg border text-sm mb-4" style={{ borderColor: "var(--gs-border)" }} />
                  <label className="block text-sm text-[var(--gs-muted)] mb-1">Phone</label>
                  <input value={phoneField} onChange={(e) => setPhoneField(e.target.value)} placeholder="Optional" className="w-full px-3 py-2 rounded-lg border text-sm mb-4" style={{ borderColor: "var(--gs-border)" }} />
                  <div className="text-sm text-[var(--gs-muted)] mb-1">Email</div>
                  <div className="font-semibold mb-4">{user.email}</div>
                  <Button onClick={saveProfile} disabled={saving} className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">
                    {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />} Save changes
                  </Button>
                </div>

                <div className="gs-card p-6">
                  <div className="flex items-center gap-2 mb-4"><Lock className="h-4 w-4 text-[var(--gs-teal)]" /><h3 className="font-display text-lg">Change password</h3></div>
                  <label className="block text-sm text-[var(--gs-muted)] mb-1">Current password</label>
                  <input type="password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} className="w-full px-3 py-2 rounded-lg border text-sm mb-3" style={{ borderColor: "var(--gs-border)" }} />
                  <label className="block text-sm text-[var(--gs-muted)] mb-1">New password</label>
                  <input type="password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} className="w-full px-3 py-2 rounded-lg border text-sm mb-3" style={{ borderColor: "var(--gs-border)" }} />
                  <label className="block text-sm text-[var(--gs-muted)] mb-1">Confirm new password</label>
                  <input type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} className="w-full px-3 py-2 rounded-lg border text-sm mb-4" style={{ borderColor: "var(--gs-border)" }} />
                  <Button onClick={changePassword} disabled={pwBusy} variant="outline" className="text-[var(--gs-teal)]">
                    {pwBusy ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Lock className="h-4 w-4 mr-1" />} Update password
                  </Button>
                  <p className="text-xs text-[var(--gs-muted)] mt-3">Password must be 8+ chars with uppercase, lowercase & a number.</p>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
