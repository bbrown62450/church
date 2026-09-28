"use client";

/**
 * `/welcome` (S Flow A, Flow C; F §4.1): join or create a church. It is the
 * zero-church landing (the `(church)` layout sends users with no church here)
 * and the switcher's "Join or create a church…" target.
 *
 * - The header has no church switcher, but keeps the account menu, so a user
 *   with no church can still log out (S behavior change 20).
 * - The heading follows `me.churches`: the zero-church welcome, or "Join or
 *   create a church" with a "← Back to {active church}" link. The active
 *   church is the `(church)` layout's choice (`pickActiveChurch` over the
 *   stored id); the link waits until the stored id has been read.
 * - The tab comes from `?tab=join|create` (anything else is `join`). A tab
 *   change replaces the URL, so a refresh keeps the tab.
 * - The Join tab reads `wsb:pendingInviteCode` when it mounts: with a code it
 *   shows the info alert, prefills the field and previews automatically.
 *
 * `useSearchParams` sits inside `<Suspense>` (Next 16 needs the boundary for a
 * static build, 1b clarification 28). A `"use client"` page exports no
 * `metadata`; the root layout's title applies.
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { AppHeader } from "@/components/app/app-header";
import { CreateChurchForm } from "@/components/onboarding/create-church-form";
import { JoinInvite } from "@/components/onboarding/join-invite";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSignOut } from "@/lib/auth";
import { pickActiveChurch, useStoredChurchId, type Me } from "@/lib/church";
import { useMeContext } from "@/lib/me-context";
import { readSession, SESSION_KEYS } from "@/lib/storage";

type WelcomeTab = "join" | "create";

/** `?tab=` as a tab: `create` or `join`; anything else (missing, `foo`) is `join` (S Flow A). */
function parseTab(raw: unknown): WelcomeTab {
  return raw === "create" ? "create" : "join";
}

export default function WelcomePage() {
  const me = useMeContext();
  const signOut = useSignOut();

  return (
    <div className="min-h-dvh">
      <AppHeader user={me.user} onSignOut={() => void signOut()} />
      <main className="mx-auto grid max-w-md gap-6 px-4 py-6">
        <WelcomeHeading me={me} />
        <Suspense fallback={null}>
          <WelcomeTabs email={me.user.email} />
        </Suspense>
      </main>
    </div>
  );
}

function WelcomeHeading({ me }: { me: Me }) {
  const storedId = useStoredChurchId();
  const hasChurch = me.churches.length > 0;
  // `undefined` = the stored id is not read yet (hydration): no link until it is.
  const active = hasChurch && storedId !== undefined ? pickActiveChurch(me.churches, storedId) : null;

  return (
    <div className="grid gap-1">
      {active && (
        <Link
          href="/"
          className="inline-flex h-11 items-center self-start text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          ← Back to {active.name}
        </Link>
      )}
      <h1 className="text-2xl font-semibold">
        {hasChurch ? "Join or create a church" : "Welcome to Worship Service Builder"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {hasChurch
          ? `Signed in as ${me.user.email}.`
          : `Signed in as ${me.user.email}. You don't belong to a church yet.`}
      </p>
    </div>
  );
}

function WelcomeTabs({ email }: { email: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  // Local state, so the tab switches at once; the URL follows with replace (no history entry).
  const [tab, setTab] = useState<WelcomeTab>(() => parseTab(searchParams.get("tab")));

  function changeTab(value: unknown) {
    const next = parseTab(value);
    setTab(next);
    router.replace(`/welcome?tab=${next}`, { scroll: false });
  }

  return (
    <Tabs value={tab} onValueChange={changeTab}>
      <TabsList className="w-full group-data-horizontal/tabs:h-11">
        <TabsTrigger value="join">Join a church</TabsTrigger>
        <TabsTrigger value="create">Create a church</TabsTrigger>
      </TabsList>
      <TabsContent value="join" className="pt-2">
        <JoinTab email={email} />
      </TabsContent>
      <TabsContent value="create" className="pt-2">
        <CreateChurchForm />
      </TabsContent>
    </Tabs>
  );
}

function JoinTab({ email }: { email: string }) {
  // Read once per mount of the tab, never during a render on the server: the
  // `(signed-in)` layout renders children only after `/me` loads in the browser.
  // Re-reading on each mount means a code JoinInvite has cleared is not reused.
  const [pendingCode] = useState(() => readSession(SESSION_KEYS.pendingInviteCode));

  return (
    <div className="grid gap-4">
      {pendingCode && (
        <Alert>
          <AlertDescription>You opened an invite link. Review and accept it below.</AlertDescription>
        </Alert>
      )}
      <JoinInvite
        initialCode={pendingCode ?? undefined}
        autoPreview={Boolean(pendingCode)}
        email={email}
        showEntry
      />
    </div>
  );
}
