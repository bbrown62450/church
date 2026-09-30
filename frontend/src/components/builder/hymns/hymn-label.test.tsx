/** `HymnLabel` (S "Filled slot", "Newer-hymn year label"; Testing `hymn-label.test.tsx`; AC20). */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { hymn } from "@/test/fixtures";

import { HymnLabel } from "./hymn-label";

describe("HymnLabel", () => {
  it("shows #number and title, the hymnal when asked, and a Listen link only for an https page", () => {
    const { rerender } = render(<HymnLabel hymn={hymn()} showHymnal listen />);
    expect(screen.getByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(screen.getByText("GG2013")).toBeInTheDocument();
    const listen = screen.getByRole("link", { name: "Listen to Come, Thou Almighty King on Hymnary.org" });
    expect(listen).toHaveAttribute("href", "https://hymnary.org/hymn/GG2013/403");
    expect(listen).toHaveAttribute("target", "_blank");
    expect(listen).toHaveAttribute("rel", "noopener noreferrer");
    rerender(<HymnLabel hymn={hymn({ number: null, link: "http://hymnary.org/x" })} listen />);
    expect(screen.getByText("Come, Thou Almighty King")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull(); // not https: no link
    expect(screen.queryByText("GG2013")).toBeNull();
    rerender(<HymnLabel hymn={hymn({ link: "javascript:alert(1)" })} listen />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("adds Written {year} only for a flagged hymn, and in a chip the title truncates while the badges stay whole", () => {
    const newer = hymn({ title: "Here I Am, Lord", number: 710, text_year: 1981, newer_than_preferred: true });
    const { rerender } = render(<HymnLabel hymn={newer} recentBadge="Used Sep 6" truncate />);
    expect(screen.getByText("#710 Here I Am, Lord")).toHaveClass("truncate", "min-w-0");
    expect(screen.getByText("Written 1981")).toHaveClass("shrink-0");
    expect(screen.getByText("Used Sep 6")).toHaveClass("shrink-0");
    rerender(<HymnLabel hymn={hymn({ text_year: 1757, newer_than_preferred: false })} />);
    expect(screen.queryByText(/^Written/)).toBeNull();
    rerender(<HymnLabel hymn={{ title: "Snapshot", number: 5, hymnal: "GG2013" }} />); // a draft pick has no year
    expect(screen.queryByText(/^Written/)).toBeNull();
  });

  it("wraps everywhere but a chip, so at 375 px a row with every badge moves them to a second line", () => {
    const newer = hymn({ title: "Here I Am, Lord", number: 710, text_year: 1981, newer_than_preferred: true });
    const { rerender } = render(<HymnLabel hymn={newer} showHymnal recentBadge="Used Sep 6" listen />);
    const title = screen.getByText("#710 Here I Am, Lord");
    expect(title.parentElement).toHaveClass("flex-wrap", "min-w-0");
    expect(title).toHaveClass("wrap-anywhere", "min-w-0");
    expect(title).not.toHaveClass("truncate");
    rerender(<HymnLabel hymn={newer} showHymnal recentBadge="Used Sep 6" truncate />);
    expect(screen.getByText("#710 Here I Am, Lord").parentElement).not.toHaveClass("flex-wrap");
  });
});
