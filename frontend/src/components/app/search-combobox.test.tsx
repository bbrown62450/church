/**
 * `SearchCombobox` (F §4.9 item 5; slice 3 S Testing
 * `components/app/search-combobox.test.tsx`): opens on click, shows the
 * caller's results and hints, selects with the keyboard, and gives the row
 * back on Escape or when focus leaves.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { SearchCombobox, type SearchResult } from "./search-combobox";

type Item = { id: string; name: string };

const ITEMS: Item[] = Array.from({ length: 70 }, (_, i) => ({ id: `i${i}`, name: `Item ${String(i).padStart(2, "0")}` }));

/** The caller's rules: contains, at most 50, with the hints a hymn picker would give. */
function search(query: string): SearchResult<Item> {
  const q = query.trim().toLowerCase();
  const matches = ITEMS.filter((item) => item.name.toLowerCase().includes(q));
  const footer =
    q === "" ? [`Type to search ${ITEMS.length} items.`]
    : matches.length === 0 ? [`No items match “${query.trim()}”.`]
    : matches.length > 50 ? [`Showing 50 of ${matches.length}.`]
    : [];
  return { shown: matches.slice(0, 50), footer: q === "item 0" ? [...footer, "2 more are hidden."] : footer };
}

function Host({ onChange, onDismiss }: { onChange?: (item: Item) => void; onDismiss?: () => void }) {
  const [value, setValue] = useState<Item | null>(null);
  return (
    <>
      <SearchCombobox
        label="Opening hymn"
        items={ITEMS}
        search={search}
        itemKey={(item) => item.id}
        itemText={(item) => item.name}
        value={value}
        onValueChange={(item) => {
          setValue(item);
          onChange?.(item);
        }}
        placeholder="Search by title or number"
        onDismiss={onDismiss}
      />
      <button type="button">Elsewhere</button>
    </>
  );
}

describe("SearchCombobox", () => {
  it("opens on click and shows at most the caller's 50 with its hint", async () => {
    const user = userEvent.setup();
    render(<Host />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    expect(input).toHaveAttribute("placeholder", "Search by title or number");
    expect(screen.queryByRole("listbox")).toBeNull();
    await user.click(input);
    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(50);
    expect(screen.getByText("Type to search 70 items.")).toBeInTheDocument();
  });

  it("shows the caller's order and footers: no match, and hidden ones", async () => {
    const user = userEvent.setup();
    render(<Host />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 0");
    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option").map((o) => o.textContent)).toEqual(ITEMS.slice(0, 10).map((i) => i.name));
    expect(screen.getByText("2 more are hidden.")).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, "zzz");
    expect(screen.queryByRole("option")).toBeNull();
    expect(screen.getByText("No items match “zzz”.")).toBeInTheDocument();
  });

  it("selects with the keyboard and shows the chosen item's text", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 42");
    await screen.findByRole("option", { name: "Item 42" });
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ id: "i42", name: "Item 42" });
    expect(input).toHaveValue("Item 42");
  });

  it("highlights the top match as the user types, so Enter picks it", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 2");
    const options = await screen.findAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(ITEMS.slice(20, 30).map((i) => i.name));
    expect(options[0]).toHaveAttribute("data-highlighted");
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith({ id: "i20", name: "Item 20" });
    expect(input).toHaveValue("Item 20");
  });

  it("calls onDismiss on Escape and when focus leaves, but not when an option is clicked", async () => {
    const onDismiss = vi.fn();
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onDismiss={onDismiss} onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 07");
    await user.click(await screen.findByRole("option", { name: "Item 07" }));
    expect(onChange).toHaveBeenCalledWith({ id: "i7", name: "Item 07" });
    expect(onDismiss).not.toHaveBeenCalled();
    await user.click(input);
    await user.keyboard("{Escape}");
    expect(onDismiss).toHaveBeenCalledTimes(1);
    await user.click(input);
    // While the list is open the rest of the page is hidden from the accessibility tree, so find it by text.
    await user.click(screen.getByText("Elsewhere"));
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });

  it("keeps Tab from the field to its own ▾ button inside, and dismisses when Tab leaves the combobox", async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(<Host onDismiss={onDismiss} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.click(input);
    await user.keyboard("{Escape}"); // close the list, so Tab walks the page
    onDismiss.mockClear();
    await user.tab();
    const trigger = document.activeElement;
    expect(trigger?.tagName).toBe("BUTTON"); // the field's own ▾ button
    expect(trigger).toHaveAttribute("aria-haspopup", "listbox");
    expect(onDismiss).not.toHaveBeenCalled();
    await user.tab();
    expect(screen.getByRole("button", { name: "Elsewhere" })).toHaveFocus();
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
