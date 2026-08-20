import "server-only";
import { getCurrentProfile, type AdminProfile } from "@/lib/data/auth";

export class UnauthorizedError extends Error {
  constructor(message = "Not authorized") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

/**
 * Every Server Action under /admin calls this first. Server Actions are
 * reachable by anyone who can POST to them directly — the protected layout's
 * redirect is a UX nicety, not a security boundary — so each action
 * re-verifies the caller's session and role itself.
 */
export async function requireStaff(): Promise<AdminProfile> {
  const profile = await getCurrentProfile();
  if (!profile) throw new UnauthorizedError();
  return profile;
}

export async function requireAdmin(): Promise<AdminProfile> {
  const profile = await requireStaff();
  if (profile.role !== "admin") throw new UnauthorizedError("Admin role required");
  return profile;
}
