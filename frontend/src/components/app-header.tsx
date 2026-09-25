"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Church, Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  churches: Church[];
  active: Church | null;
  onSelectChurch: (church: Church) => void;
  onSignOut: () => void;
};

export function AppHeader({ user, churches, active, onSelectChurch, onSignOut }: Props) {
  const initial = (user.name ?? user.email).slice(0, 1).toUpperCase();

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          {churches.length > 0 ? (
            <Select
              items={churches.map((c) => ({ value: c.id, label: c.name }))}
              value={active?.id ?? ""}
              onValueChange={(id) => {
                const church = churches.find((c) => c.id === id);
                if (church) onSelectChurch(church);
              }}
            >
              <SelectTrigger className="w-full max-w-xs" aria-label="Active church">
                <SelectValue placeholder="Choose a church" />
              </SelectTrigger>
              <SelectContent>
                {churches.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Account menu"
            className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Avatar className="size-9">
              {user.picture && <AvatarImage src={user.picture} alt="" />}
              <AvatarFallback>{initial}</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="font-normal">
                <div className="text-sm font-medium">{user.name ?? user.email}</div>
                <div className="text-xs text-muted-foreground">{user.email}</div>
                {active && <div className="text-xs text-muted-foreground">Role: {active.role}</div>}
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onSignOut}>Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
