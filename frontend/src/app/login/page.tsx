"use client";

/**
 * `/login` (S Routing, proxy and login; F §4.3). Google sign-in through Supabase.
 *
 * - `?next=` is stored as the post-login path, only when `safeInternalPath`
 *   accepts it, just before Google starts; the `(signed-in)` layout follows it
 *   after `/auth/callback` lands on `/`. Without a valid `next` the stored path
 *   is left alone: a failed or cancelled sign-in comes back as
 *   `/login?error=auth` with no `next`, and must not lose `/join`
 *   (clarification 39).
 * - `?select_account=1` asks Google for its account chooser (the invite
 *   email-mismatch path, S Flow B).
 * - Mounting ends any sign-out in this tab (`endSignOut()`, clarification 21).
 */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { endSignOut } from "@/lib/auth";
import { storePostLoginPath } from "@/lib/post-login";
import { createClient } from "@/lib/supabase/client";
import { safeInternalPath } from "@/lib/urls";

function LoginForm() {
  const searchParams = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signInError = searchParams.get("error")
    ? "Sign-in didn't complete. Please try again."
    : null;

  async function signIn() {
    setBusy(true);
    setError(null);
    const next = safeInternalPath(searchParams.get("next"));
    if (next) storePostLoginPath(next);
    const selectAccount = searchParams.get("select_account") === "1";
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        ...(selectAccount ? { queryParams: { prompt: "select_account" } } : {}),
      },
    });
    if (error) {
      setError(error.message);
      setBusy(false);
    }
  }

  const message = error ?? signInError;

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Worship Service Builder</CardTitle>
        <CardDescription>Plan Sunday services with your church.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button className="w-full" onClick={signIn} disabled={busy}>
          {busy ? "Redirecting…" : "Sign in with Google"}
        </Button>
        {message && <p className="text-sm text-destructive">{message}</p>}
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  // Every sign-out ends on this page, so the flag comes down here: a browser
  // Back into a cached signed-in page then loads `/me` again instead of
  // showing the skeleton for good (clarification 21).
  useEffect(() => {
    endSignOut();
  }, []);

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
