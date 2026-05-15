import { createFileRoute, redirect, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Loader2, GitBranch } from "lucide-react";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in · Pipeline Console" },
      { name: "description", content: "Sign in to access the self-healing DevSecOps dashboard." },
    ],
  }),
  beforeLoad: async () => {
    const { data } = await supabase.auth.getSession();
    if (data.session) {
      throw redirect({ to: "/" });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_evt, session) => {
      if (session) navigate({ to: "/" });
    });
    return () => subscription.unsubscribe();
  }, [navigate]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setInfo(null); setLoading(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email, password,
          options: { emailRedirectTo: window.location.origin },
        });
        if (error) throw error;
        setInfo("Check your inbox to confirm your email, then sign in.");
        setMode("signin");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/15 text-primary">
            <GitBranch size={16} />
          </div>
          <div className="font-mono text-[13px] tracking-wide">
            <span className="text-foreground">pipeline</span>
            <span className="text-muted-foreground">.console</span>
          </div>
        </div>

        <h1 className="text-xl font-semibold">
          {mode === "signin" ? "Sign in" : "Create account"}
        </h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          {mode === "signin"
            ? "Access the self-healing DevSecOps dashboard."
            : "Start orchestrating autonomous pipeline recovery."}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-3">
          <div>
            <label className="text-[11px] uppercase tracking-wider text-muted-foreground">Email</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] outline-none focus:border-primary"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-wider text-muted-foreground">Password</label>
            <input
              type="password" required minLength={6}
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-card px-3 py-2 text-[13px] outline-none focus:border-primary"
              placeholder="••••••••"
            />
          </div>

          {error && <div className="rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">{error}</div>}
          {info  && <div className="rounded border border-primary/40 bg-primary/10 px-3 py-2 text-[12px] text-primary">{info}</div>}

          <button
            type="submit" disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-[13px] font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div className="mt-5 text-center text-[12px] text-muted-foreground">
          {mode === "signin" ? (
            <>New here? <button onClick={() => { setMode("signup"); setError(null); setInfo(null); }} className="text-primary hover:underline">Create account</button></>
          ) : (
            <>Have an account? <button onClick={() => { setMode("signin"); setError(null); setInfo(null); }} className="text-primary hover:underline">Sign in</button></>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link to="/" className="text-[11px] text-muted-foreground hover:text-foreground">← Back</Link>
        </div>
      </div>
    </main>
  );
}
