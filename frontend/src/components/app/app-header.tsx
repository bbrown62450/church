"use client";

import { AccountMenu } from "@/components/app/account-menu";
import { AppNav } from "@/components/app/app-nav";
import { ChurchSwitcher } from "@/components/app/church-switcher";
import type { Church, Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  churches?: Church[];
  active?: Church | null;
  onSelectChurch?: (id: string) => void;
  onSignOut: () => void;
};

/**
 * The signed-in header (F §4.2). With `churches` and `onSelectChurch` it shows
 * the church switcher and the primary nav (`AppNav`, slice 2): a link row
 * between the switcher and the account menu from `md`, a segmented row under
 * them below `md`. Without them (`/welcome`) it shows the app name and no nav.
 * The account menu is always there, so every signed-in screen can log out (S A6).
 */
export function AppHeader({ user, churches, active = null, onSelectChurch, onSignOut }: Props) {
  const showSwitcher = churches !== undefined && churches.length > 0 && onSelectChurch !== undefined;

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-2 md:grid-cols-[minmax(0,1fr)_auto_auto]">
        <div className="min-w-0">
          {showSwitcher ? (
            <ChurchSwitcher churches={churches} activeId={active?.id ?? null} onSelect={onSelectChurch} />
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>
        {showSwitcher ? (
          <AppNav className="col-span-2 row-start-2 md:col-span-1 md:col-start-2 md:row-start-1" />
        ) : null}
        <div className="col-start-2 row-start-1 md:col-start-3">
          <AccountMenu user={user} role={active?.role} onSignOut={onSignOut} />
        </div>
      </div>
    </header>
  );
}
