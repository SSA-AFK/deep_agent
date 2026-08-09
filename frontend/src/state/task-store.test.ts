import { expect, test } from "vitest";
import { applyEvent, fromSnapshot } from "./task-store";

const snapshot = { thread_id: "test-1", state: "waiting_confirmation" as const, sequence: 2, result: null, error: null, events: [] };

test("ignores duplicate and out-of-order events", () => {
  const state = fromSnapshot(snapshot);
  const next = applyEvent(state, { version: 1, sequence: 3, type: "task_status", thread_id: "test-1", timestamp: "now", data: { state: "running" } });
  expect(next.state).toBe("running");
  expect(applyEvent(next, { version: 1, sequence: 2, type: "task_status", thread_id: "test-1", timestamp: "now", data: { state: "failed" } })).toBe(next);
});
