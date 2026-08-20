"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, ClipboardList, UtensilsCrossed, Clock, Settings, LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { LogoWordmark } from "@/components/brand/LogoWordmark";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";
import type { AdminProfile } from "@/lib/data/auth";

const LINKS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, adminOnly: false },
  { href: "/admin/orders", label: "Live Orders", icon: ClipboardList, adminOnly: false },
  { href: "/admin/menu", label: "Menu", icon: UtensilsCrossed, adminOnly: true },
  { href: "/admin/opening-hours", label: "Opening Hours", icon: Clock, adminOnly: true },
  { href: "/admin/settings", label: "Settings", icon: Settings, adminOnly: true },
];

function NavLinks({ profile, onNavigate }: { profile: AdminProfile; onNavigate?: () => void }) {
  const pathname = usePathname();
  const links = LINKS.filter((l) => !l.adminOnly || profile.role === "admin");

  return (
    <nav className="flex flex-1 flex-col gap-1">
      {links.map((link) => {
        const active = link.href === "/admin" ? pathname === "/admin" : pathname.startsWith(link.href);
        const Icon = link.icon;
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors",
              active ? "bg-fire-500 text-cream-50" : "text-cream-100/75 hover:bg-cream-50/10"
            )}
          >
            <Icon className="h-4 w-4" />
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AdminSidebar({ profile }: { profile: AdminProfile }) {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleSignOut() {
    const supabase = getSupabaseBrowserClient();
    await supabase?.auth.signOut();
    router.push("/admin/login");
    router.refresh();
  }

  return (
    <>
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-cream-100/10 bg-char-900 px-4 py-3 md:hidden">
        <LogoWordmark tone="light" className="h-8" />
        <button onClick={() => setMobileOpen(true)} className="p-2 text-cream-50" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="w-72 bg-char-900 p-5">
            <div className="flex items-center justify-between">
              <LogoWordmark tone="light" className="h-8" />
              <button onClick={() => setMobileOpen(false)} className="p-2 text-cream-50" aria-label="Close menu">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-6">
              <NavLinks profile={profile} onNavigate={() => setMobileOpen(false)} />
            </div>
            <button
              onClick={handleSignOut}
              className="mt-6 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-cream-100/75 hover:bg-cream-50/10"
            >
              <LogOut className="h-4 w-4" /> Sign Out
            </button>
          </div>
          <div className="flex-1 bg-char-900/60" onClick={() => setMobileOpen(false)} />
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col bg-char-900 p-5 md:flex">
        <LogoWordmark tone="light" className="h-9" />
        <div className="mt-3 rounded-xl bg-cream-50/5 px-3 py-2 text-xs text-cream-100/60">
          Signed in as <span className="font-semibold text-cream-100">{profile.email}</span>
          <span className="ml-1.5 rounded-full bg-fire-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-fire-400">
            {profile.role}
          </span>
        </div>
        <div className="mt-6 flex flex-1 flex-col">
          <NavLinks profile={profile} />
        </div>
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-cream-100/75 hover:bg-cream-50/10"
        >
          <LogOut className="h-4 w-4" /> Sign Out
        </button>
      </aside>
    </>
  );
}
