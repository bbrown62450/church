import { act, render, renderHook, screen } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { churchProfile, DRAFT_NOW, testDraft, USER_ID } from "@/test/fixtures";

import { DRAFT_MESSAGES, DraftProvider, useDraft } from "./context";
import { editOccasion } from "./readings";
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

const GRACE = churchProfile();
const KEY = draftKey(USER_ID, GRACE.id);

function Probe() {
  const { draft, update, persistence } = useDraft();
  return (
    <div>
      <p>Occasion: {draft.readings.occasion || "none"}</p>
      <p>Persistence: {persistence}</p>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest"))}>
        Edit
      </button>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest Home"))}>
        Rename
      </button>
    </div>
  );
}

/** The Benediction card and the latest draft `peek` returns, for the liturgy defaults (slice 4b). */
function BenedictionProbe() {
  const { draft, peek } = useDraft();
  return (
    <div>
      <p>Benediction: {draft.liturgy.cards.benediction.text || "empty"}</p>
      <button type="button" onClick={() => window.alert(peek().liturgy.cards.benediction.text)}>
        Peek
      </button>
    </div>
  );
}

function renderProbe() {
  return render(
    <DraftProvider userId={USER_ID} church={GRACE}>
      <Probe />
    </DraftProvider>,
  );
}

function storedOccasion(): string | undefined {
  const raw = window.localStorage.getItem(KEY);
  return raw === null ? undefined : (JSON.parse(raw) as DraftV1).readings.occasion;
}

describe("DraftProvider and useDraft (F §4.6 Persistence)", () => {
  let toastError: MockInstance<typeof toast.error>;
  let toastWarning: MockInstance<typeof toast.warning>;
  let toastInfo: MockInstance<typeof toast.info>;

  beforeEach(() => {
    // The test drafts are dated for DRAFT_NOW (next Sunday October 4, 2026).
    // With the real clock, from October 5 the store would roll a pristine
    // draft forward with a real `updated_at`, newer than "the other tab's".
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(DRAFT_NOW);
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
    toastWarning = vi.spyOn(toast, "warning").mockImplementation(() => 0);
    toastInfo = vi.spyOn(toast, "info").mockImplementation(() => 0);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("fills the Benediction from the church profile, follows a new default, and peek reads the latest draft (slice 4b)", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const view = render(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "Go in peace." })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: Go in peace.")).toBeInTheDocument();
    view.rerender(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "" })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: empty")).toBeInTheDocument();
    act(() => screen.getByRole("button", { name: "Peek" }).click());
    expect(alert).toHaveBeenCalledWith("");
    // An older API without the field: the fallback.
    view.rerender(
      <DraftProvider userId={USER_ID} church={{ id: GRACE.id, timezone: GRACE.timezone }}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText(`Benediction: ${DEFAULT_BENEDICTION_FALLBACK}`)).toBeInTheDocument();
  });

  it("keeps peek, update and replace the same functions across edits, so callbacks built on them do not change per keystroke", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const { result } = renderHook(() => useDraft(), {
      wrapper: ({ children }) => (
        <DraftProvider userId={USER_ID} church={GRACE}>
          {children}
        </DraftProvider>
      ),
    });
    const first = result.current;
    act(() => first.update((d) => editOccasion(d, "Harvest")));
    act(() => first.update((d) => editOccasion(d, "Harvest Home")));
    expect(result.current.draft).not.toBe(first.draft);
    expect(result.current.peek).toBe(first.peek);
    expect(result.current.update).toBe(first.update);
    expect(result.current.replace).toBe(first.replace);
    expect(result.current.peek().readings.occasion).toBe("Harvest Home");
  });

  it("useDraft throws outside the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useDraft())).toThrow("useDraft() must be used inside <DraftProvider>.");
  });

  it("writes before the debounce when the page is hidden or left, and on unmount", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const { unmount } = renderProbe();
    const click = (name: string) => act(() => screen.getByRole("button", { name }).click());

    click("Edit");
    expect(screen.getByText("Occasion: Harvest")).toBeInTheDocument();
    expect(storedOccasion()).toBe(""); // the 400 ms write has not run yet
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(storedOccasion()).toBe("Harvest");

    click("Rename");
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    expect(storedOccasion()).toBe("Harvest Home");

    click("Edit");
    unmount(); // a church switch unmounts the provider
    expect(storedOccasion()).toBe("Harvest");
  });

  it("adopts a newer draft from another tab and says so", () => {
    const mine = testDraft();
    window.localStorage.setItem(KEY, JSON.stringify(mine));
    renderProbe();
    const theirs = { ...editOccasion(mine, "From the other tab"), updated_at: "2026-09-29T17:00:00.000Z" };
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: JSON.stringify(theirs) }));
    });
    expect(screen.getByText("Occasion: From the other tab")).toBeInTheDocument();
    expect(toastInfo).toHaveBeenCalledWith(DRAFT_MESSAGES.adopted, expect.anything());
    expect(DRAFT_MESSAGES.adopted).toBe("Updated from another tab.");
  });

  it("backs up a draft it cannot restore and toasts; a full or blocked storage keeps the draft in memory", () => {
    window.localStorage.setItem(KEY, "{broken");
    const first = renderProbe();
    expect(window.localStorage.getItem(corruptDraftKey(USER_ID, GRACE.id))).toBe("{broken");
    expect(toastError).toHaveBeenCalledWith("We couldn't restore your unsaved draft.", expect.anything());
    first.unmount();

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
    });
    renderProbe();
    act(() => screen.getByRole("button", { name: "Edit" }).click());
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(screen.getByText("Persistence: memory-only")).toBeInTheDocument();
    expect(screen.getByText("Occasion: Harvest")).toBeInTheDocument();
    expect(toastWarning).toHaveBeenCalledTimes(1);
    expect(toastWarning).toHaveBeenCalledWith(
      "This browser isn't saving your draft. Don't refresh or close this tab, or you'll lose your changes.",
      expect.anything(),
    );
  });
});
