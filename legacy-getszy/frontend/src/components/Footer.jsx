/* eslint-disable react/no-unescaped-entities */
import { useState } from "react";
import { Sparkle, Instagram, Twitter, Facebook, ArrowRight, Heart, ShoppingBag, GraduationCap, Wand2, User, LifeBuoy } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";

const COLUMNS = [
  {
    title: "Shop",
    icon: ShoppingBag,
    links: [
      { name: "Fashion", to: "/category/fashion" },
      { name: "Jewellery", to: "/category/jewellery" },
      { name: "Beauty", to: "/category/beauty" },
      { name: "Home", to: "/category/home-decor" },
      { name: "Kids", to: "/category/kids" },
      { name: "Gifts", to: "/shop" },
    ],
  },
  {
    title: "Learn",
    icon: GraduationCap,
    links: [
      { name: "AI Learning", to: "/category/digital-products" },
      { name: "Courses", to: "/category/digital-products" },
      { name: "eBooks", to: "/category/digital-products" },
      { name: "Practical Skills", to: "/category/digital-products" },
    ],
  },
  {
    title: "Build & Grow",
    icon: Wand2,
    links: [
      { name: "Website", to: "/dashboard/build" },
      { name: "Store", to: "/dashboard/build" },
      { name: "Creator Tools", to: "/dashboard/creator" },
      { name: "Business AI", to: "/ai-agents" },
      { name: "Solutions", to: "/pricing" },
    ],
  },
  {
    title: "My Getszy",
    icon: User,
    links: [
      { name: "Orders", to: "/account" },
      { name: "Projects", to: "/dashboard" },
      { name: "Downloads", to: "/account" },
      { name: "Wishlist", to: "/account" },
      { name: "Support", to: "/support" },
    ],
  },
  {
    title: "Company",
    icon: LifeBuoy,
    links: [
      { name: "About", to: "/about" },
      { name: "Contact", to: "/support" },
      { name: "Privacy", to: "/privacy" },
      { name: "Terms", to: "/terms" },
      { name: "Returns", to: "/support" },
    ],
  },
];

export function Footer() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const subscribe = async (e) => {
    e.preventDefault();
    const v = email.trim();
    if (!v || !v.includes("@")) return toast.error("Please enter a valid email.");
    setLoading(true);
    try {
      const { data } = await api.post("/waitlist", { email: v, interest: "newsletter", source: "footer_newsletter" });
      toast.success(data?.status === "already_subscribed" ? "You're already on the list!" : "Welcome to the Getszy Edit!");
      setEmail("");
    } catch {
      toast.error("Couldn't subscribe. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <footer className="mt-20 border-t" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
      <div className="gs-container py-14">
        <div className="grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4">
            <div className="font-display text-3xl tracking-tight">getszy</div>
            <p className="text-sm text-[var(--gs-muted)] mt-3 max-w-xs leading-relaxed">
              Made for women who do it all. Shop something beautiful, learn something useful, build something yours.
            </p>
            <div className="flex gap-2.5 mt-5">
              {[Instagram, Twitter, Facebook].map((Ic, i) => (
                <a key={i} href="#" aria-label="social" className="h-9 w-9 rounded-xl bg-[var(--gs-surface-2)] grid place-items-center text-[var(--gs-muted)] hover:bg-[var(--gs-primary)] hover:text-white transition-colors">
                  <Ic className="h-4 w-4" />
                </a>
              ))}
            </div>
            <form onSubmit={subscribe} className="mt-6 flex gap-2 max-w-sm">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Your email"
                className="flex-1 h-11 px-4 rounded-full bg-white border text-sm outline-none focus:ring-2 focus:ring-[var(--gs-primary)]/30"
                style={{ borderColor: "var(--gs-border)" }}
                data-testid="footer-newsletter-email"
              />
              <Button type="submit" disabled={loading} className="rounded-full h-11 px-5" data-testid="footer-newsletter-submit">
                {loading ? "…" : <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>
            <p className="text-[11px] text-[var(--gs-muted)] mt-2">Get the Getszy Edit — new drops, useful AI, stories worth knowing.</p>
          </div>

          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-8">
            {COLUMNS.map((col) => (
              <div key={col.title}>
                <div className="flex items-center gap-2 font-display text-sm font-semibold mb-3">
                  <col.icon className="h-4 w-4 text-[var(--gs-primary)]" />{col.title}
                </div>
                <ul className="space-y-2">
                  {col.links.map((l) => (
                    <li key={l.name}>
                      <Link to={l.to} className="text-xs text-[var(--gs-muted)] hover:text-[var(--gs-primary-2)] transition-colors">{l.name}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 pt-6 border-t flex flex-col sm:flex-row justify-between items-center gap-3" style={{ borderColor: "var(--gs-border)" }}>
          <div className="text-xs text-[var(--gs-muted)]">© {new Date().getFullYear()} Getszy. All rights reserved.</div>
          <div className="text-xs text-[var(--gs-muted)] flex items-center gap-1.5">
            <Heart className="h-3.5 w-3.5 text-[var(--gs-primary)]" /> Made with care for women who do it all.
          </div>
        </div>
      </div>
    </footer>
  );
}
