import { render, screen } from "@testing-library/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { describe, expect, it } from "vitest";
import { createClient } from "@/lib/supabase/client";
import { setTestPath, supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";

// The two tests run in order: the first dirties the DOM, storage and spies; the
// second proves setup-dom.ts reset all of them (F §5.2).
describe("the dom project setup (setup-dom.ts)", () => {
  it("renders with jest-dom matchers and the shared navigation and Supabase mocks", async () => {
    render(<button type="button">Save</button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();

    expect(useRouter()).toBe(testRouter);
    setTestPath("/welcome?tab=join");
    expect(usePathname()).toBe("/welcome");
    expect(useSearchParams().get("tab")).toBe("join");

    expect(createClient().auth).toBe(supabaseAuth);
    const { data } = await createClient().auth.getSession();
    expect(data.session?.access_token).toBe(TEST_ACCESS_TOKEN);

    testRouter.replace("/login");
    window.localStorage.setItem("activeChurchId", "stale");
    window.sessionStorage.setItem("wsb:pendingInviteCode", "stale");
  });

  it("has the Base UI jsdom shims and starts each test clean", () => {
    expect(document.body).toBeEmptyDOMElement();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(usePathname()).toBe("/");

    expect(new PointerEvent("pointerdown", { pointerId: 7 }).pointerId).toBe(7);
    const observer = new ResizeObserver(() => {});
    expect(() => {
      observer.observe(document.body);
      observer.disconnect();
    }).not.toThrow();
    expect(window.matchMedia("(min-width: 640px)").matches).toBe(false);

    const element = document.createElement("div");
    expect(() => element.scrollIntoView()).not.toThrow();
    expect(element.hasPointerCapture(1)).toBe(false);
    expect(() => element.releasePointerCapture(1)).not.toThrow();
    expect(element.getAnimations()).toEqual([]);
  });
});
