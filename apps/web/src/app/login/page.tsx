"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
      return;
    }
    // Oturum cookie'leri yazildiktan sonra korumali sayfaya git.
    router.push("/dashboard");
    router.refresh();
  }

  async function handleSignUp() {
    setError(null);
    setMessage(null);
    setLoading(true);
    const { data, error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
      return;
    }
    // E-posta onayi aciksa oturum hemen olusmaz.
    if (data.session) {
      router.push("/dashboard");
      router.refresh();
    } else {
      setMessage("Account created. If email confirmation is enabled, check your inbox, then sign in.");
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-4 font-sans dark:bg-black">
      <div className="w-full max-w-sm rounded-xl border border-black/[.08] bg-white p-8 shadow-sm dark:border-white/[.145] dark:bg-zinc-950">
        <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Sign in to ProcureFlow
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          Use your email and password.
        </p>

        <form onSubmit={handleSignIn} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-zinc-700 dark:text-zinc-300">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 outline-none focus:border-black/[.3] dark:border-white/[.2]"
              placeholder="you@example.com"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-zinc-700 dark:text-zinc-300">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 outline-none focus:border-black/[.3] dark:border-white/[.2]"
              placeholder="••••••••"
            />
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {message && <p className="text-sm text-emerald-600">{message}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 h-11 rounded-lg bg-foreground font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Please wait…" : "Sign in"}
          </button>
          <button
            type="button"
            onClick={handleSignUp}
            disabled={loading}
            className="h-11 rounded-lg border border-black/[.12] font-medium transition-colors hover:bg-black/[.04] disabled:opacity-50 dark:border-white/[.2] dark:hover:bg-white/[.06]"
          >
            Create account
          </button>
        </form>
      </div>
    </div>
  );
}
