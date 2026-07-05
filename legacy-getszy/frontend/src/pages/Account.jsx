import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, fmtINR } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Package, GraduationCap, ArrowRight, Crown } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const STATUS_COLORS = { pending: "bg-amber-100 text-amber-800", forwarded: "bg-sky-100 text-sky-800", shipped: "bg-blue-100 text-blue-800", delivered: "bg-emerald-100 text-emerald-800", cancelled: "bg-rose-100 text-rose-800" };

export default function Account() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [sub, setSub] = useState(null);

  useEffect(() => {
    if (!loading && !user) navigate("/login");
    if (user) {
      api.get("/orders/mine").then(({ data }) => setOrders(data));
      api.get("/me/enrollments").then(({ data }) => setEnrollments(data));
      api.get("/me/subscription").then(({ data }) => setSub(data));
    }
  }, [user, loading, navigate]);

  const cancelSub = async () => {
    if (!window.confirm("Cancel subscription? You'll keep access until period end.")) return;
    await api.post("/me/subscription/cancel");
    const { data } = await api.get("/me/subscription"); setSub(data);
    toast.success("Subscription cancelled");
  };

  if (!user) return null;

  return (
    <div className="gs-container gs-section" data-testid="account-page">
      <h1 className="font-display text-3xl mb-6">My Account</h1>
      <Tabs defaultValue="orders">
        <TabsList>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="learning" data-testid="account-learning-tab">Learning</TabsTrigger>
          <TabsTrigger value="subscription" data-testid="account-subscription-tab">Subscription</TabsTrigger>
          <TabsTrigger value="profile">Profile</TabsTrigger>
        </TabsList>
        <TabsContent value="orders" className="mt-6">
          {orders.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)]"><Package className="h-10 w-10 mx-auto mb-2"/>No orders yet</div>
          ) : (
            <div className="space-y-3">{orders.map((o) => (
              <div key={o.id} className="gs-card p-5 flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-0"><div className="font-semibold">{o.order_number}</div><div className="text-xs text-[var(--gs-muted)]">{new Date(o.created_at).toLocaleDateString()} · {o.items.length} item(s)</div>{o.tracking_number && <div className="text-xs mt-1">Tracking: <span className="font-mono">{o.tracking_number}</span></div>}</div>
                <Badge className={`${STATUS_COLORS[o.status] || ""} hover:opacity-100 capitalize`}>{o.status}</Badge>
                <div className="font-semibold">{fmtINR(o.total)}</div>
              </div>
            ))}</div>
          )}
        </TabsContent>
        <TabsContent value="learning" className="mt-6">
          {enrollments.length === 0 ? (
            <div className="text-center py-12 text-[var(--gs-muted)]"><GraduationCap className="h-10 w-10 mx-auto mb-2"/><p>No enrollments yet</p></div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4" data-testid="account-enrollments">{enrollments.map((e) => (
              <Link key={e.id} to={`/academy/${e.course_slug}/learn`} className="gs-card gs-card-hover overflow-hidden">
                {e.course?.thumbnail && <img src={e.course.thumbnail} alt="" className="w-full h-32 object-cover"/>}
                <div className="p-4">
                  <div className="font-semibold mb-1">{e.course?.title}</div>
                  <div className="text-xs text-[var(--gs-muted)] mb-2">{e.course?.level}</div>
                  <Progress value={(e.progress || 0) * 100} className="h-1.5 mb-1"/>
                  <div className="text-xs text-[var(--gs-muted)]">{Math.round((e.progress || 0) * 100)}% complete</div>
                </div>
              </Link>
            ))}</div>
          )}
        </TabsContent>
        <TabsContent value="profile" className="mt-6">
          <div className="gs-card p-6 max-w-md">
            <div className="text-sm text-[var(--gs-muted)]">Name</div><div className="font-semibold mb-3">{user.name}</div>
            <div className="text-sm text-[var(--gs-muted)]">Email</div><div className="font-semibold mb-3">{user.email}</div>
            <div className="text-sm text-[var(--gs-muted)]">Role</div><div className="font-semibold capitalize">{user.role}</div>
          </div>
        </TabsContent>
        <TabsContent value="subscription" className="mt-6">
          {sub ? (
            <div className="gs-card p-6 max-w-md" data-testid="account-subscription-card">
              <div className="flex items-center gap-2 mb-3"><Crown className="h-5 w-5 text-[var(--gs-teal)]"/><h3 className="font-display text-2xl capitalize">{sub.plan}</h3></div>
              <div className="text-sm text-[var(--gs-muted)] mb-1">Status: <span className="font-semibold capitalize text-[var(--gs-ink)]">{sub.status}</span></div>
              {sub.trial_ends_at && <div className="text-sm text-[var(--gs-muted)] mb-1">Trial ends: <span className="text-[var(--gs-ink)]">{new Date(sub.trial_ends_at).toLocaleDateString()}</span></div>}
              {sub.current_period_end && <div className="text-sm text-[var(--gs-muted)] mb-1">Renews: <span className="text-[var(--gs-ink)]">{new Date(sub.current_period_end).toLocaleDateString()}</span></div>}
              <div className="text-sm text-[var(--gs-muted)] mb-4">Studio builds: <span className="text-[var(--gs-ink)]">{sub.studio_builds_used || 0} / {sub.quota?.studio_builds === 9999 ? "∞" : sub.quota?.studio_builds || 0}</span> this month</div>
              <div className="flex gap-2">
                {sub.plan === "free" ? (
                  <Link to="/pricing"><Button className="bg-[var(--gs-teal)] hover:bg-[var(--gs-teal)]/90">Upgrade <ArrowRight className="h-4 w-4 ml-2"/></Button></Link>
                ) : (
                  <>
                    <Link to="/pricing"><Button variant="outline">Change plan</Button></Link>
                    {sub.status !== "cancelled" && <Button variant="outline" onClick={cancelSub} className="text-rose-600">Cancel</Button>}
                  </>
                )}
              </div>
            </div>
          ) : <div className="py-12 text-center text-[var(--gs-muted)]">Loading…</div>}
        </TabsContent>
      </Tabs>
    </div>
  );
}
