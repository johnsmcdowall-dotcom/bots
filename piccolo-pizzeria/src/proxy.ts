import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { isSupabaseConfigured } from "@/lib/config";

/**
 * Pre-launch gate: while the main site (menu, ordering, Supabase/Stripe
 * integration) is still being finished, only /links should be reachable by
 * the public, so a QR code / social bio link can point at the real domain
 * today without exposing half-connected pages to real visitors.
 *
 * Defaults to ON (gated) whenever SITE_LIVE isn't explicitly "true" — a
 * missing or misconfigured env var fails safe into "still gated", never
 * into "accidentally public". Flip SITE_LIVE=true in the hosting
 * provider's environment variables when the main site is ready; nothing
 * in the codebase needs to change, and no page or route is deleted by
 * being gated — this only redirects requests to them.
 */
const SITE_LIVE = process.env.SITE_LIVE === "true";

const GATE_EXEMPT_PATHS = new Set(["/links"]);

function isGateExempt(pathname: string): boolean {
  if (GATE_EXEMPT_PATHS.has(pathname)) return true;
  // Staff must always be able to reach /admin, gate or no gate — this is
  // about what the *public* can see, not about locking out the owner.
  if (pathname.startsWith("/admin")) return true;
  // API routes aren't pages to redirect — gating them would turn a JSON
  // endpoint into a redirect response, which breaks callers rather than
  // hiding them. With the public UI gated there's nothing calling these
  // anyway; this just avoids a confusing failure mode if something does.
  if (pathname.startsWith("/api")) return true;
  // Static assets (images, icons, manifest, robots.txt, sitemap.xml, the
  // logo /links itself displays, Next's internal chunks, …) never have an
  // app-page-shaped pathname — they always end in a file extension. Real
  // page routes in this app never do, so this one check safely lets every
  // static file through without having to list each public/ path by hand.
  if (/\.[a-zA-Z0-9]+$/.test(pathname)) return true;
  return false;
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  if (!SITE_LIVE && !isGateExempt(pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/links";
    url.search = "";
    return NextResponse.redirect(url);
  }

  const isAdminRoute = pathname.startsWith("/admin");
  if (!isAdminRoute) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  if (!isSupabaseConfigured) {
    return response;
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        },
      },
    }
  );

  // Refresh the session so it doesn't expire mid-shift for admin/staff users.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isLoginRoute = pathname === "/admin/login";

  if (!isLoginRoute && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/admin/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isLoginRoute && user) {
    const url = request.nextUrl.clone();
    url.pathname = "/admin";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
