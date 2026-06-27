import { Sparkles, Instagram, Twitter, Facebook } from "lucide-react";
import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="mt-16 border-t" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
      <div className="gs-container py-10 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
        <div>
          <div className="font-display text-2xl mb-2">getszy</div>
          <p className="text-sm text-[var(--gs-muted)]">Made for women who do it all. Shop. Learn. Build. Earn.</p>
        </div>
        <div>
          <div className="font-semibold mb-3 text-sm">Shop</div>
          <ul className="space-y-2 text-sm text-[var(--gs-muted)]">
            <li><Link to="/category/fashion" className="hover:text-[var(--gs-ink)]">Fashion</Link></li>
            <li><Link to="/category/jewellery" className="hover:text-[var(--gs-ink)]">Jewellery</Link></li>
            <li><Link to="/category/beauty" className="hover:text-[var(--gs-ink)]">Beauty</Link></li>
            <li><Link to="/category/kids" className="hover:text-[var(--gs-ink)]">Kids</Link></li>
          </ul>
        </div>
        <div>
          <div className="font-semibold mb-3 text-sm">Company</div>
          <ul className="space-y-2 text-sm text-[var(--gs-muted)]">
            <li><a href="#" className="hover:text-[var(--gs-ink)]">About</a></li>
            <li><a href="#" className="hover:text-[var(--gs-ink)]">Contact</a></li>
            <li><a href="#" className="hover:text-[var(--gs-ink)]">Privacy</a></li>
          </ul>
        </div>
        <div>
          <div className="font-semibold mb-3 text-sm flex items-center gap-2"><Sparkles className="h-4 w-4 text-[var(--gs-primary)]"/>Stay in the loop</div>
          <p className="text-xs text-[var(--gs-muted)] mb-2">New drops, AI launches, women-first stories.</p>
          <div className="flex gap-3 text-[var(--gs-muted)]"><Instagram className="h-4 w-4"/><Twitter className="h-4 w-4"/><Facebook className="h-4 w-4"/></div>
        </div>
      </div>
      <div className="border-t text-center text-xs py-4 text-[var(--gs-muted)]" style={{ borderColor: "var(--gs-border)" }}>© {new Date().getFullYear()} getszy. All rights reserved.</div>
    </footer>
  );
}
