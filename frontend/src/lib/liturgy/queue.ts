/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; "Generate empty
 * sections": at most 3 in flight, which leaves one of the server's 4 AI slots
 * free). First in, first out; each task gets its own `AbortController`.
 * `cancel(key)` aborts a running task or drops a waiting one, frees its slot
 * at once, and its outcome is never delivered; a task cancelled before its
 * `run` was called never runs. A task's outcome is delivered before the next
 * task starts, so `done` can still cancel the waiting ones (S step 7: a 429
 * stops the queue).
 */
export type TaskOutcome<T> = { ok: true; value: T } | { ok: false; error: unknown };

export type TaskQueue = {
  push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void): void;
  /** False when the key is neither waiting nor running. */
  cancel(key: string): boolean;
  cancelAll(): void;
  runningKeys(): string[];
  waitingKeys(): string[];
};

type Task = { key: string; start: () => void; controller: AbortController };

export function createTaskQueue({ concurrency }: { concurrency: number }): TaskQueue {
  const waiting: Task[] = [];
  const running = new Map<string, Task>();

  function pump(): void {
    while (running.size < concurrency && waiting.length > 0) {
      const task = waiting.shift() as Task;
      running.set(task.key, task);
      task.start();
    }
  }

  function cancel(key: string): boolean {
    const at = waiting.findIndex((t) => t.key === key);
    if (at >= 0) {
      waiting.splice(at, 1);
      return true;
    }
    const task = running.get(key);
    if (!task) return false;
    running.delete(key);
    task.controller.abort();
    pump();
    return true;
  }

  return {
    push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void) {
      cancel(key);
      const controller = new AbortController();
      const task: Task = {
        key,
        controller,
        start: () => {
          const settle = (outcome: TaskOutcome<T>) => {
            if (controller.signal.aborted || running.get(key) !== task) return;
            running.delete(key);
            try {
              done(outcome);
            } finally {
              pump();
            }
          };
          Promise.resolve()
            .then(() => (controller.signal.aborted ? Promise.reject(controller.signal.reason) : run(controller.signal)))
            .then(
              (value: T) => settle({ ok: true, value }),
              (error: unknown) => settle({ ok: false, error }),
            );
        },
      };
      waiting.push(task);
      pump();
    },
    cancel,
    cancelAll() {
      waiting.length = 0;
      for (const task of running.values()) task.controller.abort();
      running.clear();
    },
    runningKeys: () => [...running.keys()],
    waitingKeys: () => waiting.map((t) => t.key),
  };
}
