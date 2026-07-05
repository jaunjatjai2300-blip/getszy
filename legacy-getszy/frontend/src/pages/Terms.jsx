import { Link } from "react-router-dom";

export default function Terms() {
  return (
    <div className="gs-container py-12 max-w-3xl" data-testid="terms-page">
      <h1 className="font-display text-4xl mb-2">Terms of Service</h1>
      <p className="text-xs text-[var(--gs-muted)] mb-8">Last updated: {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</p>

      <div className="prose prose-sm max-w-none space-y-6 text-[var(--gs-fg)]">
        <section>
          <h2 className="font-display text-xl">1. Acceptance</h2>
          <p className="text-sm text-[var(--gs-muted)]">By accessing or using getszy.com (the “Service”) you agree to these Terms. If you do not agree, do not use the Service. These Terms are governed by the laws of India, including the Information Technology Act, 2000 and the Digital Personal Data Protection Act, 2023.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">2. The Service</h2>
          <p className="text-sm text-[var(--gs-muted)]">Getszy is an AI-native creator platform offering: (a) an AI Assistant (Neo) that generates scripts, videos, webapps, and content; (b) a storefront for physical/digital products; and (c) hosting for AI-built webapps at *.getszy.com. Features may change without notice.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">3. Accounts</h2>
          <p className="text-sm text-[var(--gs-muted)]">You must provide accurate registration information and keep your credentials confidential. You are responsible for all activity under your account. You must be 18+ or have parental consent.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">4. AI-Generated Content</h2>
          <p className="text-sm text-[var(--gs-muted)]">Neo generates content based on your prompts. You retain ownership of your prompts and the resulting outputs, subject to the license below. You are solely responsible for how you use AI outputs — verify facts, respect third-party rights, and do not use outputs for illegal, defamatory, or harmful purposes.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">5. Acceptable Use</h2>
          <ul className="text-sm text-[var(--gs-muted)] list-disc pl-5 space-y-1">
            <li>No illegal content, hate speech, harassment, or CSAM.</li>
            <li>No infringement of copyright, trademark, or privacy rights.</li>
            <li>No spam, phishing, or malware distribution via hosted subdomains.</li>
            <li>No attempts to reverse-engineer, scrape, or overload the Service.</li>
          </ul>
        </section>

        <section>
          <h2 className="font-display text-xl">6. Payments & Subscriptions</h2>
          <p className="text-sm text-[var(--gs-muted)]">Paid plans are billed monthly in INR via Razorpay. GST included where applicable. You may cancel any time — access continues until the end of the paid period. No refunds for partial months.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">7. Termination</h2>
          <p className="text-sm text-[var(--gs-muted)]">We may suspend or terminate accounts that violate these Terms. You may delete your account and request data erasure at any time via Account → Data Export / Delete.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">8. Disclaimers & Liability</h2>
          <p className="text-sm text-[var(--gs-muted)]">The Service is provided “as is” without warranties. To the maximum extent permitted by law, Getszy's total liability shall not exceed the amount you paid in the previous 3 months.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">9. Governing Law</h2>
          <p className="text-sm text-[var(--gs-muted)]">These Terms are governed by the laws of India. Disputes shall be resolved in the courts of Jaipur, Rajasthan.</p>
        </section>

        <section>
          <h2 className="font-display text-xl">10. Contact</h2>
          <p className="text-sm text-[var(--gs-muted)]">Questions? Reach us at <a className="text-[var(--gs-teal)] underline" href="mailto:support@getszy.com">support@getszy.com</a> or via <Link to="/support" className="text-[var(--gs-teal)] underline">/support</Link>.</p>
        </section>

        <p className="text-xs text-[var(--gs-muted)]">See also: <Link to="/privacy" className="text-[var(--gs-teal)] underline">Privacy Policy</Link></p>
      </div>
    </div>
  );
}
