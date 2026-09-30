import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PhotoIntake } from "../src/components/PhotoIntake";
import { reviewRequest } from "../src/api/photoReview";
import { demoKeyboard } from "../src/data/demoKeyboard";
import { boardPresets } from "../src/data/presets";

vi.mock("../src/api/photoReview", () => ({ reviewRequest: vi.fn() }));
afterEach(() => { vi.resetAllMocks(); sessionStorage.clear(); });

it("blocks intake with a clear restart message for an old backend", async () => {
  vi.mocked(reviewRequest).mockRejectedValue(new Error("404"));
  render(<PhotoIntake onApply={vi.fn()} />);
  expect(await screen.findByText(/Stop the app, run start.ps1/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Try demo keyboard" })).toBeDisabled();
});

it("offers every photo and quickly fills the board while preserving manual corrections", async () => {
  const onApply = vi.fn();
  const board = boardPresets.find((entry) => entry.layoutType === "75")!;
  vi.mocked(reviewRequest).mockImplementation(async (path) => {
    if (path === "version") return { version: "photo-review-2" };
    if (path === "reviews") return { id: "caps", title: "Quick caps", kind: "keycaps", sourceUrl: "https://shop.example/caps", layout: null,
      images: Array.from({ length: 75 }, (_, i) => ({ url: `https://example.com/${i}.png`, alt: `Candidate ${i + 1}` })), colors: [], variants: [], warnings: [], cached: false };
    if (path.endsWith("/quick-fit")) return { id: "auto", colors: [{ id: "blue", hex: "#245577" }],
      keyColorMap: Object.fromEntries(board.keys.map((key) => [key.id, "blue"])), warnings: ["Suggested scheme"] };
    if (path.endsWith("/sample")) return { id: "manual", colors: [{ id: "red", hex: "#FF0000" }], warnings: [] };
    if (path.endsWith("/confirm")) return { warnings: [] };
    throw new Error(path);
  });
  render(<PhotoIntake onApply={onApply} keyboard={board} />);
  await screen.findByText(/Backend connected/);
  fireEvent.click(screen.getByRole("button", { name: "Try demo keycaps" }));
  await screen.findByDisplayValue("Quick caps");
  expect(screen.getByLabelText("Keycaps photo").querySelectorAll("option")).toHaveLength(75);
  fireEvent.change(screen.getByLabelText("Keycaps photo"), { target: { value: "74" } });
  fireEvent.load(screen.getByAltText("Keycaps photo to crop"));
  fireEvent.click(screen.getByRole("button", { name: "Quick fit colors" }));
  await screen.findByText("Suggested scheme");
  expect(screen.getByText(/84 \/ 84 keys assigned/)).toBeInTheDocument();
  expect(reviewRequest).toHaveBeenCalledWith("reviews/caps/quick-fit", expect.objectContaining({ imageIndex: 74, layout: "ANSI_75", strategy: "scheme" }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole("button", { name: "Pick photo color for f1" }));
  expect(screen.getByLabelText("Keycap picking mode")).toHaveValue("per-key");
  expect(screen.getByText(/84 \/ 84 keys assigned/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Sample keycap colors" }));
  fireEvent.click(await screen.findByRole("button", { name: "Assign selected color to f1" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply per-key colors" }));
  await screen.findByText(/Keycaps applied/);
  expect(reviewRequest).toHaveBeenCalledWith("reviews/caps/confirm", expect.objectContaining({ keySamples: expect.objectContaining({
    f1: { sampleId: "manual", colorId: "red" }, a: { sampleId: "auto", colorId: "blue" },
  }) }), expect.any(AbortSignal));
  fireEvent.change(screen.getByLabelText("Keycap picking mode"), { target: { value: "quick" } });
  fireEvent.change(screen.getByLabelText("Keycaps photo"), { target: { value: "0" } });
  expect(screen.getByRole("button", { name: "Apply suggested colors" })).toBeDisabled();
  expect(screen.getByText(/0 \/ 84 keys assigned/)).toBeInTheDocument();
});

it("maps photo samples onto actual 75% keys and clears assignments after a board change", async () => {
  const onApply = vi.fn();
  const board = boardPresets.find((board) => board.layoutType === "75")!;
  vi.mocked(reviewRequest).mockImplementation(async (path) => {
    if (path === "version") return { version: "photo-review-2" };
    if (path === "reviews") return { id: "caps", title: "Caps", kind: "keycaps", sourceUrl: "https://shop.example/caps", layout: null,
      images: [{ url: "https://shop.example/photo.png", alt: "Caps" }], colors: [], variants: [], warnings: [], cached: false };
    if (path.endsWith("/sample")) return { id: "sample", colors: [{ id: "blue", hex: "#245577", name: "Sample 1", source: "image_sample" }], warnings: ["Approximate colors"] };
    if (path.endsWith("/confirm")) return { keyColorMap: { f1: "blue" }, warnings: [] };
    throw new Error(path);
  });
  const { rerender } = render(<PhotoIntake onApply={onApply} keyboard={board} />);
  await screen.findByText(/Backend connected/);
  fireEvent.click(screen.getByRole("button", { name: "Try demo keycaps" }));
  await screen.findByDisplayValue("Caps");
  fireEvent.change(screen.getByLabelText("Keycap picking mode"), { target: { value: "per-key" } });
  fireEvent.click(screen.getByRole("button", { name: "Pick photo color for f1" }));
  fireEvent.load(screen.getByAltText("Keycaps photo to crop"));
  fireEvent.click(screen.getByRole("button", { name: "Sample keycap colors" }));
  await screen.findByText("Approximate colors");
  fireEvent.click(screen.getByRole("button", { name: "Assign selected color to f1" }));
  expect(screen.getByText(/1 \/ 84 keys assigned/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Apply per-key colors" }));
  await screen.findByText(/Keycaps applied/);
  expect(reviewRequest).toHaveBeenCalledWith("reviews/caps/confirm", expect.objectContaining({ layout: "ANSI_75", keySamples: { f1: { sampleId: "sample", colorId: "blue" } } }), expect.any(AbortSignal));
  expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ targetKeyboardId: board.id, keyColorMap: { f1: "blue" } }));
  rerender(<PhotoIntake onApply={onApply} keyboard={demoKeyboard} />);
  expect(screen.queryByRole("button", { name: "Pick photo color for f1" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Apply per-key colors" })).toBeDisabled();
});

it("applies the keyboard even if the keycap page fails and invalidates colors when the crop changes", async () => {
  const onApply = vi.fn();
  vi.mocked(reviewRequest).mockImplementation(async (path, body) => {
    if (path === "version") return { version: "photo-review-2" };
    if (path === "reviews") {
      if ((body as { kind: string }).kind === "keycaps") throw new Error("Store blocked the request; upload a photo.");
      return { id: "review", title: "Photo board", kind: "keyboard", sourceUrl: "https://shop.example/board", layout: "ANSI_75",
        images: [{ url: "https://shop.example/photo.png", alt: "Blue housing" }], colors: [], variants: [], warnings: [], cached: false };
    }
    if (path.endsWith("/sample")) return { id: "sample", colors: [{ id: "blue", hex: "#245577", name: "Sample 1", source: "image_sample" }], warnings: ["Approximate colors"] };
    if (path.endsWith("/confirm")) return { keyboard: demoKeyboard, caseColor: "#245577", warnings: [] };
    throw new Error(path);
  });
  render(<PhotoIntake onApply={onApply} />);
  await screen.findByText(/Backend connected/);
  fireEvent.click(screen.getByRole("button", { name: "Try demo keyboard" }));
  await screen.findByDisplayValue("Photo board");
  fireEvent.click(screen.getByRole("button", { name: "Try demo keycaps" }));
  await screen.findByText(/Store blocked/);
  fireEvent.click(screen.getByRole("button", { name: "Preview keyboard layout" }));
  await screen.findByText(/Keyboard layout applied/);
  expect(onApply).toHaveBeenCalledTimes(1);
  fireEvent.load(screen.getByAltText("Keyboard photo to crop"));
  fireEvent.click(screen.getByRole("button", { name: "Sample case colors" }));
  await screen.findByText("Approximate colors");
  expect(screen.getByRole("button", { name: "Apply reviewed keyboard" })).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Keyboard crop left (%)"), { target: { value: "20" } });
  expect(screen.queryByRole("button", { name: "Apply reviewed keyboard" })).not.toBeInTheDocument();
});
