import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = await login(email, password);
      toast.success(`Welcome back, ${u.name}!`);
      navigate(u.role === "admin" ? "/admin" : "/dashboard");
    } catch (err) { toast.error(err?.response?.data?.detail || "Login failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="gs-container py-16 max-w-md mx-auto">
      <div className="gs-card p-8">
        <h1 className="font-display text-3xl mb-1">Welcome back</h1>
        <p className="text-sm text-[var(--gs-muted)] mb-6">Sign in to continue shopping & learning.</p>
        <form onSubmit={submit} className="space-y-3">
          <Input type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input"/>
          <Input type="password" required placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input"/>
          <Button type="submit" disabled={busy} className="w-full h-12 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="login-form-submit-button">{busy ? "Signing in…" : "Sign in"}</Button>
        </form>
        <div className="mt-4 text-sm text-center text-[var(--gs-muted)]">No account? <Link to="/signup" className="gs-link font-semibold">Sign up</Link></div>
      </div>
    </div>
  );
}
