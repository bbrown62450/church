"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/client";

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
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
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
  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
