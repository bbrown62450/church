/**
 * Word files on this device (slice 5a spec, Library "download.ts"; F §1.9).
 *
 * - `docxFilename(variant, dateIso)`: the name the server gives
 *   (`service_output.docx_filename`), for a response without
 *   `Content-Disposition`; shared/docx_filenames.json keeps the two equal.
 * - `downloadBlob(blob, filename)`: an object URL clicked through a hidden
 *   `<a download>`; the URL is revoked after 5 minutes, since revoking at once
 *   breaks Safari and an iPhone's "Download?" sheet can wait for the member's
 *   answer. On iPhone this opens the share or preview sheet (accepted, owner
 *   answer 7, 2026-10-01).
 */
export type DocumentVariant = "bulletin" | "pastor";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const REVOKE_AFTER_MS = 5 * 60_000;

/** "2026-10-04" → "worship_October_04_2026.docx" (pastor: "worship_pastor_October_04_2026.docx"). */
export function docxFilename(variant: DocumentVariant, dateIso: string): string {
  const [year, month, day] = dateIso.split("-");
  const prefix = variant === "pastor" ? "worship_pastor_" : "worship_";
  return `${prefix}${MONTHS[Number(month) - 1]}_${day}_${year}.docx`;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  link.hidden = true;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
}
