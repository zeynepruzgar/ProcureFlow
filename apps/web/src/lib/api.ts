import { createClient } from "@/lib/supabase/client";

// Backend (FastAPI) taban adresi. Ortam degiskeninden gelir, yoksa local.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Tum API cagrilarinin gectigi tek yardimci.
// Supabase oturumundaki JWT'yi alip "Authorization: Bearer <token>" olarak ekler.
// Boylece backend, get_current_user ile kullaniciyi ve rolunu dogrulayabilir.
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    // Backend hata detayini ({ detail: "..." }) mesaja tasimaya calis.
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // govde JSON degilse varsayilan mesaj kalir
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
