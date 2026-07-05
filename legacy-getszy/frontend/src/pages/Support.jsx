import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { HelpCircle, MessageSquare, ThumbsUp, Send, Sparkles, Loader2, Plus, ChevronUp } from "lucide-react";
import { toast } from "sonner";

export default function Support() {
  const { user } = useAuth();
  const [tab, setTab] = useState("faq"); // faq | ticket | features
  const [faq, setFaq] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [features, setFeatures] = useState([]);
  const [featureSort, setFeatureSort] = useState("votes");

  const [ticketForm, setTicketForm] = useState({ subject: "", category: "general", body: "" });
  const [featureForm, setFeatureForm] = useState({ title: "", description: "" });
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get("/support/faq").then(({ data }) => setFaq(data.items || []));
    api.get(`/support/features?sort=${featureSort}`).then(({ data }) => setFeatures(data.items || []));
    if (user) api.get("/support/tickets").then(({ data }) => setTickets(data.items || []));
  }, [user, featureSort]);

  const submitTicket = async (e) => {
    e.preventDefault();
    if (!user) { toast.error("Please sign in to open a ticket"); return; }
    setBusy("ticket");
    try {
      await api.post("/support/ticket", ticketForm);
      toast.success("Ticket submitted — team will reply soon");
      setTicketForm({ subject: "", category: "general", body: "" });
      const r = await api.get("/support/tickets");
      setTickets(r.data.items || []);
      setTab("ticket");
    } catch (e) { toast.error(e?.response?.data?.detail || "Submit failed"); }
    finally { setBusy(""); }
  };

  const submitFeature = async (e) => {
    e.preventDefault();
    if (!user) { toast.error("Please sign in to suggest features"); return; }
    setBusy("feature");
    try {
      await api.post("/support/features", featureForm);
      toast.success("Feature request submitted");
      setFeatureForm({ title: "", description: "" });
      const r = await api.get(`/support/features?sort=${featureSort}`);
      setFeatures(r.data.items || []);
    } catch (e) { toast.error(e?.response?.data?.detail || "Submit failed"); }
    finally { setBusy(""); }
  };

  const vote = async (id) => {
    if (!user) { toast.error("Please sign in to vote"); return; }
    try {
      const r = await api.post(`/support/features/${id}/vote`);
      const rr = await api.get(`/support/features?sort=${featureSort}`);
      setFeatures(rr.data.items || []);
      if (r.data.voted) toast.success("Voted"); else toast.message("Vote removed");
    } catch (e) { toast.error("Vote failed"); }
  };

  return (
    <div className="gs-container py-10 max-w-4xl" data-testid="support-page">
      <div className="text-center mb-8">
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-teal)] mb-2">Support</div>
        <h1 className="font-display text-4xl mb-2">How can we help?</h1>
        <p className="text-sm text-[var(--gs-muted)]">FAQ, contact ticket ya feature request — sab yahan.</p>
      </div>

      <div className="flex justify-center gap-1 mb-6 border-b" style={{ borderColor: "var(--gs-border)" }} role="tablist" aria-label="Support sections">
        {[
          { k: "faq", label: "FAQ", Icon: HelpCircle },
          { k: "ticket", label: "Contact", Icon: MessageSquare },
          { k: "features", label: "Feature requests", Icon: Sparkles },
        ].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)}
            role="tab" aria-selected={tab === t.k}
            className={`px-4 py-2 text-sm flex items-center gap-1.5 border-b-2 -mb-px transition ${tab === t.k ? "border-[var(--gs-teal)] text-[var(--gs-teal)]" : "border-transparent text-[var(--gs-muted)] hover:text-[var(--gs-ink)]"}`}
            data-testid={`support-tab-${t.k}`}>
            <t.Icon className="h-4 w-4"/>{t.label}
          </button>
        ))}
      </div>

      {tab === "faq" && (
        <Card className="p-2" data-testid="support-faq">
          <Accordion type="single" collapsible>
            {faq.map((f, i) => (
              <AccordionItem key={i} value={`f-${i}`}>
                <AccordionTrigger className="text-left text-sm px-3" data-testid={`faq-q-${i}`}>{f.q}</AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--gs-muted)] px-3 pb-3" data-testid={`faq-a-${i}`}>{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </Card>
      )}

      {tab === "ticket" && (
        <div className="space-y-6">
          <Card className="p-5" data-testid="ticket-form">
            <h3 className="font-display text-xl mb-3">Open a support ticket</h3>
            <form onSubmit={submitTicket} className="space-y-3">
              <Input placeholder="Subject" value={ticketForm.subject} onChange={(e) => setTicketForm({ ...ticketForm, subject: e.target.value })} required minLength={3} data-testid="ticket-subject-input"/>
              <select value={ticketForm.category} onChange={(e) => setTicketForm({ ...ticketForm, category: e.target.value })}
                className="w-full h-10 rounded-lg border bg-white px-3 text-sm" style={{ borderColor: "var(--gs-border)" }}
                data-testid="ticket-category-select" aria-label="Category">
                <option value="general">General question</option>
                <option value="bug">Bug report</option>
                <option value="billing">Billing / subscription</option>
                <option value="feature">Feature suggestion</option>
                <option value="other">Other</option>
              </select>
              <Textarea rows={5} placeholder="Describe your issue in detail…" value={ticketForm.body} onChange={(e) => setTicketForm({ ...ticketForm, body: e.target.value })} required minLength={8} data-testid="ticket-body-input"/>
              <Button type="submit" disabled={busy === "ticket"} className="bg-[var(--gs-teal)] gap-2" data-testid="ticket-submit-btn">
                {busy === "ticket" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Send className="h-4 w-4"/>} Submit
              </Button>
            </form>
          </Card>

          {tickets.length > 0 && (
            <div>
              <h3 className="font-display text-lg mb-2">Your tickets</h3>
              <div className="space-y-1.5" data-testid="my-tickets">
                {tickets.map(t => (
                  <div key={t.id} className="gs-card p-3 flex items-start gap-3" data-testid={`ticket-${t.id}`}>
                    <div className={`h-2 w-2 rounded-full mt-2 shrink-0 ${t.status === "resolved" ? "bg-emerald-500" : t.status === "in_progress" ? "bg-amber-500" : "bg-[var(--gs-teal)]"}`}/>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm">{t.subject}</div>
                      <div className="text-xs text-[var(--gs-muted)] mt-0.5 line-clamp-2">{t.body}</div>
                      {t.admin_reply && (
                        <div className="mt-2 p-2 rounded bg-[var(--gs-surface-2)] text-xs">
                          <span className="font-semibold">Reply: </span>{t.admin_reply}
                        </div>
                      )}
                    </div>
                    <Badge variant="outline" className="text-[9px]">{t.status}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "features" && (
        <div className="space-y-6">
          <Card className="p-5" data-testid="feature-form">
            <h3 className="font-display text-xl mb-3">Suggest a feature</h3>
            <form onSubmit={submitFeature} className="space-y-3">
              <Input placeholder="Feature title (e.g. 'Bulk video export')" value={featureForm.title} onChange={(e) => setFeatureForm({ ...featureForm, title: e.target.value })} required minLength={4} data-testid="feature-title-input"/>
              <Textarea rows={3} placeholder="Optional description or use-case" value={featureForm.description} onChange={(e) => setFeatureForm({ ...featureForm, description: e.target.value })} data-testid="feature-desc-input"/>
              <Button type="submit" disabled={busy === "feature"} className="bg-[var(--gs-teal)] gap-2" data-testid="feature-submit-btn">
                {busy === "feature" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Plus className="h-4 w-4"/>} Submit
              </Button>
            </form>
          </Card>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-display text-lg">Community requests</h3>
              <div className="ml-auto flex gap-1 text-xs">
                <button onClick={() => setFeatureSort("votes")} className={`px-2 py-1 rounded ${featureSort === "votes" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)]"}`} data-testid="features-sort-votes">Top voted</button>
                <button onClick={() => setFeatureSort("new")} className={`px-2 py-1 rounded ${featureSort === "new" ? "bg-[var(--gs-teal)] text-white" : "bg-[var(--gs-surface-2)]"}`} data-testid="features-sort-new">Newest</button>
              </div>
            </div>
            {features.length === 0 ? (
              <Card className="p-8 text-center text-sm text-[var(--gs-muted)]" data-testid="features-empty">
                No feature requests yet — be the first!
              </Card>
            ) : (
              <div className="space-y-2" data-testid="features-list">
                {features.map(f => (
                  <div key={f.id} className="gs-card p-3 flex items-start gap-3" data-testid={`feature-${f.id}`}>
                    <button onClick={() => vote(f.id)}
                      className="flex flex-col items-center gap-0 shrink-0 px-2 py-1 rounded-lg hover:bg-[var(--gs-surface-2)] transition"
                      aria-label={`Vote for ${f.title}`}
                      data-testid={`feature-vote-${f.id}`}>
                      <ChevronUp className="h-4 w-4 text-[var(--gs-teal)]"/>
                      <span className="font-semibold text-sm">{f.vote_count}</span>
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="font-semibold text-sm">{f.title}</div>
                        <Badge variant="outline" className="text-[9px]">{f.status}</Badge>
                      </div>
                      {f.description && <div className="text-xs text-[var(--gs-muted)] mt-1">{f.description}</div>}
                      <div className="text-[10px] text-[var(--gs-muted)] mt-1">by {f.author_name || "user"} · {new Date(f.created_at).toLocaleDateString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
