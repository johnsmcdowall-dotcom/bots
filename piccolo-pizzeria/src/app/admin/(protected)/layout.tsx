import { redirect } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { LogoMark } from "@/components/brand/LogoMark";
import { getCurrentProfile } from "@/lib/data/auth";
import { isSupabaseConfigured } from "@/lib/config";

export default async function ProtectedAdminLayout({ children }: { children: React.ReactNode }) {
  if (!isSupabaseConfigured) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-char-900 px-4">
        <div className="w-full max-w-md rounded-3xl bg-cream-50 p-8 text-center shadow-2xl">
          <div className="mx-auto w-14">
            <LogoMark />
          </div>
          <div className="mt-6 flex items-center justify-center gap-2 text-fire-600">
            <AlertTriangle className="h-5 w-5" />
            <h1 className="font-display text-xl font-semibold">Supabase not connected</h1>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-char-600">
            The admin dashboard needs a Supabase project for authentication and to persist orders
            and menu changes. Add <code className="rounded bg-char-900/10 px-1">NEXT_PUBLIC_SUPABASE_URL</code>,{" "}
            <code className="rounded bg-char-900/10 px-1">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> and{" "}
            <code className="rounded bg-char-900/10 px-1">SUPABASE_SERVICE_ROLE_KEY</code> to your
            environment, run the migrations in <code className="rounded bg-char-900/10 px-1">supabase/</code>, and
            create your first admin user — see the README for step-by-step instructions.
          </p>
        </div>
      </div>
    );
  }

  const profile = await getCurrentProfile();

  if (!profile) {
    redirect("/admin/login");
  }

  return (
    <div className="flex min-h-dvh flex-col bg-cream-100 md:flex-row">
      <AdminSidebar profile={profile} />
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</main>
    </div>
  );
}
