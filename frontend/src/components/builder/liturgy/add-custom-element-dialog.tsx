"use client";

import type { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { useRef, useState, type FormEvent } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyConfig } from "@/lib/api/types";
import type { CustomElement } from "@/lib/liturgy/cards";

/**
 * "Add custom element" (S UX "Custom elements"; BC-12): a dialog, a bottom
 * sheet below `md`, with a native form (F §4.8): Label (required), Text
 * (optional) and Place (defaulting to the first place, "After Call to
 * Worship", as app.py did). A blank label says "Label is required." and
 * focuses the field. After Add the fields are empty the next time it opens.
 * Taller than the window it scrolls inside (85 dvh as a sheet, the window
 * less 2 rem as a dialog), and the sheet's footer clears the home indicator.
 * `finalFocus` says where focus goes when it closes (Base UI's default: the
 * control that opened it).
 */
export function AddCustomElementDialog({
  open,
  onOpenChange,
  placements,
  limits,
  onAdd,
  finalFocus,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  placements: LiturgyConfig["custom_placements"];
  limits: LiturgyConfig["limits"];
  onAdd: (element: Omit<CustomElement, "id">) => void;
  finalFocus?: DialogPrimitive.Popup.Props["finalFocus"];
}) {
  const first = placements[0]?.key ?? "end";
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [place, setPlace] = useState(first);
  const [missing, setMissing] = useState(false);
  const labelRef = useRef<HTMLInputElement>(null);
  const items = Object.fromEntries(placements.map((p) => [p.key, p.label]));

  function reset() {
    setLabel("");
    setText("");
    setPlace(first);
    setMissing(false);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (label.trim() === "") {
      setMissing(true);
      labelRef.current?.focus();
      return;
    }
    onAdd({ label, text, insert_after: place });
    reset();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent
        showCloseButton={false}
        {...(finalFocus === undefined ? {} : { finalFocus })}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-h-[calc(100dvh-2rem)] md:max-w-lg md:overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle>Add custom element</DialogTitle>
          <DialogDescription>A heading and text printed in the Word files at the place you choose.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} noValidate className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="new-custom-label">Label</Label>
            <Input
              id="new-custom-label"
              ref={labelRef}
              value={label}
              maxLength={limits.max_custom_label}
              placeholder="e.g. Children's Moment"
              aria-invalid={missing ? true : undefined}
              aria-describedby={missing ? "new-custom-label-error" : undefined}
              onChange={(event) => {
                setLabel(event.target.value);
                setMissing(false);
              }}
              className="h-11"
            />
            {missing ? (
              <p id="new-custom-label-error" className="text-sm text-destructive">
                Label is required.
              </p>
            ) : null}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-custom-text">Text (optional)</Label>
            <Textarea
              id="new-custom-text"
              value={text}
              maxLength={limits.max_custom_text}
              placeholder="Words for the bulletin or order of service"
              className="max-h-[40vh] overflow-y-auto"
              onChange={(event) => setText(event.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label id="new-custom-place">Place</Label>
            <Select
              value={place}
              items={items}
              onValueChange={(value) => {
                if (typeof value === "string") setPlace(value);
              }}
            >
              <SelectTrigger aria-labelledby="new-custom-place" className="h-11 w-full data-[size=default]:h-11">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {placements.map((p) => (
                  <SelectItem key={p.key} value={p.key}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            <DialogClose render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>Cancel</DialogClose>
            <Button type="submit" size="touch" className="md:h-8">
              Add
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
