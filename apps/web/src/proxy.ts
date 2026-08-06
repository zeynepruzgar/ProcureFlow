import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Next.js 16'da eski "middleware.ts" -> "proxy.ts" olarak yeniden adlandirildi.
// Her istekte calisir ve iki isi var:
// 1) Supabase oturum cookie'lerini tazelemek (token suresi dolmasin).
// 2) Korumali sayfalar (ornek: /dashboard) icin iyimser (optimistic) yonlendirme.
//
// NOT: proxy tek basina bir "guvenlik siniri" DEGILDIR. Gercek dogrulama
// korumali sayfanin kendisinde (server component'te getUser + redirect) yapilir.
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isProtected = request.nextUrl.pathname.startsWith("/dashboard");
  if (!user && isProtected) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}

export const config = {
  // Statik dosyalar ve resimler disindaki tum yollarda calis.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
