import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  // The web manifest is fetched without the session cookie, so it must skip the sign-in redirect (Theme PR 1);
  // the dot is escaped and the name anchored, so only /manifest.webmanifest itself skips.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|manifest\\.webmanifest$|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
