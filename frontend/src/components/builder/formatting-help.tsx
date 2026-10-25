/**
 * The "Formatting help" line under a text box (formatting spec, "Help copy";
 * owner decision 4): the marks the box takes and where to see them. The two
 * dialogue boxes (the Call to Worship and the Assurance of Pardon) take bold
 * and italic only.
 */
export const FORMATTING_HELP = "Formatting: **bold**, *italic*, # Heading, ## Smaller heading, - or 1. for a list. Preview on the Review step.";
export const DIALOGUE_HELP = "Formatting: **bold**, *italic*. Preview on the Review step.";

export function FormattingHelp({ id, dialogue = false }: { id: string; dialogue?: boolean }) {
  return (
    <p id={id} className="text-sm text-muted-foreground">
      {dialogue ? DIALOGUE_HELP : FORMATTING_HELP}
    </p>
  );
}
