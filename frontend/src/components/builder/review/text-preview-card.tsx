"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useDraft } from "@/lib/draft/context";
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";
import { printedLines, serverStrip, type BoxKind, type PrintedLine } from "@/lib/formatting";
import { SECTION_LABELS } from "@/lib/liturgy/sections";
import { useLiturgyConfig } from "@/lib/queries/liturgy";
import { cn } from "@/lib/utils";

export const PREVIEW_TITLE = "Text preview";
export const PREVIEW_INTRO = "Your text as the bulletin prints it, with its bold, italic, headings and lists.";
export const PREVIEW_EMPTY = "No text to preview yet.";
const PASTORS_COPY = "Prayers of the People (pastor's copy)";

/** The free-text announcements, in the printed order, with their printed headings' words. */
const ANNOUNCEMENT_BOXES = [
  ["activities", "This week's activities"],
  ["prayer_concerns", "Prayers and concerns"],
  ["collection", "Items for collection"],
  ["other", "Other announcements"],
] as const;

export type PreviewBox = { id: string; label: string; box: BoxKind; text: string };

const SECTION_BOX: Partial<Record<string, BoxKind>> = {
  call_to_worship: "dialogue",
  assurance: "assurance",
  prayer_of_confession: "confession",
};

/** Every box that prints text, as the server prints it (`serverStrip`: line endings, a vertical tab and a form
 * feed as line breaks, trimmed): the switched-on prayers in service order, the Affirmation's own text (all bold, as
 * printed), the custom elements, then the announcements. */
export function previewBoxes(draft: DraftV1): PreviewBox[] {
  const boxes: PreviewBox[] = [];
  const add = (id: string, label: string, box: BoxKind, raw: string) => {
    const text = serverStrip(raw);
    if (text) boxes.push({ id, label, box, text });
  };
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    if (!card.enabled) continue;
    add(key, key === "prayers_of_the_people" ? PASTORS_COPY : SECTION_LABELS[key], SECTION_BOX[key] ?? "prayer", card.text);
  }
  const a = draft.liturgy.affirmation;
  if (a.include && a.choice === "own") add("affirmation", "Affirmation of Faith", "confession", a.text);
  for (const element of draft.liturgy.custom_elements) {
    if (serverStrip(element.label)) add(`custom-${element.id}`, serverStrip(element.label), "prayer", element.text);
  }
  for (const [key, label] of ANNOUNCEMENT_BOXES) add(key, label, "announcement", draft.bulletin.announcements[key]);
  return boxes;
}

const LINE_CLASS: Record<PrintedLine["style"], string> = {
  body: "",
  bold: "",
  hanging: "pl-8 -indent-8",
  center: "text-center",
  heading1: "pt-1 text-lg",
  heading2: "pt-1 text-base",
  // The marker's column is at least 2rem and as wide as a long one ("100.") needs.
  item: "grid grid-cols-[minmax(2rem,max-content)_1fr] gap-x-1",
  center_heading1: "pt-1 text-center text-lg",
  center_heading2: "pt-1 text-center text-base",
};

/** One box's printed lines, as React text (never HTML): a span's bold and italic, a line's style. */
export function PrintedText({ lines }: { lines: PrintedLine[] }) {
  return (
    <div className="grid gap-1 font-serif text-sm whitespace-pre-line wrap-anywhere">
      {lines.map((line, n) => {
        const spans = line.spans.map((s, i) => (
          <span key={i} className={cn(s.bold && "font-bold", s.italic && "italic")}>
            {s.text}
          </span>
        ));
        return (
          <p key={n} data-style={line.style} className={LINE_CLASS[line.style]}>
            {line.marker ? (
              <>
                <span>{line.marker}</span>
                <span>{spans}</span>
              </>
            ) : (
              spans
            )}
          </p>
        );
      })}
    </div>
  );
}

/**
 * The Review step's text preview (formatting spec, "The Review preview"; owner
 * decision 4): closed at first; open, each box with text as the printed
 * bulletin prints it (the rules of shared/formatting.json): the prayers, the
 * Affirmation's own text, the custom elements and the announcements. The
 * Prayers of the People print only in the pastor's Word copy, as a prayer.
 */
export function TextPreviewCard() {
  const { draft } = useDraft();
  const config = useLiturgyConfig();
  const [open, setOpen] = useState(false);
  const boxes = previewBoxes(draft);
  const response = config.data?.assurance_response ?? "";
  return (
    <section aria-labelledby="text-preview-title" className="grid gap-3 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="text-preview-title" className="text-base font-medium">
          {PREVIEW_TITLE}
        </h2>
        <p className="text-sm text-muted-foreground">{PREVIEW_INTRO}</p>
      </div>
      <Collapsible open={open} onOpenChange={setOpen} className="grid gap-3">
        <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
          <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
          Show text preview
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-4">
          {boxes.length === 0 ? <p className="text-sm text-muted-foreground">{PREVIEW_EMPTY}</p> : null}
          {boxes.map((b) => (
            <section key={b.id} aria-label={b.label} className="grid gap-1">
              <h3 className="text-sm font-medium text-muted-foreground">{b.label}</h3>
              <PrintedText lines={printedLines(b.box, b.text, response)} />
            </section>
          ))}
        </CollapsibleContent>
      </Collapsible>
    </section>
  );
}
