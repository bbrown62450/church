"use client";

import { useRef } from "react";

import { Textarea } from "@/components/ui/textarea";
import { useAutosize } from "@/lib/use-autosize";

export const PROFILE_HELP = "How you pray, in a few sentences. The AI follows it whenever it writes your liturgy.";

/**
 * Settings → Prayers' voice profile (slice 6a-3b; prayer library spec "Voice
 * profile card"): the profile the liturgy writer follows, editable by owners
 * and admins and saved with the prayers (the page's one **Save**). Members
 * read it.
 */
export function VoiceProfileCard({
  value,
  admin,
  onChange,
  error,
}: {
  value: string;
  admin: boolean;
  onChange: (value: string) => void;
  error?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  const describedBy = ["voice-profile-help", error && "voice-profile-error"].filter(Boolean).join(" ");
  return (
    <section aria-labelledby="voice-profile-title" className="grid gap-2 rounded-lg border p-4">
      <h3 id="voice-profile-title" className="text-base font-medium">
        <label htmlFor="voice-profile">Voice profile</label>
      </h3>
      <Textarea
        id="voice-profile"
        ref={ref}
        value={value}
        readOnly={!admin}
        rows={5}
        className="max-h-[60vh] overflow-y-auto"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        onChange={(e) => onChange(e.target.value)}
      />
      <p id="voice-profile-help" className="text-sm text-muted-foreground">
        {PROFILE_HELP}
      </p>
      {error ? (
        <p id="voice-profile-error" role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}
