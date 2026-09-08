import { describe, expect, it } from "vitest";

import { demoKeycapSet } from "../src/data/demoKeycapSet";

describe("fixture keycap palette", () => {
  it("provides stable named colors for offline experimentation", () => {
    expect(demoKeycapSet.colors).toHaveLength(5);
    expect(new Set(demoKeycapSet.colors.map((color) => color.id)).size).toBe(5);
    expect(demoKeycapSet.colors.every((color) => /^#[0-9A-F]{6}$/.test(color.hex))).toBe(true);
  });
});
