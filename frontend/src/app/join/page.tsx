/**
 * `/join?code=…` (S Flow B, "Pages (1b)"; F §4.3): the public invite page.
 *
 * A Server Component, so it can export `metadata` (Next 16 allows it only in
 * Server Components). The client part reads `useSearchParams`, so it sits in
 * `<Suspense>`: without it `next build` fails for this static route.
 *
 * `referrer: "no-referrer"` (1b clarification 45): until the mount effect runs
 * `replaceState`, the address bar still holds the code, and no request this page
 * makes may carry it as a Referer.
 */
import type { Metadata } from "next";
import { Suspense } from "react";

import { JoinClient, JoinSkeleton } from "./join-client";

export const metadata: Metadata = {
  title: "Join a church",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function JoinPage() {
  return (
    <Suspense fallback={<JoinSkeleton />}>
      <JoinClient />
    </Suspense>
  );
}
