import { createBrowserClient } from "@supabase/ssr";
import { isSupabaseConfigured } from "@/lib/config";

let client: ReturnType<typeof createBrowserClient> | null = null;

/** Browser Supabase client (singleton). Returns `null` if not configured. */
export function getSupabaseBrowserClient() {
  if (!isSupabaseConfigured) return null;
  if (!client) {
    client = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return client;
}
