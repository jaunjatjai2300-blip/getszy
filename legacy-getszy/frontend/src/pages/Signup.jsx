import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { const u = await signup(form); toast.success(`Welcome, ${u.name}!`); navigate("/"); }
    catch (err) { toast.error(err?.response?.data?.detail || "Sign up failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="gs-container py-16 max-w-md mx-auto">
      <div className="gs-card p-8">
        <h1 className="font-display text-3xl mb-1">Join getszy</h1>
        <p className="text-sm text-[var(--gs-muted)] mb-6">Shop, learn, and build — all in one place.</p>
        <form onSubmit={submit} className="space-y-3">
          <Input required placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="signup-name-input"/>
          <Input type="email" required placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="signup-email-input"/>
          <Input placeholder="Phone (optional)" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}/>
          <Input type="password" required minLength={6} placeholder="Password (min 6 chars)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="signup-password-input"/>
          <Button type="submit" disabled={busy} className="w-full h-12 bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]" data-testid="signup-form-submit-button">{busy ? "Creating…" : "Create account"}</Button>
        </form>
        <div className="mt-4 text-sm text-center text-[var(--gs-muted)]">Have an account? <Link to="/login" className="gs-link font-semibold">Sign in</Link></div>
      </div>
    </div>
  );
}
