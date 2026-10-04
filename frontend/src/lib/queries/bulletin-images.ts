"use client";

/**
 * The cover pictures (printed bulletin PR 3b; `POST /bulletin-images`, `GET
 * /bulletin-images/{id}`, PR 3a).
 *
 * - `checkPicture(file)`: what the server would refuse, said before the
 *   upload starts (a JPEG or PNG, not empty, at most 10 MB), with the
 *   server's own words; null when it may go.
 * - `useUploadBulletinImage(onStored)`: the picture itself as the request
 *   body; `onStored` gets the answer (its id goes in the draft, `setCover`).
 *   It is the mutation's own callback, not `mutate`'s, so it runs even when
 *   the step is left while the picture uploads (TanStack Query drops
 *   `mutate`'s callbacks once the component unmounts; plan review I1).
 *   Errors are the caller's to show (on the step, next to the button).
 * - `useBulletinImage(id)`: the stored picture's bytes for the preview,
 *   fetched with the church's headers (an `<img>` cannot send them), kept
 *   for the session (an id never names other bytes).
 */
import { useQuery } from "@tanstack/react-query";

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

export function useUploadBulletinImage(onStored: (stored: BulletinImage) => void) {
  const api = useApi();
  return useChurchMutation<BulletinImage, ApiError, File>({
    mutationFn: (file) =>
      api.church<BulletinImage>("/bulletin-images", {
        method: "POST",
        init: { body: file, headers: { "Content-Type": file.type } },
      }),
    onSuccess: (stored) => onStored(stored),
  });
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
