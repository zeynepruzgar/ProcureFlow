import { redirect } from "next/navigation";

import { DashboardNav } from "@/components/dashboard-nav";
import { SignOutButton } from "@/components/sign-out-button";
import { createClient } from "@/lib/supabase/server";

// Tum /dashboard/* sayfalarini saran ortak cerceve: baslik + navigasyon.
// Middleware zaten giris kontrolu yapar; burada ayrica dogruluyoruz.
export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <header className="border-b border-black/[.08] px-6 py-4 dark:border-white/[.145]">
        <div className="flex items-center justify-between">
          <span className="font-semibold tracking-tight">ProcureFlow</span>
          <SignOutButton />
        </div>
        <div className="mt-3">
          <DashboardNav />
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-6 py-10">{children}</main>
    </div>
  );
}
