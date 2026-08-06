import { redirect } from "next/navigation";

import { SignOutButton } from "@/components/sign-out-button";
import { createClient } from "@/lib/supabase/server";

// Korumali sayfa (server component). Middleware zaten giris kontrolu yapar;
// burada ek olarak kullaniciyi ve profilini (rolunu) sunucuda okuyoruz.
export default async function DashboardPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  // Profil + rol (RLS: giris yapmis kullanici profilleri okuyabilir).
  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, role")
    .eq("id", user.id)
    .single();

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <header className="flex items-center justify-between border-b border-black/[.08] px-6 py-4 dark:border-white/[.145]">
        <span className="font-semibold tracking-tight">ProcureFlow</span>
        <SignOutButton />
      </header>

      <main className="mx-auto w-full max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Dashboard
        </h1>
        <p className="mt-1 text-zinc-500">You are signed in.</p>

        <dl className="mt-8 grid gap-px overflow-hidden rounded-xl border border-black/[.08] bg-black/[.06] text-sm dark:border-white/[.145] dark:bg-white/[.08] sm:grid-cols-2">
          <div className="bg-white p-4 dark:bg-zinc-950">
            <dt className="text-zinc-500">Email</dt>
            <dd className="mt-1 font-medium">{user.email}</dd>
          </div>
          <div className="bg-white p-4 dark:bg-zinc-950">
            <dt className="text-zinc-500">Name</dt>
            <dd className="mt-1 font-medium">{profile?.full_name ?? "—"}</dd>
          </div>
          <div className="bg-white p-4 dark:bg-zinc-950">
            <dt className="text-zinc-500">Role</dt>
            <dd className="mt-1">
              <span className="inline-flex rounded-full border border-black/[.08] px-2.5 py-0.5 font-medium dark:border-white/[.145]">
                {profile?.role ?? "unknown"}
              </span>
            </dd>
          </div>
          <div className="bg-white p-4 dark:bg-zinc-950">
            <dt className="text-zinc-500">User ID</dt>
            <dd className="mt-1 truncate font-mono text-xs text-zinc-400">{user.id}</dd>
          </div>
        </dl>
      </main>
    </div>
  );
}
