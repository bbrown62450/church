"use client";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useChurch } from "@/lib/church-context";

/** Home (`/`): the slice-0 placeholder cards for the confirmed church (slice 2 makes `/` a redirect to `/builder`). */
export default function HomePage() {
  const church = useChurch();

  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>Service Builder</CardTitle>
          <CardDescription>
            Readings, hymns, and liturgy for {church.name} are coming soon. Until then, keep
            using the current app.
          </CardDescription>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>Church profile, members, and invites are coming later.</CardDescription>
        </CardHeader>
      </Card>
    </main>
  );
}
