import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AiStatus } from "../src/components/AiStatus";

afterEach(() => vi.restoreAllMocks());

it.each([true, false])("shows configured AI status (%s)", async (enabled) => {
  const message = enabled ? "AI configured" : "AI disabled; sample works offline";
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ aiEnabled: enabled, message })));
  render(<AiStatus />);
  expect(await screen.findByText(message)).toBeInTheDocument();
});

it("handles an unreachable backend", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
  render(<AiStatus />);
  expect(await screen.findByText(/unavailable while the local service is offline/)).toBeInTheDocument();
});
