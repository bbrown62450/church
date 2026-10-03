/**
 * The builder shell (F §4.7, F acceptance 11; S "Builder shell", Testing
 * `builder-shell.test.tsx`; AC17). Every test fixes the clock at Tuesday,
 * September 29, 2026 (only `Date` is faked, so user-event's timers run), so a
 * fresh draft is dated Sunday, October 4, 2026. The lectionary answers "no
 * readings" unless a test says otherwise, so drafts keep their fields
 * (`lectionary-sync.test.tsx` tests the fill).
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BuilderIndexPage from "@/app/(signed-in)/(church)/builder/page";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import HymnsStepPage from "@/app/(signed-in)/(church)/builder/hymns/page";
import LiturgyStepPage from "@/app/(signed-in)/(church)/builder/liturgy/page";
import ReadingsStepPage from "@/app/(signed-in)/(church)/builder/readings/page";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setPick, setTranslation } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { addCustomElement, editCardText } from "@/lib/liturgy/cards";
import { installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  lectionary,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  sectionResult,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { StepProgress } from "./step-progress";
import { StillNeeded } from "./still-needed";
import { SummaryPanel } from "./summary-panel";

const KEY = draftKey(USER_ID, church().id);
const READINGS_SHIPPED = new Set(["readings"] as const);

function seed(draft: DraftV1): DraftV1 {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  return draft;
}

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

/** Shows what the shell's draft holds, as a step page would. */
function DraftProbe() {
  const { draft } = useDraft();
  return (
    <p>
      Probe: {draft.readings.occasion || "no occasion"} / {draft.save_key}
    </p>
  );
}

