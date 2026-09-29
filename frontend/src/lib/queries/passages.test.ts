/** The passage limiter and `passageText` (S Testing `lib/queries/passages.test.ts`). */
import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";

import { createLimiter, passageStaleTime, passageText, PASSAGE_STALE_MS } from "./passages";

/** A task the test settles by hand. */
function deferred() {
  let resolve!: (value: string) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<string>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function tick(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

describe("createLimiter", () => {
  it("runs at most 3 tasks; a 4th waits until one settles", async () => {
    const limit = createLimiter(3);
    const tasks = [deferred(), deferred(), deferred(), deferred()];
    const started: number[] = [];
    const results = tasks.map((t, i) =>
      limit(() => {
        started.push(i);
        return t.promise;
      }),
    );
    await tick();
    expect(started).toEqual([0, 1, 2]);
    tasks[1].resolve("second");
    await expect(results[1]).resolves.toBe("second");
    await tick();
    expect(started).toEqual([0, 1, 2, 3]);
    for (const t of [tasks[0], tasks[2], tasks[3]]) t.resolve("done");
    await expect(Promise.all(results)).resolves.toEqual(["done", "second", "done", "done"]);
  });

  it("a rejection frees its slot, and a waiting task whose signal aborts never starts", async () => {
    const limit = createLimiter(1);
    const first = deferred();
    const started: string[] = [];
    const a = limit(() => {
      started.push("a");
      return first.promise;
    });
    const controller = new AbortController();
    const b = limit(async () => {
      started.push("b");
      return "b";
    }, controller.signal);
    const c = limit(async () => {
      started.push("c");
      return "c";
    });
    controller.abort(new Error("collapsed"));
    await expect(b).rejects.toThrow("collapsed");
    first.reject(new Error("network"));
    await expect(a).rejects.toThrow("network");
    await expect(c).resolves.toBe("c");
    expect(started).toEqual(["a", "c"]);
    await expect(limit(async () => "d", controller.signal)).rejects.toThrow("collapsed");
  });
});

describe("passageText and passageStaleTime", () => {
  it("joins only the sections that loaded, is null when none did, and asks again after an unavailable answer", () => {
    const passage: Passage = {
      reference: "Matthew 26:14-27:66 or Matthew 27:11-54",
      status: "unavailable",
      sections: [
        { reference: "Matthew 26:14-27:66", status: "unavailable", text: "Part one." },
        { reference: "Matthew 27:11-54", status: "ok", text: "Jesus stood before the governor." },
        { reference: "Matthew 28:1", status: "ok", text: "After the Sabbath." },
      ],
    };
    expect(passageText(passage)).toBe("Jesus stood before the governor.\n\nAfter the Sabbath.");
    const none: Passage = { reference: "Hezekiah 1:1", status: "not_found", sections: [{ reference: "Hezekiah 1:1", status: "not_found", text: null }] };
    expect(passageText(none)).toBeNull();
    expect(passageStaleTime(passage)).toBe(0);
    expect(passageStaleTime(none)).toBe(PASSAGE_STALE_MS);
    expect(passageStaleTime(undefined)).toBe(PASSAGE_STALE_MS);
  });
});
