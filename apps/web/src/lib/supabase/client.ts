import { createBrowserClient } from "@supabase/ssr";

// Tarayicida (client component) kullanilan Supabase istemcisi.
// Yalnizca public (anon) anahtari kullanir; RLS erisimi satir bazinda sinirlar.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
