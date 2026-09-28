"use client";

import { useId, useMemo, useState } from "react";

import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listTimezones, timezoneLabel } from "@/lib/timezones";

/** F §4.9 item 5: a long list renders at most this many filtered matches. */
export const TIMEZONE_MATCH_LIMIT = 50;

/** S Flow A Create tab: the field's helper, the same in both modes. */
export const TIMEZONE_HELPER = "Sets the default service date (the next Sunday in this time zone).";

export type TimezoneComboboxProps = {
  /** The IANA id ("" when none). */
  value: string;
  /** Called with the picked IANA id (combobox) or the typed text (fallback). */
  onChange: (value: string) => void;
  /** Inline message under the field; also sets `aria-invalid`. */
  error?: string | null;
  /** The `<input>`'s id in both modes (default: generated), for the label and for focusing. */
  id?: string;
};

/**
 * Matches the typed query against the label (`_` shown as a space) or the raw id,
 * ignoring case: "new york" and "new_york" both find America/New_York.
 */
function matchesZone(zone: string, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (q === "") return true;
  return timezoneLabel(zone).toLowerCase().includes(q) || zone.toLowerCase().includes(q);
}

/**
 * The time-zone picker (S Flow A Create tab; F §4.9 item 5, §7.2): the first use of
 * the Combobox pattern, reused by 6a's church profile. Items are
 * `Intl.supportedValuesOf("timeZone")`; at most 50 matches render, with "Type to search"
 * while more match. Without `Intl.supportedValuesOf` it is a plain text input and the
 * server validates the id.
 */
export function TimezoneCombobox({ value, onChange, error, id }: TimezoneComboboxProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const helperId = `${inputId}-helper`;
  const errorId = `${inputId}-error`;
  const describedBy = error ? `${helperId} ${errorId}` : helperId;

  const [zones] = useState(listTimezones);
  // What the user has typed since the list opened ("" = nothing yet, so every zone matches).
  const [query, setQuery] = useState("");
  const matchCount = useMemo(
    () => (zones ? zones.filter((zone) => matchesZone(zone, query)).length : 0),
    [zones, query],
  );

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={inputId}>Time zone</Label>
      {zones ? (
        <Combobox
          items={zones}
          limit={TIMEZONE_MATCH_LIMIT}
          filter={matchesZone}
          itemToStringLabel={timezoneLabel}
          value={value === "" ? null : value}
          onValueChange={(next) => onChange(next ?? "")}
          onInputValueChange={(next, details) => setQuery(details.reason === "input-change" ? next : "")}
          onOpenChange={(open) => {
            if (!open) setQuery("");
          }}
        >
          <ComboboxInput
            id={inputId}
            className="h-11 w-full *:data-[slot=input-group-control]:h-full"
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
          />
          <ComboboxContent>
            <ComboboxEmpty>No matching time zone.</ComboboxEmpty>
            <ComboboxList>
              {(zone: string) => (
                <ComboboxItem key={zone} value={zone} className="min-h-11 md:min-h-8">
                  {timezoneLabel(zone)}
                </ComboboxItem>
              )}
            </ComboboxList>
            {matchCount > TIMEZONE_MATCH_LIMIT ? (
              <p className="border-t px-2 py-1.5 text-xs text-muted-foreground">Type to search</p>
            ) : null}
          </ComboboxContent>
        </Combobox>
      ) : (
        <Input
          id={inputId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          className="h-11"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
      )}
      <p id={helperId} className="text-sm text-muted-foreground">
        {TIMEZONE_HELPER}
      </p>
      {error ? (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
