"use client";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSignOut } from "@/lib/auth";
import { useMeContext } from "@/lib/me-context";
import { useDisconnectGmail, useGmailConnection, useStartGmailConnect } from "@/lib/queries/gmail";
import { safeHttpsUrl } from "@/lib/urls";

export const SIGNED_IN_WITH_GOOGLE = "Signed in with Google.";
export const GMAIL_STATUS_ERROR = "Couldn't check your Gmail connection.";
export const GMAIL_NOT_CONFIGURED = "Per-user Gmail sending isn't configured on this deployment.";
export const GMAIL_INTRO =
  "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail.";
export const GMAIL_EVERY_CHURCH = "Works in all your churches.";
const ACCOUNT_PATH = "/settings/account";

/**
 * `/settings/account` (slice 5b spec, UX "/settings/account"; slice 5b-2): who
 * is signed in, with **Log out**, and the user's own Gmail connection, which
 * works in every church they belong to. Everyone sees the same page.
 */
export function AccountSettingsPage() {
  return (
    <section aria-labelledby="account-title" className="grid gap-4">
      <h2 id="account-title" className="text-lg font-semibold">
        Account
      </h2>
      <AccountCard />
      <GmailConnectionCard />
    </section>
  );
}

function AccountCard() {
  const { user } = useMeContext();
  const signOut = useSignOut();
  const name = user.name ?? user.email;
  const picture = safeHttpsUrl(user.picture);
  return (
    <div className="grid gap-4 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Avatar className="size-11">
          {picture ? <AvatarImage src={picture} alt="" /> : null}
          <AvatarFallback>{name.slice(0, 1).toUpperCase()}</AvatarFallback>
        </Avatar>
        <div className="grid min-w-0 gap-0.5">
          <p className="font-medium break-words">{name}</p>
          <p className="text-sm text-muted-foreground break-all">{user.email}</p>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{SIGNED_IN_WITH_GOOGLE}</p>
      <Button variant="outline" size="touch" className="w-full sm:w-fit" onClick={() => void signOut()}>
        Log out
      </Button>
    </div>
  );
}

/**
 * The Gmail card: loading, a failed check (Retry), not set up on this
 * deployment, not connected (**Connect Gmail**, which leaves for Google in
 * this tab and comes back here), connected (the address, **Disconnect**, no
 * confirmation: connecting again is one tap).
 */
function GmailConnectionCard() {
  const status = useGmailConnection();
  const start = useStartGmailConnect();
  const disconnect = useDisconnectGmail();
  let body;
  if (status.data) {
    const { configured, connected, google_email } = status.data;
    if (!configured) {
      body = <p className="text-sm">{GMAIL_NOT_CONFIGURED}</p>;
    } else if (connected) {
      body = (
        <>
          <div className="grid gap-1 text-sm">
            <p className="break-all">
              Connected as <strong>{google_email}</strong>.
            </p>
            <p className="text-muted-foreground">{GMAIL_EVERY_CHURCH}</p>
          </div>
          <PendingButton
            variant="outline"
            size="touch"
            className="w-full sm:w-fit"
            pending={disconnect.isPending}
            pendingLabel="Disconnecting…"
            onClick={() => disconnect.mutate()}
          >
            Disconnect
          </PendingButton>
        </>
      );
    } else {
      body = (
        <>
          <p className="text-sm">{GMAIL_INTRO}</p>
          <PendingButton
            size="touch"
            className="w-full sm:w-fit"
            pending={start.isPending}
            pendingLabel="Opening Google…"
            onClick={() => start.mutate({ returnTo: ACCOUNT_PATH })}
          >
            Connect Gmail
          </PendingButton>
        </>
      );
    }
  } else if (status.isError) {
    body = (
      <ErrorState
        message={GMAIL_STATUS_ERROR}
        error={status.error}
        onRetry={() => void status.refetch()}
        retrying={status.isFetching}
      />
    );
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }
  return (
    <section aria-labelledby="gmail-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="gmail-title" className="text-base font-medium">
        Gmail
      </h3>
      {body}
    </section>
  );
}
