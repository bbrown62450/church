"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";

export const DISCARD_TITLE = "Discard unsaved changes?";
const DISCARD_BODY = "Your changes on this page haven't been saved.";

type Leave = () => void;

/** The mounted guard while it has unsaved edits to protect (one settings page at a time), else null. */
let activeGuard: ((leave: Leave) => void) | null = null;

/**
 * For a way out of the page that is not a link (the church menu's "Join or
 * create a church…"): while a `LeaveGuard` has unsaved edits, `leave` runs
 * only after "Discard changes"; otherwise it runs at once.
 */
export function confirmLeave(leave: Leave): void {
  if (activeGuard !== null) activeGuard(leave);
  else leave();
}

/** The link a click would follow to another in-app page, or null when the click should go ahead as usual. */
function guardedLink(event: MouseEvent): { link: HTMLAnchorElement; href: string } | null {
  if (event.defaultPrevented || event.button !== 0) return null;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return null; // a new tab or window
  const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
  if (!(link instanceof HTMLAnchorElement) || link.hasAttribute("download")) return null;
  if (link.target !== "" && link.target !== "_self") return null;
  const url = new URL(link.href, window.location.href);
  // A blob: or data: URL can share the page's origin, but it is a file, not a page of the app.
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  if (url.origin !== window.location.origin) return null;
  if (url.pathname === window.location.pathname && url.search === window.location.search) return null;
  return { link, href: `${url.pathname}${url.search}${url.hash}` };
}

/**
 * 6a's leave guard for a settings form (slice 6a-1; the Bulletin settings
 * page's guard, moved here so every settings page shares it). While `when`
 * is true:
 * - closing or reloading the tab shows the browser's own warning;
 * - a plain click on any in-app link to another page (the settings nav, the
 *   header's nav, a page's own links) asks "Discard unsaved changes?" first:
 *   **Discard changes** goes on, **Keep editing** stays with the edits.
 * A modified or middle click opens the link as usual. After **Discard
 * changes** the link is clicked again with the guard standing aside, so its
 * own handler navigates as it would have (a `<Link replace>` replaces); a link
 * with no handler of its own goes on with `router.push`. "Join or create a
 * church…" asks through `confirmLeave`. The browser's Back and Forward
 * buttons, Log out and choosing another church in the church menu are not
 * covered.
 */
export function LeaveGuard({ when }: { when: boolean }) {
  const router = useRouter();
  const [leave, setLeave] = useState<Leave | null>(null);
  const standAside = useRef(false);

  useEffect(() => {
    if (!when) return;
    const ask = (next: Leave) => setLeave(() => next);
    activeGuard = ask;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = ""; // older Chrome and Edge, and some webviews, ask only when this is set
    };
    // Capture, on the document: runs before the link's own handler (Next's Link), which it stops.
    const intercept = (event: MouseEvent) => {
      if (standAside.current) return;
      const found = guardedLink(event);
      if (found === null) return;
      event.preventDefault();
      event.stopPropagation();
      ask(() => follow(found.link, found.href));
    };
    // The link again, its own handler included; when nothing handled it (a plain <a>), router.push.
    const follow = (link: HTMLAnchorElement, href: string) => {
      if (!link.isConnected) {
        router.push(href);
        return;
      }
      const fallback = (event: MouseEvent) => {
        if (event.defaultPrevented) return;
        event.preventDefault();
        router.push(href);
      };
      document.addEventListener("click", fallback, { once: true });
      standAside.current = true;
      try {
        link.click();
      } finally {
        standAside.current = false;
        document.removeEventListener("click", fallback);
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", intercept, true);
    return () => {
      if (activeGuard === ask) activeGuard = null;
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", intercept, true);
    };
  }, [when, router]);

  return (
    <ConfirmDialog
      open={leave !== null}
      onOpenChange={(open) => {
        if (!open) setLeave(null);
      }}
      title={DISCARD_TITLE}
      description={DISCARD_BODY}
      confirmLabel="Discard changes"
      cancelLabel="Keep editing"
      destructive
      onConfirm={() => {
        setLeave(null);
        leave?.();
      }}
    />
  );
}
