import { readFileSync } from "node:fs";

import { afterEach, describe, expect, it, vi } from "vitest";

import { docxFilename, downloadBlob, printedFilename, REVOKE_AFTER_MS, type DocumentVariant } from "./download";

type Case = { date: string; variant: DocumentVariant; display: string; filename: string };
const { cases } = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/docx_filenames.json", import.meta.url), "utf-8"),
) as { cases: Case[] };

describe("docxFilename (slice 5a; F §1.9)", () => {
  it("names each file as the server does (shared/docx_filenames.json)", () => {
    expect(cases).toHaveLength(8);
    for (const c of cases) expect(docxFilename(c.variant, c.date), c.date).toBe(c.filename);
  });
});

describe("printedFilename (printed bulletin PR 1)", () => {
  it("names the printed bulletin as the server does (printed_bulletin.printed_filename)", () => {
    expect(printedFilename("pdf", "2026-10-04")).toBe("printed_bulletin_October_04_2026.pdf");
    expect(printedFilename("docx", "2026-12-25")).toBe("printed_bulletin_December_25_2026.docx");
  });
});

describe("downloadBlob (slice 5a; F §1.9)", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("clicks a hidden download link and keeps the file's URL 5 minutes, so an iPhone's Download? sheet can wait", () => {
    vi.useFakeTimers();
    const link = { click: vi.fn(), remove: vi.fn() } as unknown as HTMLAnchorElement;
    const appendChild = vi.fn();
    vi.stubGlobal("document", { createElement: vi.fn(() => link), body: { appendChild } });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test/1");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    downloadBlob(new Blob(["PK"]), "worship_October_04_2026.docx");
    expect(link).toMatchObject({ href: "blob:test/1", download: "worship_October_04_2026.docx", hidden: true });
    expect(appendChild).toHaveBeenCalledWith(link);
    expect(link.click).toHaveBeenCalledOnce();
    expect(link.remove).toHaveBeenCalledOnce();
    expect(REVOKE_AFTER_MS).toBe(5 * 60_000);
    vi.advanceTimersByTime(REVOKE_AFTER_MS - 1);
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(revoke).toHaveBeenCalledWith("blob:test/1");
  });
});
