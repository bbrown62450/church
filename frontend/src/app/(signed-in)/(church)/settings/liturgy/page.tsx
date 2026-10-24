"use client";

import { useState } from "react";

import { LeaveGuard } from "@/components/app/leave-guard";
import { AffirmationDefaultCard } from "@/components/settings/affirmation-default-card";
import { LiturgyPromptsPage } from "@/components/settings/liturgy-prompts-page";

/**
 * Settings → Liturgy: the church's default Affirmation of Faith (affirmation
 * spec), then the instructions the AI follows when it writes the liturgy
 * (slice 6a-3a; F §4.1). Each saves on its own; one leave guard covers both.
 */
export default function LiturgySettingsRoute() {
  const [affirmationDirty, setAffirmationDirty] = useState(false);
  const [promptsDirty, setPromptsDirty] = useState(false);
  return (
    <div className="grid gap-8">
      <AffirmationDefaultCard onDirtyChange={setAffirmationDirty} />
      <LiturgyPromptsPage onDirtyChange={setPromptsDirty} />
      <LeaveGuard when={affirmationDirty || promptsDirty} />
    </div>
  );
}
