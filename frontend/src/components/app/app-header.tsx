"use client";

import { AccountMenu } from "@/components/app/account-menu";
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
 * the church switcher; without them (the `/welcome` stub) it shows the app name.
 * The account menu is always there, so every signed-in screen can log out (S A6).
 */
export function AppHeader({ user, churches, active = null, onSelectChurch, onSignOut }: Props) {
  const showSwitcher = churches !== undefined && churches.length > 0 && onSelectChurch !== undefined;

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-2">
        <div className="min-w-0 flex-1">
          {showSwitcher ? (
            <ChurchSwitcher churches={churches} activeId={active?.id ?? null} onSelect={onSelectChurch} />
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>
        <AccountMenu user={user} role={active?.role} onSignOut={onSignOut} />
      </div>
    </header>
  );
}
