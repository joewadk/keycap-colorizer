import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { createIntake, fixtureCatalog, intakeStatus, type IntakeJob } from "../src/api/ingestion";
import { ProductIntake } from "../src/components/ProductIntake";
import { demoKeyboard } from "../src/data/demoKeyboard";
import { demoKeycapSet } from "../src/data/demoKeycapSet";

vi.mock("../src/api/ingestion", () => ({
  createIntake: vi.fn(), fixtureCatalog: vi.fn(), intakeStatus: vi.fn(),
}));

afterEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
});

const completed: IntakeJob = {
  id: "job-1", status: "complete", step: "COMPLETE", message: "Products are ready to preview.",
  reviewEvidence: [], events: [
    { step: "CHECKING_CACHE", message: "Checking cache.", occurredAt: "2026-09-27T12:00:00Z" },
    { step: "COMPLETE", message: "Products are ready.", occurredAt: "2026-09-27T12:00:01Z" },
  ],
  result: {
    keyboard: demoKeyboard, keycapSet: demoKeycapSet,
    compatibility: { status: "unknown", compatible: false, missing: [], uncertain: [], warnings: [] },
    warnings: [], cachedProducts: [],
  },
};

it("loads offline fixture URLs and sends them through the local workflow", async () => {
  vi.mocked(fixtureCatalog).mockResolvedValue({
    keyboardUrl: "https://fixtures.keycap.test/products/ansi-75",
    keycapUrl: "https://fixtures.keycap.test/products/botanical-keycaps",
    message: "Offline products; no network is used.",
  });
  vi.mocked(createIntake).mockResolvedValue(completed);
  const onComplete = vi.fn();
  render(<ProductIntake onComplete={onComplete} />);

  fireEvent.click(screen.getByRole("button", { name: "Use offline demo" }));
  expect(await screen.findByDisplayValue("https://fixtures.keycap.test/products/ansi-75")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Analyze products" }));

  expect(await screen.findByText("Products are ready.")).toBeInTheDocument();
  expect(createIntake).toHaveBeenCalledWith(
    "https://fixtures.keycap.test/products/ansi-75",
    "https://fixtures.keycap.test/products/botanical-keycaps",
    "playwright",
    expect.any(AbortSignal),
  );
  expect(intakeStatus).not.toHaveBeenCalled();
  expect(onComplete).toHaveBeenCalledWith(completed.result);
});

it("shows review evidence without replacing the current workbench", async () => {
  vi.mocked(createIntake).mockResolvedValue({
    ...completed, result: null, status: "needs_review", step: "NEEDS_REVIEW",
    message: "The keyboard layout could not be determined.",
    reviewEvidence: [{ sourceUrl: "https://shop.example/board", finalUrl: "https://shop.example/board", title: "Mystery board", warnings: [] }],
  });
  const onComplete = vi.fn();
  render(<ProductIntake onComplete={onComplete} />);
  fireEvent.change(screen.getByLabelText("Keyboard product URL"), { target: { value: "https://shop.example/board" } });
  fireEvent.change(screen.getByLabelText("Keycap product URL"), { target: { value: "https://shop.example/caps" } });
  fireEvent.click(screen.getByRole("button", { name: "Analyze products" }));

  expect(await screen.findByText("Review: Mystery board")).toBeInTheDocument();
  expect(screen.getByText(/The keyboard layout could not be determined.*preview was not changed/)).toBeInTheDocument();
  expect(onComplete).not.toHaveBeenCalled();
});

it("rejects the same page in both product fields before creating a job", async () => {
  render(<ProductIntake onComplete={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Keyboard product URL"), { target: { value: "https://shop.example/product" } });
  fireEvent.change(screen.getByLabelText("Keycap product URL"), { target: { value: "https://shop.example/product" } });
  fireEvent.click(screen.getByRole("button", { name: "Analyze products" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("two different product pages");
  expect(createIntake).not.toHaveBeenCalled();
});

it("retains the explicitly selected reader after a remount and submits with it", async () => {
  vi.mocked(createIntake).mockResolvedValue(completed);
  const first = render(<ProductIntake onComplete={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Page reader"), { target: { value: "firecrawl" } });
  first.unmount();

  render(<ProductIntake onComplete={vi.fn()} />);
  expect(screen.getByLabelText("Page reader")).toHaveValue("firecrawl");
  expect(screen.getByText(/Uncached pages use your Firecrawl credits/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Keyboard product URL"), { target: { value: "https://shop.example/board" } });
  fireEvent.change(screen.getByLabelText("Keycap product URL"), { target: { value: "https://shop.example/caps" } });
  fireEvent.click(screen.getByRole("button", { name: "Analyze products" }));
  await screen.findByText("Products analyzed and loaded into the workbench.");
  expect(createIntake).toHaveBeenCalledWith("https://shop.example/board", "https://shop.example/caps", "firecrawl", expect.any(AbortSignal));
});
