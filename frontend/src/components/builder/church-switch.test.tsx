/**
 * One draft per church (F §4.6 key, F acceptance 10; S Testing
 * `church-switch.test.tsx`): the real `(signed-in)` and `(church)` layouts
 * around the builder, against the fake API. A switch remounts the builder
 * under the other church's key; switching back restores the first draft.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SignedInLayout from "@/app/(signed-in)/layout";
import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { storeChurchId } from "@/lib/church";
import { useDraft } from "@/lib/draft/context";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey } from "@/lib/draft/schema";
import { type RecordedRequest, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, churchProfile, DRAFT_NOW, lectionaryRoute, me, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

const GRACE = churchProfile();
const HOPE = churchProfile({ id: CHURCH_IDS.hope, name: "Hope", role: "member", timezone: "America/Chicago" });

function OccasionProbe() {
  const { draft, update } = useDraft();
  return (
    <div>
      <p>Draft for {draft.church_id === GRACE.id ? "Grace" : "Hope"}: {draft.readings.occasion || "empty"}</p>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest at Grace"))}>
        Type an occasion
      </button>
    </div>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("church switch keeps one draft per church", () => {
  it("shows the other church's own draft and restores the first on the way back", async () => {
    installFakeApi({
      "GET /me": me({ churches: [church(), church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" })] }),
      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === HOPE.id ? HOPE : GRACE),
      "GET /lectionary/readings": lectionaryRoute(), // no readings: the drafts keep what the test types
    });
    storeChurchId(GRACE.id);
    const { user } = renderWithProviders(
      <SignedInLayout>
        <ChurchLayout>
          <BuilderLayout>
            <OccasionProbe />
          </BuilderLayout>
        </ChurchLayout>
      </SignedInLayout>,
      { path: "/builder/readings" },
    );

    expect(await screen.findByText("Draft for Grace: empty")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Type an occasion" }));
    expect(screen.getByText("Draft for Grace: Harvest at Grace")).toBeInTheDocument();

    act(() => storeChurchId(HOPE.id));
    expect(await screen.findByText("Draft for Hope: empty")).toBeInTheDocument();
    // The switch unmounted Grace's builder, which wrote its draft at once.
    const graceStored = JSON.parse(window.localStorage.getItem(draftKey(USER_ID, GRACE.id)) ?? "null");
    expect(graceStored.readings.occasion).toBe("Harvest at Grace");

    act(() => storeChurchId(GRACE.id));
    expect(await screen.findByText("Draft for Grace: Harvest at Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(draftKey(USER_ID, HOPE.id))).not.toBeNull());
  });
});
