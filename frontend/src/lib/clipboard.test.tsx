/** `copyText` (slice 6b-2a): the Clipboard API, the textarea fallback, and false when both fail. */
import { afterEach, describe, expect, it, vi } from "vitest";

import { copyText } from "./clipboard";

const realExecCommand = document.execCommand;

afterEach(() => {
  vi.unstubAllGlobals();
  document.execCommand = realExecCommand;
});

function stubClipboard(writeText: (text: string) => Promise<void>) {
  vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText: vi.fn(writeText) } });
  return navigator.clipboard.writeText as ReturnType<typeof vi.fn>;
}

describe("copyText (slice 6b-2a)", () => {
  it("copies with the Clipboard API", async () => {
    const writeText = stubClipboard(async () => {});
    document.execCommand = vi.fn(() => true);
    expect(await copyText("https://app.example/join?code=abc")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("https://app.example/join?code=abc");
    expect(document.execCommand).not.toHaveBeenCalled();
  });

  it("falls back to a hidden textarea when the Clipboard API refuses, and removes it again", async () => {
    stubClipboard(async () => {
      throw new DOMException("Not allowed", "NotAllowedError");
    });
    let copied = "";
    document.execCommand = vi.fn((command: string) => {
      copied = document.querySelector("textarea")?.value ?? "";
      return command === "copy";
    });
    expect(await copyText("the link")).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(copied).toBe("the link");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("says false, without throwing, when both ways fail", async () => {
    vi.stubGlobal("navigator", { ...navigator, clipboard: undefined });
    document.execCommand = vi.fn(() => false);
    expect(await copyText("the link")).toBe(false);
    document.execCommand = vi.fn(() => {
      throw new Error("unsupported");
    });
    expect(await copyText("the link")).toBe(false);
    expect(document.querySelector("textarea")).toBeNull();
  });
});
