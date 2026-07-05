import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Download, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Privacy() {
  const { user } = useAuth();
  const [busy, setBusy] = useState("");

  const exportData = async () => {
    if (!user) { toast.error("Please sign in to export your data"); return; }
    setBusy("export");
    try {
      const backend = process.env.REACT_APP_BACKEND_URL || "";
      const token = localStorage.getItem("token") || "";
      const r = await fetch(`${backend}/api/legal/data-export`, { headers: { Authorization: `Bearer ${token}` } });
      if (!r.ok) throw new Error("Export failed");
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `getszy-data-${user.email}.zip`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Data export downloaded");
    } catch (e) { toast.error("Export failed"); }
    finally { setBusy(""); }
  };

  const requestDelete = async () => {
    if (!user) { toast.error("Please sign in first"); return; }
    if (!confirm("Confirm account & data deletion request? Team will process within 7 days.")) return;
    setBusy("delete");
    try {
      await api.post("/legal/data-delete");
      toast.success("Deletion request submitted");
    } catch (e) { toast.error("Request failed"); }
    finally { setBusy(""); }
  };

  return (
    <div className="gs-container py-12 max-w-3xl" data-testid="privacy-page">
      <h1 className="font-display text-4xl mb-2">Privacy Policy</h1>
      <p className="text-xs text-[var(--gs-muted)] mb-8">Last updated: {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</p>

      <div className="prose prose-sm max-w-none space-y-6 text-[var(--gs-fg)]">
        <section>
          <h2 className="font-display text-xl">1. Who we are</h2>
          <p className="text-sm text-[var(--gs-muted)]">Getszy (“we”) is an AI creator platform operated in India. We act as a Data Fiduciary under the Digital Personal Data Protection Act, 2023.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">2. Data we collect</h2>
          <ul className="text-sm text-[var(--gs-muted)] list-disc pl-5 space-y-1">
            <li><b>Account</b>: name, email, hashed password, role.</li>
            <li><b>Content</b>: chat messages, prompts, uploaded files, AI outputs, hosted webapps.</li>
            <li><b>Commerce</b>: orders, shipping address, payment status (payments are processed by Razorpay — we never see full card numbers).</li>
            <li><b>Learning</b>: course enrollments, lesson progress.</li>
            <li><b>Technical</b>: IP address, browser, device (for security & analytics only).</li>
          </ul>
        </section>

        <section>
          <h2 className="font-display text-xl">3. How we use it</h2>
          <p className="text-sm text-[var(--gs-muted)]">To provide the Service, personalize AI outputs, process payments, deliver orders, respond to support requests, prevent fraud, and comply with law. We do not sell personal data.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">4. Third parties (Sub-processors)</h2>
          <ul className="text-sm text-[var(--gs-muted)] list-disc pl-5 space-y-1">
            <li><b>Razorpay</b> — payment processing (PCI-DSS certified).</li>
            <li><b>OpenAI / Google / Anthropic</b> — LLM inference (routed via Emergent LLM proxy, no direct sharing of your account identity).</li>
            <li><b>Pollinations.ai / edge-tts</b> — image/voice generation.</li>
            <li><b>MongoDB Atlas / VPS provider</b> — hosting.</li>
          </ul>
        </section>

        <section>
          <h2 className="font-display text-xl">5. Your rights (DPDP Act 2023, GDPR)</h2>
          <ul className="text-sm text-[var(--gs-muted)] list-disc pl-5 space-y-1">
            <li><b>Access</b>: Download all your data as a ZIP any time.</li>
            <li><b>Rectification</b>: Update profile via Account settings.</li>
            <li><b>Erasure</b>: Request account + data deletion.</li>
            <li><b>Withdraw consent</b>: Cancel subscription; delete account.</li>
            <li><b>Grievance</b>: Email <a className="text-[var(--gs-teal)] underline" href="mailto:grievance@getszy.com">grievance@getszy.com</a> — response within 7 days.</li>
          </ul>
        </section>

        <section className="gs-card p-4" data-testid="privacy-rights-panel">
          <h3 className="font-display text-lg mb-3">Exercise your rights</h3>
          <div className="flex flex-wrap gap-2">
            <Button onClick={exportData} disabled={busy === "export" || !user} className="gap-2 bg-[var(--gs-teal)]" data-testid="privacy-export-btn">
              {busy === "export" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Download className="h-4 w-4"/>} Download my data
            </Button>
            <Button onClick={requestDelete} disabled={busy === "delete" || !user} variant="outline" className="gap-2 text-rose-600 border-rose-200 hover:bg-rose-50" data-testid="privacy-delete-btn">
              {busy === "delete" ? <Loader2 className="h-4 w-4 animate-spin"/> : <Trash2 className="h-4 w-4"/>} Request deletion
            </Button>
          </div>
          {!user && <p className="text-xs text-[var(--gs-muted)] mt-2">Sign in to use these tools.</p>}
        </section>

        <section>
          <h2 className="font-display text-xl">6. Security</h2>
          <p className="text-sm text-[var(--gs-muted)]">Passwords are hashed (bcrypt). Data-in-transit is TLS-encrypted. We follow least-privilege access controls. In the event of a breach affecting your data, we will notify affected users and the Data Protection Board of India within 72 hours as required by DPDP Act §8.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">7. Cookies</h2>
          <p className="text-sm text-[var(--gs-muted)]">We use essential cookies for authentication (JWT token in localStorage) and preferences (theme, onboarding). No third-party ad trackers. See our cookie banner for full details.</p>
        </section>

        <p className="text-xs text-[var(--gs-muted)]">See also: <Link to="/terms" className="text-[var(--gs-teal)] underline">Terms of Service</Link></p>
      </div>
    </div>
  );
}
