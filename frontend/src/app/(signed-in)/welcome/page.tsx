"use client";

/**
 * Stub `/welcome` (slice 1a; S file map). It is the zero-church landing, so the
 * `(church)` layout's redirect never lands on a 404 between the 1a and 1b
 * merges. The header has no church switcher (there is no church to switch to)
 * but keeps the account menu, so a user with no church can still log out (S
 * behavior change 20). Slice 1b replaces this page with the Join and Create tabs.
 */
import { AppHeader } from "@/components/app/app-header";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSignOut } from "@/lib/auth";
import { useMeContext } from "@/lib/me-context";

export default function WelcomePage() {
  const me = useMeContext();
  const signOut = useSignOut();

  return (
    <div className="min-h-dvh">
      <AppHeader user={me.user} onSignOut={() => void signOut()} />
      <main className="mx-auto grid max-w-3xl gap-4 p-4">
        <Card>
          <CardHeader>
            <CardTitle>No church yet</CardTitle>
            <CardDescription>
              Creating or joining a church is coming in the next update.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    </div>
  );
}
