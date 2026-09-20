import { expect, it } from "vitest";
import { boardPresets, boardColors } from "../src/data/presets";
import { demoKeycapSet } from "../src/data/demoKeycapSet";
import { adaptColors } from "../src/state/presets";

it("provides three distinct offline layouts with stable unique keys", () => {
  expect(boardPresets.map((board) => [board.layoutType, board.keys.length])).toEqual([["65", 68], ["75", 84], ["TKL", 87]]);
  expect(new Set(boardPresets.map((board) => board.id)).size).toBe(3);
  for (const board of boardPresets) {
    expect(new Set(board.keys.map((key) => key.id)).size).toBe(board.keys.length);
    for (const key of board.keys) {
      expect(key.group).toContain("entire-keyboard");
      expect(key.widthU).toBeGreaterThan(0);
    }
  }
});

it("provides named board colors with neutral gray and white", () => {
  expect(boardColors.length).toBe(9);
  for (const name of ["White", "Charcoal", "Black"]) {
    const hex = boardColors.find(([label]) => label === name)![1];
    expect(hex.slice(1, 3)).toBe(hex.slice(3, 5));
    expect(hex.slice(3, 5)).toBe(hex.slice(5, 7));
  }
});

it("carries only existing keys between boards without changing the input", () => {
  const map = { a: "bone", d: "forest", f12: "forest", missing: "bone" };
  expect(adaptColors(map, demoKeycapSet, demoKeycapSet, boardPresets[0])).toEqual({ a: "bone", d: "forest" });
  expect(map.f12).toBe("forest");
});
