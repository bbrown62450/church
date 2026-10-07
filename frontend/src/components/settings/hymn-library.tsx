"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Hymn, Hymnals } from "@/lib/api/types";
import { useHymnLibrary } from "@/lib/queries/hymn-library";
import { countLine, hymnLabel } from "@/lib/settings/hymns";

import { HymnDialog } from "./hymn-dialog";

export const LIBRARY_CAPTION = "Anyone in your church can add and edit hymns. Only admins can delete them.";
export const EMPTY_TITLE = "No hymns yet";
export const EMPTY_ADMIN = "Add hymns one at a time, or add a bundled hymnal above.";
export const EMPTY_MEMBER = "Add hymns one at a time, or ask an admin to add a bundled hymnal.";
/** How long typing waits before it searches (6a spec UX §2b). */
export const SEARCH_DEBOUNCE_MS = 300;

/** Which dialog is open: "add", or the hymn being edited. */
type Open = { key: "add" } | { key: string; hymn: Hymn };

/**
 * Settings → Hymns' "Hymn library" (slice 6a-2; 6a spec UX §2b): **Add hymn**,
 * a search by title or number (300 ms after typing stops), hymnal chips when
 * the church has several, the count, and the hymns 50 at a time in the
 * server's order with **Show more**. Each row opens **Edit hymn**.
 */
export function HymnLibrary({ admin, hymnals }: { admin: boolean; hymnals: Hymnals | undefined }) {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [chosen, setChosen] = useState<string | null>(null);
  const [open, setOpen] = useState<Open | null>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const searchBox = useRef<HTMLInputElement>(null);
  const codes = hymnals?.items.map((h) => h.code) ?? [];
  // A hymnal removed meanwhile is no longer a filter.
  const hymnal = chosen !== null && codes.includes(chosen) ? chosen : null;
  const library = useHymnLibrary({ hymnal, q });

  useEffect(() => {
    const timer = setTimeout(() => setQ(text.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text]);

  const clearSearch = () => {
    setText("");
    setQ("");
    searchBox.current?.focus();
  };

  const several = codes.length > 1;
  const pages = library.data?.pages;
  const items = pages?.flatMap((p) => p.items) ?? [];
  const total = pages?.[0]?.total ?? 0;

  let body;
  if (pages) {
    if (total === 0 && q !== "") {
      body = (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm">{`No hymns match “${q}”.`}</p>
          <Button type="button" variant="outline" size="touch" className="md:h-8" onClick={clearSearch}>
            Clear search
          </Button>
        </div>
      );
    } else if (total === 0) {
      body = <EmptyState title={EMPTY_TITLE} description={admin ? EMPTY_ADMIN : EMPTY_MEMBER} />;
    } else {
      body = (
        <>
          <p className="text-sm text-muted-foreground">{countLine(total, q !== "" || hymnal !== null)}</p>
          <ul className="divide-y rounded-lg border" aria-label="Hymns">
            {items.map((h) => (
              <li key={h.id}>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center gap-2 px-4 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring md:min-h-9"
                  onClick={() => setOpen({ key: h.id, hymn: h })}
                >
                  <span className="min-w-0 flex-1 break-words">{hymnLabel(h)}</span>
                  {several ? <Badge variant="outline">{h.hymnal}</Badge> : null}
                </button>
              </li>
            ))}
          </ul>
          {library.hasNextPage ? (
            <PendingButton
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit md:h-8"
              pending={library.isFetchingNextPage}
              pendingLabel="Loading…"
              onClick={() => void library.fetchNextPage()}
            >
              Show more
            </PendingButton>
          ) : null}
        </>
      );
    }
  } else if (library.isError) {
    body = <ErrorState error={library.error} onRetry={() => void library.refetch()} retrying={library.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="hymn-library-title" className="grid gap-3">
      <div className="grid gap-1">
        <h3 id="hymn-library-title" className="text-base font-medium">
          Hymn library
        </h3>
        <p className="text-sm text-muted-foreground">{LIBRARY_CAPTION}</p>
      </div>
      <Button ref={addButton} type="button" size="touch" className="w-full sm:w-fit md:h-8" onClick={() => setOpen({ key: "add" })}>
        Add hymn
      </Button>
      <div className="relative">
        <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={searchBox}
          type="search"
          aria-label="Search by title or number"
          placeholder="Search by title or number"
          value={text}
          className="h-11 pr-11 pl-9 md:h-9 [&::-webkit-search-cancel-button]:appearance-none"
          autoComplete="off"
          onChange={(event) => setText(event.target.value)}
        />
        {text !== "" ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute top-1/2 right-0 size-11 -translate-y-1/2 md:size-9"
            aria-label="Clear search"
            onClick={clearSearch}
          >
            <X aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      {several ? (
        <div role="group" aria-label="Hymnal" className="flex flex-wrap gap-2">
          {[null, ...codes].map((code) => (
            <Button
              key={code ?? "all"}
              type="button"
              variant={hymnal === code ? "default" : "outline"}
              size="touch"
              className="md:h-8"
              aria-pressed={hymnal === code}
              onClick={() => setChosen(code)}
            >
              {code ?? "All"}
            </Button>
          ))}
        </div>
      ) : null}
      {body}
      {open ? (
        <HymnDialog
          key={open.key}
          hymn={"hymn" in open ? open.hymn : null}
          codes={codes}
          defaultHymnal={hymnals?.effective_hymnal ?? codes[0] ?? ""}
          admin={admin}
          fallbackFocus={addButton}
          onClose={(key) => setOpen((current) => (current?.key === key ? null : current))}
        />
      ) : null}
    </section>
  );
}
