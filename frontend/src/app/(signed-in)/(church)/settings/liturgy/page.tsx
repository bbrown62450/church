"use client";

import { LiturgyPromptsPage } from "@/components/settings/liturgy-prompts-page";

/** Settings → Liturgy: the instructions the AI follows when it writes the liturgy (slice 6a-3a; F §4.1). */
export default function LiturgySettingsRoute() {
  return <LiturgyPromptsPage />;
}
