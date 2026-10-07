import { createBrowserClient } from "@supabase/ssr";

/**
 * The browser's Supabase client. It never reads a sign-in from the address
 * bar (`detectSessionInUrl: false`, slice 5b-2): Google sends the Gmail
 * connection back to `/gmail/callback?code=…&state=…` (or `?error=…`), the
 * same names Supabase's own callbacks use, and the client would otherwise
 * post the Gmail code to Supabase. Sign-in does not need it: the server's
 * `/auth/callback` route exchanges Supabase's code.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { detectSessionInUrl: false } },
  );
}
