"use client";

import { useRef, useState, type FormEvent, type RefObject } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ApiError } from "@/lib/api/client";
import type { Hymn } from "@/lib/api/types";
import { hymnFieldErrors, isDuplicateHymn, useCreateHymn, useDeleteHymn, useUpdateHymn } from "@/lib/queries/hymn-library";
import {
  emptyHymnForm,
  hymnFormErrors,
  hymnFormFrom,
  hymnLabel,
  hymnPatch,
  newHymnBody,
  type HymnFieldErrors,
  type HymnForm,
} from "@/lib/settings/hymns";

export const SAVED_SERVICES_NOTE = "Changes also appear in saved services that use this hymn.";
export const ADMINS_ONLY_FIELD = "Only admins can change this.";
export const REFS_HELP = "Used by “Hymns for the readings” and AI suggestions.";
export const DELETE_BODY = "Saved services keep this hymn. Services in progress that use it will ask you to choose a replacement.";

const SHEET =
  "max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg";

/** The order fields are checked and focused in. */
const ORDER: (keyof HymnForm)[] = ["title", "number", "hymnal", "scripture_refs", "themes", "link", "text_year", "hymnal_count"];

export type HymnDialogProps = {
  /** null: **Add hymn**; a hymn: **Edit hymn**. */
  hymn: Hymn | null;
  /** The church's hymnal codes; the Hymnal field shows only with more than one. */
  codes: string[];
  /** The add form's hymnal (the effective default), "" when the church has none. */
  defaultHymnal: string;
  admin: boolean;
  /** Where focus goes when the hymn is gone (deleted here or elsewhere): the row that opened it is gone too. */
  fallbackFocus: RefObject<HTMLElement | null>;
  /** Closes the dialog; `key` is "add" or the hymn's id, so a late answer never closes another one. */
  onClose(key: string): void;
};

/**
 * **Add hymn** / **Edit hymn** (slice 6a-2; 6a spec UX §2b): Title, Number,
 * Hymnal (with several), Scripture references, Themes, Link, and the year and
 * familiarity (an admin's; a member sees them read-only and never sends them).
 * An edit sends only what changed and notes that saved services follow it; an
 * admin may delete the hymn (confirmed). A 409 shows above the buttons, a field
 * error under its field; the dialog cannot be closed while a request runs. A
 * bottom sheet on phones, as Edit contact is.
 */
