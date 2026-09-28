import { Skeleton } from "@/components/ui/skeleton";

/**
 * The app shell's shape while a layout waits: a header bar and two cards
 * (F §4.8 "Loading"). The `(signed-in)` layout shows it while `/me` loads, a
 * sign-out runs or a post-login redirect leaves; the `(church)` layout shows it
 * until the stored church is read. It is one `role="status"` region named
 * "Loading", so screen readers announce it and tests find it by role and name
 * (1a minor T23-m3: one skeleton for both layouts).
 */
export function ShellSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="ml-auto size-9 rounded-full" />
        </div>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
