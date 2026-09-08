import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CompatibilityPanel } from "../src/components/CompatibilityPanel";
import { KeyboardWorkbench } from "../src/components/KeyboardWorkbench";
import { demoKeyboard } from "../src/data/demoKeyboard";
import { demoKeycapSet } from "../src/data/demoKeycapSet";

vi.mock("../src/renderer/KeyboardScene", () => ({ KeyboardScene: () => <div>Preview</div> }));
const kit = { ...demoKeycapSet, supportedKeys: [{ widthU: 1, quantity: 50 }] };
const response = (status = "compatible", missing: object[] = []) => new Response(JSON.stringify({
  status, compatible: status === "compatible", missing, uncertain: [], warnings: [],
}), { headers: { "Content-Type": "application/json" } });
afterEach(() => vi.restoreAllMocks());

it("keeps absent inventory unknown without requiring the backend", () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  render(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={demoKeycapSet} />);
  expect(screen.getByText(/sample palette has no key inventory/)).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

it("sends normalized products and shows a successful check", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(response());
  render(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={kit} />);
  expect(await screen.findByText("Size and quantity checks passed.")).toBeInTheDocument();
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({ keyboard: demoKeyboard, keycapSet: kit });
});

it("shows missing sizes while leaving painting enabled", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(response("incompatible", [{ key: "right-shift", requiredWidthU: 1.75, reason: "Not supplied." }]));
  render(<KeyboardWorkbench keycapSet={kit} />);
  expect(await screen.findByText(/right-shift — 1.75u/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Alphas" }));
  expect(screen.getByRole("button", { name: "Apply Moss" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
  expect(screen.getByRole("button", { name: "Apply Moss" })).toHaveAttribute("aria-pressed", "true");
});

it("handles backend errors and retries", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response("failed", { status: 503 })).mockResolvedValueOnce(response());
  render(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={kit} />);
  expect(await screen.findByText(/Fit check failed \(503\)/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry fit check" }));
  expect(await screen.findByText("Size and quantity checks passed.")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("explains uncertain quantities without claiming compatibility", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    status: "unknown", compatible: false, missing: [], warnings: [],
    uncertain: [{ key: "space", requiredWidthU: 6.25, reason: "Matching keycap quantity is unspecified." }],
  })));
  render(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={kit} />);
  expect(await screen.findByText(/some kit details are incomplete/)).toBeInTheDocument();
  expect(screen.getByText(/1 keys need more information/)).toBeInTheDocument();
  expect(screen.queryByText("Size and quantity checks passed.")).not.toBeInTheDocument();
});

it("cancels obsolete checks when products change", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
  const { rerender } = render(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={kit} />);
  expect(screen.getByText(/Checking key sizes/)).toBeInTheDocument();
  const firstSignal = fetch.mock.calls[0][1]!.signal;
  rerender(<CompatibilityPanel keyboard={demoKeyboard} keycapSet={{ ...kit, id: "new" }} />);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(firstSignal?.aborted).toBe(true);
});
