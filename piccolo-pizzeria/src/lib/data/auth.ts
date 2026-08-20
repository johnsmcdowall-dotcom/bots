import "server-only";
import { getSupabaseServerClient } from "@/lib/supabase/server";

export interface AdminProfile {
  id: string;
  email: string;
  role: "admin" | "staff";
  fullName: string | null;
}

/** The current signed-in staff/admin user, or `null` if not signed in / not staff. */
export async function getCurrentProfile(): Promise<AdminProfile | null> {
  const supabase = await getSupabaseServerClient();
  if (!supabase) return null;

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data } = await supabase.from("profiles").select("*").eq("id", user.id).maybeSingle();
  const profile = data as { id: string; role: "admin" | "staff"; full_name: string | null } | null;
  if (!profile) return null;

  return { id: profile.id, email: user.email ?? "", role: profile.role, fullName: profile.full_name };
}
