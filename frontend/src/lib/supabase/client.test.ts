import { beforeEach, describe, expect, it, vi } from "vitest";

const createBrowserClient = vi.fn<(...args: unknown[]) => object>(() => ({}));
vi.mock("@supabase/ssr", () => ({ createBrowserClient: (...args: unknown[]) => createBrowserClient(...args) }));

import { createClient } from "./client";

beforeEach(() => {
  createBrowserClient.mockClear();
});

describe("the browser's Supabase client (slice 5b-2)", () => {
  it("never reads a sign-in from the address bar, so /gmail/callback?code= stays the Gmail page's", () => {
    createClient();
    expect(createBrowserClient).toHaveBeenCalledTimes(1);
    expect(createBrowserClient.mock.calls[0][2]).toEqual({ auth: { detectSessionInUrl: false } });
  });
});
