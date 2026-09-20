import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SavedWorkbench } from "../src/components/SavedWorkbench";
import { demoKeyboard } from "../src/data/demoKeyboard";
import { demoKeycapSet } from "../src/data/demoKeycapSet";
import { boardPresets } from "../src/data/presets";
import { listDesigns, restoreDesign, saveDesign } from "../src/api/storage";

vi.mock("../src/api/storage", () => ({ listDesigns: vi.fn(), restoreDesign: vi.fn(), saveDesign: vi.fn() }));
vi.mock("../src/renderer/KeyboardScene", () => ({
  KeyboardScene: (props: { keyboard: typeof demoKeyboard; keyColorMap: Record<string, string>; onKeyClick: (id: string, additive: boolean) => void }) =>
    <div><output aria-label="case color">{props.keyboard.case.color}</output><button onClick={() => props.onKeyClick("a", false)}>Select A</button><output aria-label="painted colors">{JSON.stringify(props.keyColorMap)}</output></div>,
}));

afterEach(() => vi.resetAllMocks());

const saved = {
  configuration: { id: "saved-1", keyboardId: demoKeyboard.id, keycapSetId: demoKeycapSet.id,
    keyColorMap: { a: "moss" }, name: "Moss accents", dateCreated: "2026-09-19T12:00:00Z" },
  keyboard: demoKeyboard, keycapSet: demoKeycapSet,
  compatibility: { compatible: false, status: "unknown" as const, missing: [], uncertain: [], warnings: [] },
};

function paint() {
  fireEvent.click(screen.getByRole("button", { name: "Select A" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
}

it("saves painted colors and restores them after resetting", async () => {
  vi.mocked(saveDesign).mockResolvedValue(saved);
  vi.mocked(restoreDesign).mockResolvedValue(saved);
  render(<SavedWorkbench />);
  paint();
  fireEvent.change(screen.getByLabelText("Design name (optional)"), { target: { value: "Moss accents" } });
  fireEvent.click(screen.getByRole("button", { name: "Save design" }));
  await screen.findByText(/Design saved locally/);
  expect(saveDesign).toHaveBeenCalledWith(demoKeyboard, demoKeycapSet, { a: "moss" }, "Moss accents", demoKeyboard.case.color);
  fireEvent.click(screen.getByRole("button", { name: "Reset board" }));
  expect(screen.getByLabelText("painted colors")).toHaveTextContent("{}");
  fireEvent.click(screen.getByRole("button", { name: "Restore selected design" }));
  await screen.findByText(/Design restored/);
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('{"a":"moss"}');
  expect(screen.getByRole("button", { name: "Clear selection" })).toBeDisabled();
});

it("loads saved designs in a new mount and restores a chosen snapshot", async () => {
  vi.mocked(listDesigns).mockResolvedValue([saved.configuration]);
  vi.mocked(restoreDesign).mockResolvedValue(saved);
  render(<SavedWorkbench />);
  expect(listDesigns).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Load saved designs" }));
  await screen.findByRole("option", { name: /Moss accents/ });
  fireEvent.click(screen.getByRole("button", { name: "Restore selected design" }));
  await waitFor(() => expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"'));
});

it("keeps painting and the current preview when saving fails", async () => {
  vi.mocked(saveDesign).mockRejectedValue(new Error("Backend unavailable"));
  render(<SavedWorkbench />);
  paint();
  fireEvent.click(screen.getByRole("button", { name: "Save design" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
  expect(screen.getByRole("button", { name: "Save design" })).not.toBeDisabled();
});

it("shows the empty library without clearing paint", async () => {
  vi.mocked(listDesigns).mockResolvedValue([]);
  render(<SavedWorkbench />);
  paint();
  fireEvent.click(screen.getByRole("button", { name: "Load saved designs" }));
  await screen.findByText("No saved designs yet.");
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
});

it("keeps unsaved paint when restoring fails", async () => {
  vi.mocked(listDesigns).mockResolvedValue([saved.configuration]);
  vi.mocked(restoreDesign).mockRejectedValue(new Error("Configuration not found"));
  render(<SavedWorkbench />);
  paint();
  fireEvent.click(screen.getByRole("button", { name: "Load saved designs" }));
  await screen.findByRole("option", { name: /Moss accents/ });
  fireEvent.click(screen.getByRole("button", { name: "Restore selected design" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Configuration not found");
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
});

it("switches board sizes offline, preserving shared paint and each board draft", () => {
  render(<SavedWorkbench />);
  paint();
  const board = screen.getByLabelText("Board size");
  expect(screen.getByRole("button", { name: "Function row" })).toBeDisabled();
  fireEvent.change(board, { target: { value: boardPresets[1].id } });
  expect(screen.getByRole("heading", { name: "ANSI 75 Preview" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Clear selection" })).toBeDisabled();
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
  fireEvent.click(screen.getByRole("button", { name: "Function row" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply Forest" }));
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"f12":"forest"');
  fireEvent.change(board, { target: { value: boardPresets[2].id } });
  expect(screen.getByRole("heading", { name: "ANSI TKL Preview" })).toBeInTheDocument();
  fireEvent.change(board, { target: { value: demoKeyboard.id } });
  expect(JSON.parse(screen.getByLabelText("painted colors").textContent!)).toEqual({ a: "moss" });
  fireEvent.change(board, { target: { value: boardPresets[1].id } });
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"f12":"forest"');
  expect(listDesigns).not.toHaveBeenCalled();
  expect(saveDesign).not.toHaveBeenCalled();
});

it("changes board case color without changing keycap paint or selection", () => {
  render(<SavedWorkbench />);
  paint();
  fireEvent.click(screen.getByRole("button", { name: "Board color White" }));
  expect(screen.getByLabelText("case color")).toHaveTextContent("#F5F5F5");
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
  expect(screen.getByRole("button", { name: "Clear selection" })).not.toBeDisabled();
  expect(screen.queryByLabelText("Color palette")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Custom board color"), { target: { value: "#123456" } });
  expect(screen.getByLabelText("case color")).toHaveTextContent("#123456");
  fireEvent.change(screen.getByLabelText("Board size"), { target: { value: boardPresets[1].id } });
  expect(screen.getByLabelText("case color")).toHaveTextContent("#123456");
});

it("saves a TKL case color independently of its immutable product and restores it", async () => {
  const snapshot = { ...saved, keyboard: boardPresets[2],
    configuration: { ...saved.configuration, keyboardId: boardPresets[2].id, caseColor: "#F5F5F5" } };
  vi.mocked(saveDesign).mockResolvedValue(snapshot);
  vi.mocked(restoreDesign).mockResolvedValue(snapshot);
  render(<SavedWorkbench />);
  paint();
  fireEvent.change(screen.getByLabelText("Board size"), { target: { value: boardPresets[2].id } });
  fireEvent.click(screen.getByRole("button", { name: "Board color White" }));
  fireEvent.click(screen.getByRole("button", { name: "Save design" }));
  await screen.findByText(/Design saved locally/);
  expect(saveDesign).toHaveBeenCalledWith(boardPresets[2], demoKeycapSet, { a: "moss" }, "", "#F5F5F5");
  fireEvent.click(screen.getByRole("button", { name: "Board color Black" }));
  fireEvent.click(screen.getByRole("button", { name: "Restore selected design" }));
  await screen.findByText(/Design restored/);
  expect(screen.getByLabelText("Board size")).toHaveValue(boardPresets[2].id);
  expect(screen.getByLabelText("case color")).toHaveTextContent("#F5F5F5");
  expect(screen.getByLabelText("painted colors")).toHaveTextContent('"a":"moss"');
});