export function HymnDialog({ hymn, codes, defaultHymnal, admin, fallbackFocus, onClose }: HymnDialogProps) {
  const key = hymn?.id ?? "add";
  const thisYear = new Date().getFullYear();
  const create = useCreateHymn();
  const update = useUpdateHymn();
  const remove = useDeleteHymn();
  const [baseline] = useState<HymnForm>(() => (hymn ? hymnFormFrom(hymn) : emptyHymnForm(defaultHymnal)));
  const [form, setForm] = useState<HymnForm>(baseline);
  const [errors, setErrors] = useState<HymnFieldErrors>({});
  const [duplicate, setDuplicate] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const gone = useRef(false);
  const refs = useRef<Partial<Record<keyof HymnForm, HTMLElement | null>>>({});
  const pending = create.isPending || update.isPending || remove.isPending;
  const options = { thisYear, admin };

  const set = (field: keyof HymnForm, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
    setDuplicate(null);
  };

  const close = (isGone = false) => {
    gone.current = isGone;
    onClose(key);
  };

  function showErrors(found: HymnFieldErrors) {
    setErrors(found);
    const first = ORDER.find((field) => found[field]);
    if (first) refs.current[first]?.focus();
  }

  const handlers = {
    onError: (e: ApiError) => {
      if (e.status === 403 || e.status === 404) {
        close(e.status === 404); // toasted, and the role or the lists refetched, by the mutation
        return;
      }
      if (isDuplicateHymn(e)) {
        setDuplicate(e.message);
        return;
      }
      const found = hymnFieldErrors(e);
      if (found) showErrors(found);
    },
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    const found = hymnFormErrors(form, options);
    if (Object.keys(found).length > 0) {
      showErrors(found);
      return;
    }
    if (hymn === null) {
      create.mutate(newHymnBody(form, options), {
        ...handlers,
        onSuccess: () => {
          toast.success("Hymn added.");
          close();
        },
      });
      return;
    }
    const patch = hymnPatch(baseline, form, options);
    if (Object.keys(patch).length === 0) {
      close();
      return;
    }
    update.mutate(
      { id: hymn.id, patch },
      {
        ...handlers,
        onSuccess: () => {
          toast.success("Hymn updated.");
          close();
        },
      },
    );
  }

  function field(
    name: keyof HymnForm,
    label: string,
    extra: { help?: string; placeholder?: string; numeric?: boolean; readOnly?: boolean; maxLength?: number } = {},
  ) {
    const id = `hymn-${name}`;
    const error = errors[name];
    const described = [extra.help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean).join(" ");
    return (
      <div className="grid gap-1.5">
        <Label htmlFor={id}>{label}</Label>
        <Input
          id={id}
          ref={(el) => {
            refs.current[name] = el;
          }}
          value={form[name]}
          className="h-11 md:h-9"
          placeholder={extra.placeholder}
          readOnly={extra.readOnly}
          maxLength={extra.maxLength}
          autoComplete="off"
          {...(extra.numeric ? { inputMode: "numeric" as const } : {})}
          aria-invalid={error ? true : undefined}
          aria-describedby={described || undefined}
          onChange={(event) => set(name, event.target.value)}
        />
        {extra.help ? (
          <p id={`${id}-help`} className="text-sm text-muted-foreground">
            {extra.help}
          </p>
        ) : null}
        {error ? (
          <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  const hymnalItems = Object.fromEntries(codes.map((code) => [code, code]));
  const factsHelp = admin ? undefined : ADMINS_ONLY_FIELD;

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        // while a request runs the dialog stays open (Escape and a tap outside are ignored; Cancel is disabled)
        if (!open && !pending) close();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className={SHEET}
        finalFocus={() => (gone.current ? fallbackFocus.current : true)}
      >
        <DialogHeader>
          <DialogTitle>{hymn ? "Edit hymn" : "Add hymn"}</DialogTitle>
          <DialogDescription>{hymn ? hymnLabel(hymn) : "A hymn your church sings that is not in the list yet."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          {field("title", "Title", { maxLength: 300 })}
          {field("number", "Number", { numeric: true, maxLength: 5 })}
          {codes.length > 1 ? (
            <div className="grid gap-1.5">
              <Label htmlFor="hymn-hymnal">Hymnal</Label>
              <Select
                value={form.hymnal}
                items={hymnalItems}
                onValueChange={(value) => {
                  if (typeof value === "string") set("hymnal", value);
                }}
              >
                <SelectTrigger
                  id="hymn-hymnal"
                  ref={(el: HTMLElement | null) => {
                    refs.current.hymnal = el;
                  }}
                  className="h-11 w-full data-[size=default]:h-11 md:h-9"
                  aria-invalid={errors.hymnal ? true : undefined}
                  aria-describedby={errors.hymnal ? "hymn-hymnal-error" : undefined}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {codes.map((code) => (
                    <SelectItem key={code} value={code}>
                      {code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.hymnal ? (
                <p id="hymn-hymnal-error" role="alert" className="text-sm text-destructive">
                  {errors.hymnal}
                </p>
              ) : null}
            </div>
          ) : null}
          {field("scripture_refs", "Scripture references", { placeholder: "e.g. Psalm 23; John 10:11-18", help: REFS_HELP, maxLength: 2000 })}
          {field("themes", "Themes", { placeholder: "e.g. Advent, hope", maxLength: 2000 })}
          {field("link", "Link", { placeholder: "https://hymnary.org/…", maxLength: 500 })}
          {field("text_year", "Year the words were written", { numeric: true, readOnly: !admin, help: factsHelp })}
          {field("hymnal_count", "Number of hymnals (familiarity)", { numeric: true, readOnly: !admin, help: factsHelp })}
          {hymn ? <p className="text-sm text-muted-foreground">{SAVED_SERVICES_NOTE}</p> : null}
          {duplicate ? (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{duplicate}</AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            {hymn && admin ? (
              <Button
                type="button"
                variant="destructive"
                size="touch"
                className="sm:mr-auto md:h-8"
                disabled={pending}
                onClick={() => setConfirming(true)}
              >
                Delete hymn
              </Button>
            ) : null}
            <DialogClose disabled={pending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
              Cancel
            </DialogClose>
            <PendingButton type="submit" size="touch" className="md:h-8" pending={create.isPending || update.isPending} pendingLabel={hymn ? "Saving…" : "Adding…"}>
              {hymn ? "Save changes" : "Add hymn"}
            </PendingButton>
          </DialogFooter>
        </form>
        {hymn && admin ? (
          <ConfirmDialog
            open={confirming}
            onOpenChange={(open) => {
              if (!open && !remove.isPending) setConfirming(false);
            }}
            title={`Delete “${hymn.title}”?`}
            description={DELETE_BODY}
            confirmLabel="Delete hymn"
            destructive
            pending={remove.isPending}
            onConfirm={() =>
              remove.mutate(hymn.id, {
                onSuccess: () => {
                  toast.success("Hymn deleted.");
                  setConfirming(false);
                  close(true);
                },
                onError: (e) => {
                  setConfirming(false);
                  if (e.status === 404) close(true); // deleted elsewhere: gone all the same (toasted)
                  if (e.status === 403) close();
                },
              })
            }
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
