import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { KeyboardWorkbench } from "../src/components/KeyboardWorkbench";
import { demoKeyboard } from "../src/data/demoKeyboard";

vi.mock("../src/renderer/KeyboardScene", () => ({
  KeyboardScene: (props: {
    selectedKeyIds: string[];
    keyColorMap: Record<string, string>;
    onKeyClick: (id: string, additive: boolean) => void;
  }) => (
    <div>
      <button onClick={() => props.onKeyClick("a", false)}>Select fixture A</button>
      <output aria-label="selection">{props.selectedKeyIds.join(",")}</output>
      <output aria-label="colors">{JSON.stringify(props.keyColorMap)}</output>
    </div>
  ),
}));

describe("KeyboardWorkbench", () => {
  it("disables the absent function row on the 65% board", () => {
    render(<KeyboardWorkbench />);
    const button = screen.getByRole("button", { name: "Function row" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-pressed", "false");
  });

  it("selects, paints, and deselects a present function row", () => {
    const keyboard = { ...demoKeyboard, keys: [
      ...demoKeyboard.keys,
      { ...demoKeyboard.keys[0], id: "f1", legend: "F1", group: ["function-row"] },
      { ...demoKeyboard.keys[0], id: "f2", legend: "F2", group: ["function-row"] },
    ] };
    render(<KeyboardWorkbench keyboard={keyboard} />);
    const button = screen.getByRole("button", { name: "Function row" });
    fireEvent.click(button);
    expect(screen.getByLabelText("selection")).toHaveTextContent("f1,f2");
    fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
    expect(JSON.parse(screen.getByLabelText("colors").textContent!)).toEqual({ f1: "moss", f2: "moss" });
    fireEvent.click(button);
    expect(screen.getByLabelText("selection")).toBeEmptyDOMElement();
  });
  it("toggles the active group off without removing its colors", () => {
    render(<KeyboardWorkbench />);
    fireEvent.click(screen.getByRole("button", { name: "WASD" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
    const colors = screen.getByLabelText("colors").textContent;
    fireEvent.click(screen.getByRole("button", { name: "WASD" }));
    expect(screen.getByLabelText("selection")).toBeEmptyDOMElement();
    expect(screen.getByRole("button", { name: "WASD" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByLabelText("colors").textContent).toBe(colors);
    expect(screen.getByRole("button", { name: "Apply Moss" })).toBeDisabled();
  });

  it("clears an individual selection without resetting paint", () => {
    render(<KeyboardWorkbench />);
    const clear = screen.getByRole("button", { name: "Clear selection" });
    expect(clear).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Select fixture A" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
    fireEvent.click(clear);
    expect(screen.getByLabelText("selection")).toBeEmptyDOMElement();
    expect(screen.getByLabelText("colors")).toHaveTextContent('{"a":"moss"}');
    expect(clear).toBeDisabled();
  });

  it("shows every available palette color", () => {
    render(<KeyboardWorkbench />);
    for (const name of ["Bone", "Moss", "Forest", "Clay", "Charcoal"]) {
      expect(screen.getByRole("button", { name: `Apply ${name}` })).toBeInTheDocument();
    }
  });

  it("paints a selected key and can reset the board", () => {
    render(<KeyboardWorkbench />);
    fireEvent.click(screen.getByRole("button", { name: "Select fixture A" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply Moss" }));
    expect(screen.getByLabelText("colors")).toHaveTextContent('{"a":"moss"}');

    fireEvent.click(screen.getByRole("button", { name: "Reset board" }));
    expect(screen.getByLabelText("colors")).toHaveTextContent("{}");
  });

  it("selects the WASD preset", () => {
    render(<KeyboardWorkbench />);
    fireEvent.click(screen.getByRole("button", { name: "WASD" }));
    expect(screen.getByLabelText("selection")).toHaveTextContent("w,a,s,d");
  });

  it("switches groups immediately and paints only the new selection", () => {
    render(<KeyboardWorkbench />);
    fireEvent.click(screen.getByRole("button", { name: "Alphas" }));
    expect(screen.getByRole("button", { name: "Alphas" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Modifiers" }));
    expect(screen.getByRole("button", { name: "Alphas" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Modifiers" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("status", { name: "Selection summary" })).toHaveTextContent(/Modifiers.*keys selected/);
    fireEvent.click(screen.getByRole("button", { name: "Apply Charcoal" }));
    const assignments = JSON.parse(screen.getByLabelText("colors").textContent!);
    expect(assignments["left-shift"]).toBe("charcoal");
    expect(assignments.a).toBeUndefined();
    expect(screen.getByRole("button", { name: "Apply Charcoal" })).toHaveAttribute("aria-pressed", "true");
  });
});
