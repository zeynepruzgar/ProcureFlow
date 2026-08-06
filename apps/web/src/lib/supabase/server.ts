import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

// Sunucu tarafinda (server component / route handler) kullanilan Supabase istemcisi.
// Oturumu cookie'ler uzerinden okur/yazar; boylece giris durumu sunucuda da bilinir.
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          // Server component'ten cagirildiginda cookie yazilamayabilir; bu durumda
          // sessizce gecilir (oturum tazeleme middleware'de yapilir).
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // ignore
          }
        },
      },
    },
  );
}
