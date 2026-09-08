import { describe, expect, it } from "vitest";

import { demoKeyboard } from "../src/data/demoKeyboard";
import {
  applyColor,
  clearSelection,
  initialConfiguratorState,
  resetKeyboard,
  resetSelectedKeys,
  selectGroup,
  selectKey,
} from "../src/state/configurator";

describe("configurator state", () => {
  it("selects one key and replaces the previous selection", () => {
    const first = selectKey(initialConfiguratorState, "esc");
    expect(selectKey(first, "a").selectedKeyIds).toEqual(["a"]);
  });

  it("toggles keys during additive selection", () => {
    const first = selectKey(initialConfiguratorState, "a");
    const second = selectKey(first, "b", true);
    expect(second.selectedKeyIds).toEqual(["a", "b"]);
    expect(selectKey(second, "a", true).selectedKeyIds).toEqual(["b"]);
  });

  it("selects every key in a logical group", () => {
    const state = selectGroup(initialConfiguratorState, demoKeyboard.keys, "wasd");
    expect(new Set(state.selectedKeyIds)).toEqual(new Set(["w", "a", "s", "d"]));
  });

  it("applies a color only to selected keys without mutating prior state", () => {
    const selected = { selectedKeyIds: ["esc", "enter"], keyColorMap: { a: "warm" } };
    const painted = applyColor(selected, "moss");
    expect(painted.keyColorMap).toEqual({ a: "warm", esc: "moss", enter: "moss" });
    expect(selected.keyColorMap).toEqual({ a: "warm" });
  });

  it("clears selection without clearing color assignments", () => {
    const state = { selectedKeyIds: ["esc"], keyColorMap: { esc: "moss" } };
    expect(clearSelection(state)).toEqual({ selectedKeyIds: [], keyColorMap: { esc: "moss" } });
  });

  it("provides a complete 68-key offline fixture", () => {
    expect(demoKeyboard.keys).toHaveLength(68);
    expect(new Set(demoKeyboard.keys.map((key) => key.id)).size).toBe(68);
  });

  it("resets only selected keys to their default color", () => {
    const state = {
      selectedKeyIds: ["esc", "enter"],
      keyColorMap: { esc: "moss", enter: "forest", a: "clay" },
    };
    expect(resetSelectedKeys(state).keyColorMap).toEqual({ a: "clay" });
  });

  it("resets every key while preserving selection", () => {
    const state = { selectedKeyIds: ["esc"], keyColorMap: { esc: "moss", a: "clay" } };
    expect(resetKeyboard(state)).toEqual({ selectedKeyIds: ["esc"], keyColorMap: {} });
  });
});
