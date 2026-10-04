"use client";

/**
 * The cover pictures (printed bulletin PR 3b; `POST /bulletin-images`, `GET
 * /bulletin-images/{id}`, PR 3a).
 *
 * - `checkPicture(file)`: what the server would refuse, said before the
 *   upload starts (a JPEG or PNG, not empty, at most 10 MB), with the
 *   server's own words; null when it may go.
 * - `useUploadBulletinImage({ onStored, onFailed })`: the picture itself as
 *   the request body, with the choice it answers (`PictureUpload`);
 *   `onStored` gets the answer (its id goes in the draft, `setCover`) and
 *   `onFailed` the error. They are the mutation's own callbacks, not
 *   `mutate`'s, so they run even when the step is left while the picture
 *   uploads (TanStack Query drops `mutate`'s callbacks once the component
 *   unmounts; plan review I1).
 * - `useUploadingPicture()`: true while an upload for the active church is in
 *   flight, read from the mutation cache by the upload's key, so a step left
 *   and opened again still says "Uploading…" (PR 3b build review I1).
 * - `newChoice(draft)` and `isLatestChoice(draft, token)`: the member's
 *   latest choice for a draft (Choose, or Remove), kept for the tab's life,
 *   so only the upload of the latest choice is ever applied (build review I1).
 * - `useBulletinImage(id)`: the stored picture's bytes for the preview,
 *   fetched with the church's headers (an `<img>` cannot send them), kept
 *   for the session (an id never names other bytes).
 */
import { useIsMutating, useQuery } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { BulletinImage } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** `bulletin_image.MAX_UPLOAD_BYTES`. */
export const MAX_PICTURE_BYTES = 10 * 1024 * 1024;
/** `bulletin_image.TOO_LARGE_MESSAGE` and `NOT_A_PICTURE_MESSAGE`: the server's words. */
export const PICTURE_TOO_LARGE = "The picture is larger than 10 MB. Choose a smaller one.";
export const NOT_A_PICTURE = "Choose a JPEG or PNG picture.";
const TYPES = new Set(["image/jpeg", "image/png"]);

export function checkPicture(file: File): string | null {
  if (!TYPES.has(file.type) || file.size === 0) return NOT_A_PICTURE; // 0 bytes: an iCloud photo not downloaded yet
  if (file.size > MAX_PICTURE_BYTES) return PICTURE_TOO_LARGE;
  return null;
}

/** The upload's mutation key: one church's uploads, whichever step started them. */
export function uploadKey(churchId: string) {
  return ["bulletinImageUpload", churchId] as const;
}

/** What an upload answers: the draft it was chosen for (its id, `created_at` and date) and the choice's token. */
export type PictureChoice = { church: string; draft: string; created: string; date: string; token: number };
export type PictureUpload = { file: File; choice: PictureChoice };

// Kept outside any component, so a step left and opened again (a remount) still knows the latest choice.
const latestChoices = new Map<string, number>();
let lastToken = 0;

/** A new choice for `draft` (Choose, or Remove): an upload of an earlier choice is no longer applied. */
export function newChoice(draft: string): number {
  lastToken += 1;
  latestChoices.set(draft, lastToken);
  return lastToken;
}

export function isLatestChoice(draft: string, token: number): boolean {
  return latestChoices.get(draft) === token;
}

export function useUploadBulletinImage({
  onStored,
  onFailed,
}: {
  onStored: (stored: BulletinImage, upload: PictureUpload) => void;
  onFailed: (error: ApiError, upload: PictureUpload) => void;
}) {
  const api = useApi();
  const church = useChurch();
  return useChurchMutation<BulletinImage, ApiError, PictureUpload>({
    mutationKey: uploadKey(church.id),
    mutationFn: ({ file }) =>
      api.church<BulletinImage>("/bulletin-images", {
        method: "POST",
        init: { body: file, headers: { "Content-Type": file.type } },
      }),
    onSuccess: (stored, upload) => onStored(stored, upload),
    onError: (error, upload) => onFailed(error, upload),
  });
}

export function useUploadingPicture(): boolean {
  const church = useChurch();
  return useIsMutating({ mutationKey: uploadKey(church.id) }) > 0;
}

export function useBulletinImage(imageId: string | null) {
  const api = useApi();
  const church = useChurch();
  return useQuery<Blob, ApiError>({
    queryKey: keys.bulletinImage(church.id, imageId ?? ""),
    queryFn: async ({ signal }) => (await api.churchBlob(`/bulletin-images/${imageId}`, { signal })).blob,
    enabled: imageId !== null,
    staleTime: Infinity,
  });
}
