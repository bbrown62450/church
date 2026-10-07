"use client";

import { GmailCallback } from "@/components/gmail/gmail-callback";

/**
 * `/gmail/callback`: where Google sends the browser back after Gmail's consent
 * screen (slice 5b-2; F §4.1). Signed in, outside the church shell: the Gmail
 * connection is the user's own, for every church.
 */
export default function GmailCallbackPage() {
  return <GmailCallback />;
}
