"use client";

import { useId, useRef, useState, type ReactNode } from "react";

import {
  Combobox,
  ComboboxContent,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type SearchResult<T> = {
  /** What the list shows for the query, best first (the caller caps it, F §4.9 item 5). */
  shown: readonly T[];
  /** Hint lines under the list ("Type to search 853 hymns.", "No hymns match …"). */
  footer: readonly string[];
};

export type SearchComboboxProps<T> = {
  label: string;
  /** Hide the label visually (a card heading already names the field); it stays the input's name. */
  labelHidden?: boolean;
  /** Every item; `search` picks what shows. */
  items: readonly T[];
  search: (query: string) => SearchResult<T>;
  itemKey: (item: T) => string;
  /** The text for the input once an item is chosen, and the option's name. */
  itemText: (item: T) => string;
  /** The option's content; defaults to `itemText`. */
  renderItem?: (item: T) => ReactNode;
  value: T | null;
  onValueChange: (item: T) => void;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  /**
   * Escape, or focus leaving the combobox ("Change" puts the row back). Focus
   * moving between the field, its own ▾ button and its list stays inside, so
   * Tab from the field lands on ▾ with the combobox still there.
   */
  onDismiss?: () => void;
  id?: string;
};

/**
 * A searchable long list (F §4.9 item 5; slice 3's hymn picker). The caller
 * filters and ranks (`search`), so the list shows exactly its order; Base UI
 * only renders the items it is given (`filteredItems`) and handles focus,
 * highlight and keyboard selection; the first row is highlighted as the user
 * types, so Enter picks the top match. The footer holds the caller's hints.
 */
export function SearchCombobox<T>({
  label,
  labelHidden = false,
  items,
  search,
  itemKey,
  itemText,
  renderItem,
  value,
  onValueChange,
  placeholder,
  disabled = false,
  autoFocus = false,
  onDismiss,
  id,
}: SearchComboboxProps<T>) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  // What the user has typed since the list opened ("" = nothing yet).
  const [query, setQuery] = useState("");
  const result = search(query);
  const wrapperRef = useRef<HTMLDivElement>(null);

  return (
    // The wrapper sees the blur and Escape of the field and of ▾; the list's are
    // seen too (React events bubble through its portal). Escape is caught on the
    // way down: Base UI stops it once it has closed an open list.
    <div
      ref={wrapperRef}
      className="grid gap-1.5"
      onKeyDownCapture={(event) => {
        if (event.key === "Escape") onDismiss?.();
      }}
      onBlur={(event) => {
        const next = event.relatedTarget;
        const inside =
          next instanceof Element &&
          ((wrapperRef.current?.contains(next) ?? false) || next.closest("[data-slot=combobox-content]") !== null);
        if (!inside) onDismiss?.();
      }}
    >
      <Label htmlFor={inputId} className={cn(labelHidden && "sr-only")}>
        {label}
      </Label>
      <Combobox
        items={items}
        filteredItems={result.shown}
        itemToStringLabel={itemText}
        isItemEqualToValue={(a: T, b: T) => itemKey(a) === itemKey(b)}
        // The top match is highlighted as the user types, so Enter picks it ("403", Enter; owner answer 2026-09-30).
        autoHighlight
        value={value}
        onValueChange={(next) => {
          if (next !== null) onValueChange(next as T);
        }}
        onInputValueChange={(next, details) => setQuery(details.reason === "input-change" ? next : "")}
        onOpenChange={(open) => {
          if (!open) setQuery("");
        }}
        disabled={disabled}
      >
        <ComboboxInput
          id={inputId}
          placeholder={placeholder}
          disabled={disabled}
          autoFocus={autoFocus}
          className="h-11 w-full *:data-[slot=input-group-control]:h-full"
        />
        <ComboboxContent>
          <ComboboxList>
            {(item: T) => (
              <ComboboxItem key={itemKey(item)} value={item} className="min-h-11 md:min-h-8">
                {renderItem ? renderItem(item) : itemText(item)}
              </ComboboxItem>
            )}
          </ComboboxList>
          {result.footer.length > 0 ? (
            <div className="grid gap-0.5 border-t px-2 py-1.5 text-xs text-muted-foreground">
              {result.footer.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}
        </ComboboxContent>
      </Combobox>
    </div>
  );
}
