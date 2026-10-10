import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/lib/settings/people";

/**
 * A person's initials in a circle (6b spec "Every page"): never a picture,
 * since another person's picture address is theirs to edit. Hidden from
 * screen readers: the name is written beside it.
 */
export function InitialsAvatar({ name, email }: { name: string | null; email: string }) {
  return (
    <Avatar size="lg" aria-hidden="true">
      <AvatarFallback className="font-medium">{initials({ name, email })}</AvatarFallback>
    </Avatar>
  );
}
