import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import { isSupabaseConfigured } from "@/lib/config";

/**
 * Server-side Supabase client bound to the current request's cookies, for
 * use in Server Components, Server Actions and Route Handlers. Returns
 * `null` when Supabase env vars aren't set so callers can fall back to seed
 * data (see `lib/data/*`) instead of the app crashing in local/demo mode.
 *
 * Deliberately untyped with the `Database` generic: the current
 * @supabase/supabase-js select-query-parser has a sharp edge where multiple
 * typed `.select("*")` calls in one file collapse to `never` (see
 * `lib/supabase/database.types.ts` for the full note). Row shapes are cast
 * explicitly in `lib/data/*` instead, using the hand-maintained Row types.
 */
export async function getSupabaseServerClient() {
  if (!isSupabaseConfigured) return null;

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
          try {
            cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          } catch {
            // Called from a Server Component render — safe to ignore because
            // middleware refreshes the session on the next request.
          }
        },
      },
    }
  );
}
