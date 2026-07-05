import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { ShoppingBag, Search, User, Menu, Sparkles, LogOut, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";
import { api } from "@/lib/api";
import { PlanBadge } from "@/components/PlanBadge";

export function Header() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [cats, setCats] = useState([]);

  useEffect(() => {
    api.get("/categories").then(({ data }) => setCats(data)).catch(() => {});
  }, []);

  const submitSearch = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/shop?search=${encodeURIComponent(q.trim())}`);
  };

  return (
    <header className="sticky top-0 z-40 border-b" style={{ background: "var(--gs-surface)", borderColor: "var(--gs-border)" }}>
      <div className="gs-container flex items-center gap-3 h-16">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden" data-testid="header-mobile-menu-button"><Menu className="h-5 w-5"/></Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72">
            <div className="font-display text-2xl mb-6">getszy</div>
            <nav className="flex flex-col gap-1">
              <Link to="/shop" className="py-2 hover:text-[var(--gs-primary-2)]">All Products</Link>
              {cats.map((c) => (
                <Link key={c.slug} to={`/category/${c.slug}`} className="py-2 hover:text-[var(--gs-primary-2)]">{c.name}</Link>
              ))}
            </nav>
          </SheetContent>
        </Sheet>

        <Link to="/" className="font-display text-2xl tracking-tight" data-testid="header-logo-link">
          getszy
        </Link>

        <nav className="hidden md:flex items-center gap-5 ml-6 text-sm">
          <Link to="/shop" className="hover:text-[var(--gs-primary-2)]">Shop</Link>
          {cats.slice(0, 4).map((c) => (
            <Link key={c.slug} to={`/category/${c.slug}`} className="hover:text-[var(--gs-primary-2)]">{c.name}</Link>
          ))}
          <Link to="/pricing" className="hover:text-[var(--gs-ink)]" data-testid="header-pricing-link">Pricing</Link>
        </nav>

        <form onSubmit={submitSearch} className="flex-1 hidden md:flex justify-center max-w-md ml-4">
          <div className="relative w-full">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gs-muted)]"/>
            <Input data-testid="header-search-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search dresses, jewellery, gadgets..." className="pl-9 h-10"/>
          </div>
        </form>

        <div className="ml-auto flex items-center gap-2">
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" data-testid="header-user-menu-button"><User className="h-5 w-5"/></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5 text-sm font-medium">{user.name}</div>
                <div className="px-2 pb-1.5 text-xs text-[var(--gs-muted)]">{user.email}</div>
                <div className="px-2 pb-2"><PlanBadge plan={user.subscription?.plan || "free"} status={user.subscription?.status}/></div>
                <DropdownMenuSeparator/>
                <DropdownMenuItem onClick={() => navigate("/account")} data-testid="header-account-item"><User className="h-4 w-4 mr-2"/>My Account</DropdownMenuItem>
                {user.role === "admin" && (
                  <DropdownMenuItem onClick={() => navigate("/admin")} data-testid="header-admin-item"><LayoutDashboard className="h-4 w-4 mr-2"/>Admin Dashboard</DropdownMenuItem>
                )}
                <DropdownMenuSeparator/>
                <DropdownMenuItem onClick={() => { logout(); navigate("/"); }} data-testid="header-logout-item"><LogOut className="h-4 w-4 mr-2"/>Logout</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button variant="ghost" onClick={() => navigate("/login")} data-testid="header-login-button" className="text-sm">Login</Button>
          )}
          <Link to="/cart" className="relative" data-testid="header-cart-link">
            <Button variant="ghost" size="icon"><ShoppingBag className="h-5 w-5"/></Button>
            {cart.count > 0 && (
              <span className="absolute -top-1 -right-1 bg-[var(--gs-primary)] text-white text-[10px] rounded-full h-5 w-5 flex items-center justify-center font-semibold">{cart.count}</span>
            )}
          </Link>
        </div>
      </div>
    </header>
  );
}
