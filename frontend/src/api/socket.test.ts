import { expect, test } from "vitest";
import { reconnectDelay } from "./socket";

test("reconnect delay is bounded exponential backoff", () => {
  expect(reconnectDelay(0)).toBe(500);
  expect(reconnectDelay(10)).toBe(10_000);
});
