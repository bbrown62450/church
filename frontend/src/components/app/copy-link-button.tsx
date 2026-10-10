"use client";

import { CopyIcon } from "lucide-react";
import { useEffect, useRef, useState, type ComponentProps } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { copyText } from "@/lib/clipboard";

export const LINK_COPIED = "Link copied";
export const COPY_FAILED = "Couldn't copy. The link is selected; copy it from there.";
const COPIED_FOR_MS = 2000;

export type CopyLinkButtonProps = Omit<ComponentProps<typeof Button>, "onClick" | "children"> & {
  /** The link to copy. */
  text: string;
  /** When copying fails: show and select the link so the user can copy it themselves. */
  onCopyFailed(): void;
  /**
   * Screen readers' name when the visible label alone is not enough ("Copy link
   * for …"); dropped while "Copied ✓" shows, so the name follows the label.
   */
  label?: string;
};

/**
 * **Copy link** (6b spec UX 1a): copies `text`; on success the label reads
 * "Copied ✓" for 2 s and a toast says "Link copied"; when the browser refuses,
 * `onCopyFailed` selects the link and a toast says so.
 */
export function CopyLinkButton({ text, onCopyFailed, label, ...props }: CopyLinkButtonProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  async function onClick() {
    if (await copyText(text)) {
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), COPIED_FOR_MS);
      toast.success(LINK_COPIED);
    } else {
      onCopyFailed();
      toast.error(COPY_FAILED);
    }
  }

  return (
    <Button type="button" aria-label={copied ? undefined : label} {...props} onClick={() => void onClick()}>
      {copied ? null : <CopyIcon data-icon="inline-start" aria-hidden="true" />}
      {copied ? "Copied ✓" : "Copy link"}
    </Button>
  );
}
