import { afterEach, expect, it, vi } from "vitest";
import { saveDesign, restoreDesign } from "../src/api/storage";
import { demoKeyboard } from "../src/data/demoKeyboard";
import { demoKeycapSet } from "../src/data/demoKeycapSet";

afterEach(() => vi.restoreAllMocks());

it("imports both products before saving a configuration", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}"));
  await saveDesign(demoKeyboard, demoKeycapSet, { a: "moss" }, "  Design  ");
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(["/api/products/manual", "/api/products/manual", "/api/configurations"]);
  expect(JSON.parse(fetch.mock.calls[2][1]!.body as string)).toEqual({ keyboardId: demoKeyboard.id,
    keycapSetId: demoKeycapSet.id, keyColorMap: { a: "moss" }, name: "Design" });
});

it("does not attempt a save after a conflicting import", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Product cannot be overwritten" }), { status: 409 }));
  await expect(saveDesign(demoKeyboard, demoKeycapSet, {}, "")).rejects.toThrow("Product cannot be overwritten");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("gives an actionable offline error", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
  await expect(restoreDesign("design")).rejects.toThrow("Start the backend");
});
