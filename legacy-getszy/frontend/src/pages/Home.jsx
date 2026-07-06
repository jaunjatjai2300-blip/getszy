import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowRight, Sparkles, Bot, GraduationCap, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { ProductCard } from "@/components/ProductCard";
import { CategoryCard } from "@/components/CategoryCard";

export default function Home() {
  const [cats, setCats] = useState([]);
  const [trending, setTrending] = useState([]);
  const [newsletterEmail, setNewsletterEmail] = useState("");
  const [newsletterLoading, setNewsletterLoading] = useState(false);

  useEffect(() => {
    api.get("/categories").then(({ data }) => setCats(data)).catch(() => setCats([]));
    api.get("/products?featured=true&limit=8").then(({ data }) => setTrending(data)).catch(() => setTrending([]));
  }, []);

  const handleNewsletterSubmit = async (e) => {
    e.preventDefault();
    const email = newsletterEmail.trim();
    if (!email || !email.includes("@")) {
      toast.error("Please enter a valid email address.");
      return;
    }
    setNewsletterLoading(true);
    try {
      const { data } = await api.post("/waitlist", { email, interest: "newsletter", source: "home_newsletter" });
      if (data?.status === "already_subscribed") {
        toast.info("You're already on the list!");
      } else {
        toast.success("You're subscribed! We'll keep you posted.");
      }
      setNewsletterEmail("");
    } catch {
      toast.error("Couldn't subscribe right now. Please try again.");
    } finally {
      setNewsletterLoading(false);
    }
  };

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-[55%] gs-hero-wash pointer-events-none"/>
        <div className="gs-container relative grid lg:grid-cols-2 gap-10 py-12 lg:py-20 items-center">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-primary-2)] mb-4 flex items-center gap-2"><Sparkles className="h-3.5 w-3.5"/>Made for women who do it all</div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display leading-[1.05] tracking-tight">Shop premium essentials.<br/>Learn AI.<br/>Run your business — without coding.</h1>
            <p className="mt-6 text-base sm:text-lg text-[var(--gs-muted)] max-w-xl">Fashion, beauty, kids, home + powerful digital tools.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/shop" data-testid="hero-primary-cta-button"><Button size="lg" className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)] h-12 px-6 text-base">Shop Women <ArrowRight className="h-4 w-4 ml-2"/></Button></Link>
              <Link to="/category/digital-products" data-testid="hero-secondary-cta-button"><Button size="lg" variant="outline" className="h-12 px-6 text-base border-[var(--gs-border)]">Explore Digital Tools</Button></Link>
            </div>
            <div className="mt-10 grid grid-cols-3 gap-4 max-w-md">
              {[{ icon: Bot, label: "AI Admin Chat" }, { icon: GraduationCap, label: "AI Learning" }, { icon: Wand2, label: "App Generator" }].map((f) => (
                <div key={f.label} className="flex flex-col items-start gap-2"><div className="h-9 w-9 rounded-xl flex items-center justify-center" style={{ background: "var(--gs-teal-soft)" }}><f.icon className="h-4 w-4 text-[var(--gs-teal)]"/></div><div className="text-xs text-[var(--gs-muted)]">{f.label}</div></div>
              ))}
            </div>
          </div>
          {/* Bento collage */}
          <div className="grid grid-cols-2 grid-rows-2 gap-3 sm:gap-4 aspect-[1.1/1]">
            <div className="row-span-2 rounded-2xl overflow-hidden"><img src="https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800" alt="Fashion" className="w-full h-full object-cover"/></div>
            <div className="rounded-2xl overflow-hidden"><img src="https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600" alt="Jewellery" className="w-full h-full object-cover"/></div>
            <div className="rounded-2xl overflow-hidden"><img src="https://images.unsplash.com/photo-1522335789203-aaa2f6ed9b51?w=600" alt="Beauty" className="w-full h-full object-cover"/></div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="gs-section" data-testid="home-categories-grid">
        <div className="gs-container">
          <div className="flex items-end justify-between mb-6">
            <h2 className="font-display text-2xl sm:text-3xl">Shop by Category</h2>
            <Link to="/shop" className="text-sm gs-link">View all <ArrowRight className="h-3 w-3 inline"/></Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 auto-rows-[140px] sm:auto-rows-[180px]">
            {cats.slice(0, 7).map((c, i) => (
              <CategoryCard key={c.slug} category={c} large={i === 0}/>
            ))}
          </div>
        </div>
      </section>

      {/* TRENDING */}
      <section className="gs-section" data-testid="home-trending-products">
        <div className="gs-container">
          <div className="flex items-end justify-between mb-6">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--gs-primary-2)] mb-1">Trending now</div>
              <h2 className="font-display text-2xl sm:text-3xl">Loved by our community</h2>
            </div>
            <Link to="/shop" className="text-sm gs-link">Shop all <ArrowRight className="h-3 w-3 inline"/></Link>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-5">
            {trending.map((p) => <ProductCard key={p.id} product={p}/>)}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="gs-section" data-testid="home-testimonials">
        <div className="gs-container">
          <h2 className="font-display text-2xl sm:text-3xl mb-8 text-center">Voices from getszy</h2>
          <div className="grid md:grid-cols-3 gap-5">
            {[{ q: "Maine ek week me apna dropshipping store launch kiya — sab AI chat se. Insane!", n: "Aanya — Mumbai" }, { q: "AI Learning ke courses ne mujhe job dilai. Premium feel + practical content.", n: "Riya — Bengaluru" }, { q: "Beauty + jewellery quality genuinely premium hai. My new favourite store.", n: "Meher — Delhi" }].map((t, i) => (
              <div key={i} className="gs-card p-6">
                <p className="font-display text-lg leading-snug mb-3">“{t.q}”</p>
                <div className="text-sm text-[var(--gs-muted)]">{t.n}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="gs-container my-10">
        <div className="rounded-3xl p-8 sm:p-12 flex flex-col sm:flex-row items-start sm:items-center gap-6 sm:justify-between" style={{ background: "var(--gs-champagne)" }} data-testid="newsletter-signup-form">
          <div>
            <h3 className="font-display text-2xl sm:text-3xl">Be first to know</h3>
            <p className="text-sm text-[var(--gs-muted)] mt-1">New drops, AI launches, women-first stories — straight to your inbox.</p>
          </div>
          <form onSubmit={handleNewsletterSubmit} className="flex gap-2 w-full sm:w-auto">
            <input
              type="email"
              placeholder="Your email"
              value={newsletterEmail}
              onChange={(e) => setNewsletterEmail(e.target.value)}
              disabled={newsletterLoading}
              className="h-12 px-4 rounded-xl bg-white border min-w-[240px]"
              style={{ borderColor: "var(--gs-border)" }}
              data-testid="newsletter-email-input"
            />
            <Button type="submit" disabled={newsletterLoading} className="bg-[var(--gs-ink)] hover:bg-black h-12 px-6" data-testid="newsletter-submit-button">
              {newsletterLoading ? "Subscribing…" : "Subscribe"}
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}
