import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TimezoneCombobox } from "./timezone-combobox";

// A fixed zone list (never the runner's): 70 filler ids plus three real ones, so the
// full list is over the 50-match cap and "new york" has exactly one match.
const FILLER = Array.from({ length: 70 }, (_, i) => `Test/Zone_${String(i).padStart(2, "0")}`);
const ZONES = ["America/Chicago", "America/New_York", "America/North_Dakota/New_Salem", ...FILLER];

const originalSupportedValuesOf = Object.getOwnPropertyDescriptor(Intl, "supportedValuesOf");

afterEach(() => {
  vi.restoreAllMocks();
  if (originalSupportedValuesOf) Object.defineProperty(Intl, "supportedValuesOf", originalSupportedValuesOf);
});

function stubZones(zones: string[]) {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(zones);
}

function removeSupportedValuesOf() {
  Object.defineProperty(Intl, "supportedValuesOf", { configurable: true, writable: true, value: undefined });
}

/** A controlled host, as the create form uses it. */
function Host({ initial = "", onChange }: { initial?: string; onChange?: (value: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <TimezoneCombobox
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange?.(next);
      }}
    />
  );
}

describe("TimezoneCombobox", () => {
  it("opens the zone list on click", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host initial="America/Chicago" />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveValue("America/Chicago");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    await user.click(input);

    expect(await screen.findByRole("listbox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "America/New York" })).toBeInTheDocument();
  });

  it("renders at most 50 matches with the Type to search hint", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host />);

    await user.click(screen.getByRole("combobox", { name: "Time zone" }));

    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(50);
    expect(screen.getByText("Type to search")).toBeInTheDocument();
  });

  it("finds America/New_York when typing new york (spaces for underscores)", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host />);
    // Keep this reference: while the list is open, Testing Library computes an empty
    // accessible name for the combobox, so a second getByRole by name would fail.
    const input = screen.getByRole("combobox", { name: "Time zone" });

    await user.type(input, "new york");

    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "America/New York",
    ]);
    expect(screen.queryByText("Type to search")).not.toBeInTheDocument();
    expect(screen.queryByText("No matching time zone.")).not.toBeInTheDocument();

    await user.clear(input);
    await user.type(input, "zzz");

    expect(screen.queryByRole("option")).not.toBeInTheDocument();
    expect(screen.getByText("No matching time zone.")).toBeInTheDocument();
  });

  it("calls onChange with the IANA id on keyboard selection", async () => {
    stubZones(ZONES);
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onChange={onChange} />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    await user.type(input, "new york");
    await screen.findByRole("option", { name: "America/New York" });
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("America/New_York");
    expect(input).toHaveValue("America/New York");
  });

  it("renders the error below the field and marks the input invalid", () => {
    stubZones(ZONES);
    render(<TimezoneCombobox value="" onChange={() => {}} error="Timezone is required." />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription(
      "Sets the default service date (the next Sunday in this time zone). Timezone is required.",
    );
    const helper = screen.getByText("Sets the default service date (the next Sunday in this time zone).");
    const error = screen.getByText("Timezone is required.");
    expect(helper.compareDocumentPosition(error) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("falls back to a plain text input with the same helper when Intl.supportedValuesOf is missing", async () => {
    removeSupportedValuesOf();
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TimezoneCombobox value="" onChange={onChange} id="church-timezone" />);

    const input = screen.getByRole("textbox", { name: "Time zone" });
    expect(input).toHaveAttribute("id", "church-timezone");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(input).toHaveAccessibleDescription("Sets the default service date (the next Sunday in this time zone).");
    expect(input).not.toHaveAttribute("aria-invalid");

    await user.type(input, "E");
    expect(onChange).toHaveBeenLastCalledWith("E");
  });

  it("shows a value that is not in the list as chosen, with the warning under the field (6a-1)", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<TimezoneCombobox value="Eastern" onChange={() => {}} warning="Timezone not recognized. Choose one from the list." />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveValue("Eastern");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAccessibleDescription(
      "Sets the default service date (the next Sunday in this time zone). Timezone not recognized. Choose one from the list.",
    );
    await user.click(input);
    expect(await screen.findByRole("option", { name: "Eastern", selected: true })).toBeInTheDocument();
  });
});