function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute(), routes: Record<string, FakeHandler> = {}) {
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lookup,
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    ...routes,
  });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>, { me: me(), church: church(), path });
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("builder shell (F §4.7)", () => {
  it("renders each step route inside the shell: progress, the step, and the footer links", async () => {
    const cases: [string, ReactElement, number, string, string[]][] = [
      ["/builder/readings", <ReadingsStepPage key="r" />, 1, "Date & readings", ["Next: Hymns"]],
      ["/builder/hymns", <HymnsStepPage key="h" />, 2, "Hymns", ["Back", "Next: Liturgy"]],
      ["/builder/liturgy", <LiturgyStepPage key="l" />, 3, "Liturgy", ["Back", "Next: Bulletin"]],
      ["/builder/bulletin", <BulletinStepPage key="b" />, 4, "Bulletin", ["Back", "Next: Review"]],
      ["/builder/review", <ReviewStepPage key="v" />, 5, "Review & send", ["Back"]],
    ];
    for (const [path, page, number, label, footer] of cases) {
      const { unmount } = renderBuilder(page, path);
      expect(await screen.findByRole("heading", { level: 1, name: "Service Builder" })).toBeInTheDocument();
      expect(screen.getByText(`Step ${number} of 5 · ${label}`)).toBeInTheDocument();

      const steps = within(screen.getByRole("navigation", { name: "Steps" })).getAllByRole("link");
      expect(steps.map((link) => link.textContent)).toEqual([
        "1 Date & readings 1 of 3", // shipped in 2c: a date, no occasion, no readings
        "2 Hymns 0 of 3", // shipped in 3b: no hymn chosen
        "3 Liturgy 1 of 7", // shipped in 4b: the Benediction follows the church default
        "4 Bulletin Optional", // shipped in printed bulletin PR 2b
        "5 Review & send Not in archive",
      ]);
      expect(steps.map((link) => link.getAttribute("href"))).toEqual([
        "/builder/readings",
        "/builder/hymns",
        "/builder/liturgy",
        "/builder/bulletin",
        "/builder/review",
      ]);
      expect(steps.filter((link) => link.getAttribute("aria-current") === "step")).toEqual([steps[number - 1]]);

      const card = await screen.findByRole("region", { name: label }); // Liturgy's shows once its config loads
      if (number === 1) {
        // Date & readings is the real step from slice 2c.
        expect(within(card).getByLabelText("Service date")).toHaveValue("2026-10-04");
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 2) {
        // Hymns is the real step from slice 3b.
        expect(within(card).getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 3) {
        // Liturgy is the real step from slice 4b.
        expect(await within(card).findByRole("textbox", { name: "Sermon title" })).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 4) {
        // Bulletin is the real step from printed bulletin PR 2b.
        expect(within(card).getByRole("textbox", { name: "Prelude title" })).toBeInTheDocument();
      } else {
        // Review & send is the real step from slice 5a-1: Still to do, the Archive card (5a-3), the Word documents.
        expect(within(card).getByRole("heading", { name: "Word documents" })).toBeInTheDocument();
        expect(within(card).getByRole("button", { name: "Save to archive" })).toBeEnabled();
        expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      }

      const links = within(screen.getByRole("navigation", { name: "Step navigation" })).getAllByRole("link");
      expect(links.map((link) => link.textContent)).toEqual(footer);
      // Review lists what the shipped steps still need; the other steps do not.
      if (number === 5) {
        const needed = screen.getByRole("region", { name: "Still to do" });
        expect(within(needed).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
          "No occasion — Add one",
          "No scripture readings — Add one",
          "No Opening hymn — Choose one",
          "No Response hymn — Choose one",
          "No Closing hymn — Choose one",
          "Call to Worship is empty — Write or generate it",
          "Opening Prayer is empty — Write or generate it",
          "Prayer of Confession is empty — Write or generate it",
          "Assurance of Pardon is empty — Write or generate it",
          "Prayer for Illumination is empty — Write or generate it",
          "Offertory Prayer is empty — Write or generate it",
          "No sermon title — Add one",
        ]);
        const links = within(needed).getAllByRole("link").map((link) => link.getAttribute("href"));
        expect(links).toEqual([
          "/builder/readings",
          "/builder/readings",
          "/builder/hymns",
          "/builder/hymns",
          "/builder/hymns",
          "/builder/liturgy#card-call_to_worship",
          "/builder/liturgy#card-opening_prayer",
          "/builder/liturgy#card-prayer_of_confession",
          "/builder/liturgy#card-assurance",
          "/builder/liturgy#card-prayer_for_illumination",
          "/builder/liturgy#card-offertory_prayer",
          "/builder/liturgy",
        ]);
      } else {
        expect(screen.queryByRole("heading", { name: "Still to do" })).toBeNull();
      }

      // The frame fills what the header leaves (the (church) layout's flex column), with no hard-coded header height.
      const main = screen.getByRole("main");
      const column = main.parentElement;
      expect(column).toHaveClass("flex", "flex-1", "flex-col");
      expect(column?.parentElement).toHaveClass("flex", "flex-1", "flex-col");
      expect(`${column?.className} ${column?.parentElement?.className}`).not.toMatch(/dvh/);
      // One landmark holds the heading, the progress and the step; the footer follows it. The main
      // grows (flex-1), so on a short step the sticky footer rests at the bottom of the viewport.
      expect(within(main).getByRole("heading", { level: 1, name: "Service Builder" })).toBeInTheDocument();
      expect(within(main).getByRole("navigation", { name: "Steps" })).toBeInTheDocument();
      expect(within(main).getByRole("region", { name: label })).toBeInTheDocument();
      expect(main).toHaveClass("flex-1");
      const footerNav = screen.getByRole("navigation", { name: "Step navigation" });
      expect(main.contains(footerNav)).toBe(false);
      expect(main.nextElementSibling).toBe(footerNav);
      expect(footerNav).toHaveClass("sticky", "bottom-0");
      // Back keeps the outline border: its classes are merged, not concatenated.
      for (const link of within(footerNav).getAllByRole("link")) {
        if (link.textContent === "Back") expect(link.className.split(/\s+/)).not.toContain("border-transparent");
      }
      unmount();
    }
  });

  it("shows the summary: the date and occasion, the readings, the hymns, the liturgy, and where the draft is kept", async () => {
    // A controllable (min-width: 64rem) query, so the test can widen the window past lg.
    const wide = { matches: false, listeners: new Set<() => void>() };
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          get matches() {
            return query === "(min-width: 64rem)" && wide.matches;
          },
          media: query,
          addEventListener: (_: string, listener: () => void) => wide.listeners.add(listener),
          removeEventListener: (_: string, listener: () => void) => wide.listeners.delete(listener),
        }) as unknown as MediaQueryList,
    );
    const { user, unmount } = renderBuilder(<HymnsStepPage />, "/builder/hymns");
    const aside = await screen.findByRole("complementary", { name: "Summary" });
    expect(within(aside).getByRole("heading", { level: 2, name: "Summary" })).toHaveClass("sr-only");
    // The sticky column clears the header's measured height (AppHeader sets --app-header-h).
    expect(aside.firstElementChild).toHaveClass("sticky", "top-[var(--app-header-h,4rem)]", "py-4");
    for (const block of ["Date", "Readings", "Hymns", "Liturgy"]) {
      // 44px tap targets on phones (the sheet), compact from lg.
      expect(within(aside).getByRole("link", { name: block })).toHaveClass(
        "inline-flex",
        "min-h-11",
        "min-w-11",
        "items-center",
        "lg:min-h-0",
        "lg:min-w-0",
      );
    }
    expect(within(aside).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(within(aside).getByText("No occasion yet")).toBeInTheDocument();
    const readings = within(aside).getByRole("link", { name: "Readings" }).closest("h3");
    expect(readings?.nextElementSibling).toHaveTextContent(/^No readings yet$/);
    const hymnsBlock = within(aside).getByRole("link", { name: "Hymns" }).closest("h3");
    expect(hymnsBlock?.nextElementSibling).toHaveTextContent(/^No Opening hymnNo Response hymnNo Closing hymn$/);
    const liturgy = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3");
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^1 of 7 liturgy sections readyCommunion: YesNo custom elements$/);
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
    const archive = within(aside).getByRole("link", { name: "Not in archive" }); // only the archive half links (build review M5)
    expect(archive).toHaveAttribute("href", "/builder/review");
    expect(archive.closest("p")).toHaveTextContent(/^Draft saved on this device · Not in archive$/);

    // Below lg the same panel opens in a bottom sheet from "Summary".
    await user.click(screen.getByRole("button", { name: "Summary" }));
    const sheet = await screen.findByRole("dialog", { name: "Summary" });
    expect(within(sheet).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(within(sheet).getByRole("link", { name: "Not in archive" }).closest("p")).toHaveTextContent("Draft saved on this device · Not in archive");
    // The sheet only shows below lg, so its Close is a 44 px square throughout.
    expect(within(sheet).getByRole("button", { name: "Close" })).toHaveClass("size-11");
    await user.click(within(sheet).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

    // Widening past lg while the sheet is open closes it, so no backdrop is left over the page.
    await user.click(screen.getByRole("button", { name: "Summary" }));
    await screen.findByRole("dialog", { name: "Summary" });
    act(() => {
      wide.matches = true;
      for (const listener of wide.listeners) listener();
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(wide.listeners.size).toBeGreaterThan(0);
    unmount();
    expect(wide.listeners.size).toBe(0);
  });

  it("writes last_step on entry without touching updated_at, and /builder opens that step", async () => {
    const saved = seed(testDraft());
    const first = renderBuilder(<HymnsStepPage />, "/builder/hymns");
    await screen.findByRole("heading", { level: 1, name: "Service Builder" });
    await waitFor(() => expect(stored().last_step).toBe("hymns"));
    expect(stored().updated_at).toBe(saved.updated_at);
    first.unmount();

    renderBuilder(<BuilderIndexPage />, "/builder");
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/builder/hymns"));
    expect(screen.queryByRole("navigation", { name: "Steps" })).toBeNull();
    expect(stored().updated_at).toBe(saved.updated_at);
  });

  it("New service resets a draft with nothing to lose at once, then opens Date & readings", async () => {
    const saved = seed(testDraft());
    const { user } = renderBuilder(<DraftProbe />, "/builder/liturgy");
    expect(await screen.findByText(`Probe: no occasion / ${saved.save_key}`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(screen.queryByText(`Probe: no occasion / ${saved.save_key}`)).toBeNull();
    expect(screen.getByText(/^Probe: no occasion \//)).toBeInTheDocument();
  });

  it("New service asks first when the draft has something to lose; Cancel keeps it, confirming clears it", async () => {
    const saved = seed(setTranslation(editOccasion(testDraft(), "Harvest Sunday"), "kjv", "web"));
    const { user } = renderBuilder(<DraftProbe />, "/builder/review");
    expect(await screen.findByText(`Probe: Harvest Sunday / ${saved.save_key}`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    let dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    expect(within(dialog).getByText("This clears the current draft on this device.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByText(`Probe: Harvest Sunday / ${saved.save_key}`)).toBeInTheDocument();
    expect(testRouter.push).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    await user.click(within(dialog).getByRole("button", { name: "Start new service" }));
    expect(await screen.findByText(/^Probe: no occasion \//)).toBeInTheDocument();
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    await waitFor(() => expect(stored().save_key).not.toBe(saved.save_key));
    expect(stored().readings.occasion).toBe("");
    expect(stored().readings.translation).toBe("kjv"); // the chosen translation stays (owner answer A)

    // The kept translation alone is nothing to lose, so the next New service resets at once.
    const before = stored().save_key;
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    await waitFor(() => expect(stored().save_key).not.toBe(before));
  });

  it("shows the builder skeleton until the church profile loads", async () => {
    installFakeApi({
      "GET /church": async () => churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /translations": translations(),
    });
    renderWithProviders(
      <BuilderLayout>
        <ReadingsStepPage />
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/readings" },
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Service Builder" })).toBeInTheDocument();
  });
});

describe("the shell with Date & readings shipped (slice 2c)", () => {
  it("counts the step Complete once the lectionary fills it, and the summary shows the readings with their chips", async () => {
    renderBuilder(<ReadingsStepPage />, "/builder/readings", lectionaryRoute(lectionary));
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    await waitFor(() =>
      expect(within(progress).getAllByRole("link")[0]).toHaveTextContent("1 Date & readings Complete"),
    );
    const aside = screen.getByRole("complementary", { name: "Summary" });
    expect(within(aside).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    const readingsBlock = within(aside).getByRole("link", { name: "Readings" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(readingsBlock).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Isaiah 5:1-7OT (auto)",
      "Psalm 80:7-15",
      "Philippians 3:4b-14NT (auto)",
      "Matthew 21:33-46",
    ]);
  });

  it("shows the readings status, Still to do, the occasion and the bulletin chips", async () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    seed(setPick(filled, "nt", "Matthew 21:33-46"));
    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /translations": translations(),
    });
    renderWithProviders(
      <BuilderLayout>
        <StepProgress current="readings" shipped={READINGS_SHIPPED} />
        <StillNeeded shipped={READINGS_SHIPPED} />
        <section aria-label="Shipped summary">
          <SummaryPanel shipped={READINGS_SHIPPED} />
        </section>
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/readings" },
    );

    const progress = (await screen.findAllByRole("navigation", { name: "Steps" }))[1];
    expect(within(progress).getAllByRole("link")[0]).toHaveTextContent("1 Date & readings Complete");
    // Nothing missing (slice 5a-3: the checklist says so).
    expect(screen.getByRole("region", { name: "Still to do" })).toHaveTextContent("Still to doEverything's ready.");

    const summary = screen.getByRole("region", { name: "Shipped summary" });
    expect(within(summary).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    const rows = within(summary).getAllByRole("listitem").map((li) => li.textContent);
    expect(rows).toEqual(["Isaiah 5:1-7OT (auto)", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46NT"]);
  });

  it("lists what is missing, each linking to its step", async () => {
    seed(testDraft());
    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /translations": translations(),
    });
    renderWithProviders(
      <BuilderLayout>
        <StillNeeded shipped={READINGS_SHIPPED} />
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/review" },
    );
    const section = await screen.findByRole("region", { name: "Still to do" });
    expect(within(section).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "No occasion — Add one",
      "No scripture readings — Add one",
    ]);
    for (const link of within(section).getAllByRole("link")) expect(link).toHaveAttribute("href", "/builder/readings");
  });
});

describe("the shell with Hymns shipped (slice 3b)", () => {
  it("counts Hymns n of 3, then Complete, and the summary lists the three slots in the column and the sheet", async () => {
    const [, praise, come, grace] = gg2013();
    seed(setSlot(setSlot(testDraft(), "opening", pickFromHymn(come)), "closing", pickFromHymn(praise)));
    function FillResponse() {
      const { update } = useDraft();
      return (
        <button type="button" onClick={() => update((d) => setSlot(d, "response", pickFromHymn(grace)))}>
          Fill Response
        </button>
      );
    }
    const { user } = renderBuilder(
      <>
        <ReviewStepPage />
        <FillResponse />
      </>,
      "/builder/review",
    );
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[1]).toHaveTextContent("2 Hymns 2 of 3");
    const aside = screen.getByRole("complementary", { name: "Summary" });
    const hymnsBlock = within(aside).getByRole("link", { name: "Hymns" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(hymnsBlock).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Opening · #403 Come, Thou Almighty King",
      "No Response hymn",
      "Closing · #35 Praise, My Soul, the King of Heaven",
    ]);
    expect(within(aside).getByRole("link", { name: "Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(hymnsBlock).not.toHaveTextContent("Available soon");
    const needed = screen.getByRole("region", { name: "Still to do" });
    expect(within(needed).getAllByRole("listitem").map((li) => li.textContent)).toContain("No Response hymn — Choose one");

    await user.click(screen.getByRole("button", { name: "Fill Response" }));
    await waitFor(() => expect(within(progress).getAllByRole("link")[1]).toHaveTextContent("2 Hymns Complete"));
    expect(within(needed).queryByText(/hymn — Choose one/)).toBeNull();
    // Below lg the same rows show in the bottom sheet.
    await user.click(screen.getByRole("button", { name: "Summary" }));
    const sheet = await screen.findByRole("dialog", { name: "Summary" });
    expect(within(sheet).getByText("Response · #649 Amazing Grace")).toBeInTheDocument();
    expect(within(sheet).getByText("Opening · #403 Come, Thou Almighty King")).toBeInTheDocument();
  });
});

describe("the shell with Liturgy shipped (slice 4b)", () => {
  it("counts the liturgy, lists it in the summary with the sections being written, and in Still to do", async () => {
    let d = editCardText(testDraft(), "call_to_worship", "Come, let us worship.");
    d = addCustomElement(d, { label: "Anthem", text: "", insert_after: "sermon" }, "a");
    seed({ ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "user" } });
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const view = renderBuilder(<LiturgyStepPage />, "/builder/liturgy", lectionaryRoute(), {
      "POST /liturgy/generate": async (req: RecordedRequest) => {
        await held;
        return { results: [sectionResult((req.body as { sections: ["opening_prayer"] }).sections[0], "Gracious God")] };
      },
    });
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[2]).toHaveTextContent("3 Liturgy 2 of 7");
    const aside = screen.getByRole("complementary", { name: "Summary" });
    const block = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(block).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "2 of 7 liturgy sections ready",
      "Communion: No",
      "1 custom element",
    ]);
    expect(within(aside).getByRole("link", { name: "Liturgy" })).toHaveAttribute("href", "/builder/liturgy");
    expect(block).not.toHaveTextContent("Available soon");

    // While a section is written the first line says so, and the line goes when it is done.
    const opening = await screen.findByRole("region", { name: "Opening Prayer" });
    await view.user.click(within(opening).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(block).toHaveTextContent("2 of 7 liturgy sections ready · Writing 1 section…"));
    release();
    await waitFor(() => expect(within(block).getAllByRole("listitem")[0]).toHaveTextContent(/^3 of 7 liturgy sections ready$/));
    expect(within(progress).getAllByRole("link")[2]).toHaveTextContent("3 Liturgy 3 of 7");
    view.unmount();

    renderBuilder(<ReviewStepPage />, "/builder/review");
    const needed = await screen.findByRole("region", { name: "Still to do" });
    const liturgyRows = within(needed)
      .getAllByRole("listitem")
      .map((li) => li.textContent)
      .filter((text) => /empty|sermon/.test(text ?? ""));
    expect(liturgyRows).toEqual([
      "Prayer of Confession is empty — Write or generate it",
      "Assurance of Pardon is empty — Write or generate it",
      "Prayer for Illumination is empty — Write or generate it",
      "Offertory Prayer is empty — Write or generate it",
      "No sermon title — Add one",
    ]);
    const hrefs = within(needed)
      .getAllByRole("link", { name: "Write or generate it" })
      .map((link) => link.getAttribute("href"));
    expect(hrefs[0]).toBe("/builder/liturgy#card-prayer_of_confession");
    expect(within(needed).getAllByRole("link", { name: "Add one" }).at(-1)).toHaveAttribute("href", "/builder/liturgy");
  });
});
