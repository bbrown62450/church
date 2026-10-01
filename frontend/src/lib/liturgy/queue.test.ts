/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; Testing
 * `queue.test.ts`): at most 3 running, first in first out, and a cancelled
 * task's signal aborts and its outcome is never delivered.
 */
import { describe, expect, it } from "vitest";

import { createTaskQueue, type TaskOutcome } from "./queue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function tick(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

function harness(concurrency = 3) {
  const queue = createTaskQueue({ concurrency });
  const started: string[] = [];
  const signals = new Map<string, AbortSignal>();
  const tasks = new Map<string, ReturnType<typeof deferred<string>>>();
  const outcomes: [string, TaskOutcome<string>][] = [];
  const push = (key: string) => {
    const task = deferred<string>();
    tasks.set(key, task);
    queue.push(
      key,
      (signal) => {
        started.push(key);
        signals.set(key, signal);
        return task.promise;
      },
      (outcome) => outcomes.push([key, outcome]),
    );
  };
  return { queue, started, signals, tasks, outcomes, push };
}

describe("createTaskQueue (S queue.ts)", () => {
  it("runs at most 3 at once, in the order pushed, and delivers each outcome", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d", "e"]) h.push(key);
    await tick();
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "b", "c"]);
    expect(h.queue.waitingKeys()).toEqual(["d", "e"]);
    h.tasks.get("b")!.resolve("B");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d"]);
    h.tasks.get("a")!.reject(new Error("no"));
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d", "e"]);
    expect(h.outcomes).toEqual([
      ["b", { ok: true, value: "B" }],
      ["a", { ok: false, error: new Error("no") }],
    ]);
  });

  it("cancel aborts a running task or drops a waiting one, and neither outcome is delivered", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d"]) h.push(key);
    await tick();
    expect(h.queue.cancel("d")).toBe(true); // waiting: never starts
    expect(h.queue.cancel("b")).toBe(true); // running: its signal aborts
    expect(h.signals.get("b")?.aborted).toBe(true);
    expect(h.queue.cancel("zzz")).toBe(false);
    h.tasks.get("b")!.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "c"]);
    h.push("e");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "e"]); // b's slot freed at once
    // A task cancelled as soon as it got a slot, before its run was called, never runs.
    h.queue.cancel("c");
    h.push("f");
    h.queue.cancel("f");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "e"]);
  });

  it("delivers an outcome before the next task starts, so it can stop the waiting ones", async () => {
    const queue = createTaskQueue({ concurrency: 1 });
    const started: string[] = [];
    const run = (key: string) => () => {
      started.push(key);
      return key === "x" ? Promise.reject(new Error("429")) : new Promise<string>(() => {});
    };
    // As the provider does on a 429: the failed task's outcome cancels every waiting one.
    queue.push("x", run("x"), () => {
      for (const key of queue.waitingKeys()) queue.cancel(key);
    });
    queue.push("y", run("y"), () => {});
    await tick();
    expect(started).toEqual(["x"]);
    expect(queue.waitingKeys()).toEqual([]);
  });

  it("cancelAll aborts every running task and drops every waiting one", async () => {
    const h = harness(2);
    for (const key of ["a", "b", "c"]) h.push(key);
    await tick();
    h.queue.cancelAll();
    expect([h.signals.get("a")?.aborted, h.signals.get("b")?.aborted]).toEqual([true, true]);
    for (const task of h.tasks.values()) task.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b"]);
    expect([h.queue.runningKeys(), h.queue.waitingKeys()]).toEqual([[], []]);
  });
});
