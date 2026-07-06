import { Link } from "react-router-dom";
import { Sparkles, Bot, GraduationCap, ShoppingBag } from "lucide-react";

export default function About() {
  return (
    <div className="gs-container py-12 max-w-3xl" data-testid="about-page">
      <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-primary-2)] mb-4 flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5" /> Our story
      </div>
      <h1 className="font-display text-4xl mb-4">About getszy</h1>
      <p className="text-base text-[var(--gs-muted)] mb-8">
        getszy started as a premium destination for women's fashion, beauty and lifestyle essentials.
        We're now growing into something more — a platform where you can shop what you love and also
        build, create and earn with AI, without needing to write a single line of code.
      </p>

      <div className="grid sm:grid-cols-3 gap-6 mb-10">
        <div className="gs-card p-5">
          <ShoppingBag className="h-5 w-5 text-[var(--gs-primary)] mb-3" />
          <h3 className="font-display text-lg mb-1">Shop</h3>
          <p className="text-sm text-[var(--gs-muted)]">Curated fashion, beauty, jewellery and kids' essentials made for women who do it all.</p>
        </div>
        <div className="gs-card p-5">
          <Bot className="h-5 w-5 text-[var(--gs-primary)] mb-3" />
          <h3 className="font-display text-lg mb-1">Create</h3>
          <p className="text-sm text-[var(--gs-muted)]">AI tools for images, faceless videos, logos and voice — built for creators and small businesses.</p>
        </div>
        <div className="gs-card p-5">
          <GraduationCap className="h-5 w-5 text-[var(--gs-primary)] mb-3" />
          <h3 className="font-display text-lg mb-1">Learn</h3>
          <p className="text-sm text-[var(--gs-muted)]">Guided courses and an AI tutor to help you go from idea to running business, step by step.</p>
        </div>
      </div>

      <p className="text-sm text-[var(--gs-muted)]">
        Have questions or feedback? We'd love to hear from you —{" "}
        <Link to="/support" className="text-[var(--gs-teal)] underline">reach out via Support</Link>.
      </p>
    </div>
  );
}
