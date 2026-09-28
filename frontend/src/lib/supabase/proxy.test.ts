import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { updateSession } from "./proxy";

// Node project: no setup-dom.ts here, so this file stubs the server client itself.
// `getUser()` resolving `{ user: null }` is a signed-out visitor.
const { getUser } = vi.hoisted(() => ({ getUser: vi.fn() }));
vi.mock("@supabase/ssr", () => ({ createServerClient: () => ({ auth: { getUser } }) }));

const ORIGIN = "https://wsb.example.test";

function visit(pathAndQuery: string): Promise<Response> {
  return updateSession(new NextRequest(new URL(pathAndQuery, ORIGIN)));
}

/** The redirect target as a URL, or null when the proxy let the request through. */
function redirectTarget(response: Response): URL | null {
  const location = response.headers.get("location");
  return location === null ? null : new URL(location);
}

beforeEach(() => {
  getUser.mockReset();
  getUser.mockResolvedValue({ data: { user: null }, error: null });
});

describe("updateSession (S Routing, proxy and login)", () => {
  it("lets a signed-out visitor through to /join with its code", async () => {
    const response = await visit("/join?code=x");

    expect(redirectTarget(response)).toBeNull();
    expect(response.headers.get("x-middleware-next")).toBe("1");
    expect(getUser).toHaveBeenCalledTimes(1);
  });

  it("sends a signed-out deep link to /login?next=<path>, dropping its query", async () => {
    const response = await visit("/builder?x=1");

    expect(response.status).toBe(307);
    const target = redirectTarget(response);
    expect(target?.origin).toBe(ORIGIN);
    expect(target?.pathname).toBe("/login");
    expect(target?.search).toBe("?next=%2Fbuilder");
  });

  it("sends a signed-out / to /login with no next", async () => {
    const response = await visit("/");

    expect(response.status).toBe(307);
    const target = redirectTarget(response);
    expect(target?.pathname).toBe("/login");
    expect(target?.search).toBe("");
  });
});
