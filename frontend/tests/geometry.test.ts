import { describe, expect, it } from "vitest";

import {
  buildKeyboardTransforms,
  buildKeyTransform,
  KEYBOARD_UNIT_MM,
  KEY_GAP_MM,
} from "../src/renderer/geometry";
import type { KeyboardDefinition, KeyboardKey } from "../src/types/domain";

function makeKey(overrides: Partial<KeyboardKey> = {}): KeyboardKey {
  return {
    id: "a",
    legend: "A",
    row: 0,
    x: 0,
    y: 0,
    widthU: 1,
    heightU: 1,
    stabilizer: false,
    group: ["alphas"],
    ...overrides,
  };
}

describe("keyboard geometry", () => {
  it("converts a 1u key to millimeters with a physical gap", () => {
    const transform = buildKeyTransform(makeKey());
    expect(transform.size[0]).toBe(KEYBOARD_UNIT_MM - KEY_GAP_MM);
    expect(transform.size[2]).toBe(KEYBOARD_UNIT_MM - KEY_GAP_MM);
    expect(transform.position[0]).toBe(KEYBOARD_UNIT_MM / 2);
  });

  it("centers a 1.75u key on its occupied unit span", () => {
    const transform = buildKeyTransform(makeKey({ x: 12, widthU: 1.75 }));
    expect(transform.size[0]).toBeCloseTo(1.75 * KEYBOARD_UNIT_MM - KEY_GAP_MM);
    expect(transform.position[0]).toBeCloseTo((12 + 0.875) * KEYBOARD_UNIT_MM);
  });

  it("keeps adjacent key centers exactly one unit apart", () => {
    const first = buildKeyTransform(makeKey({ id: "a", x: 0 }));
    const second = buildKeyTransform(makeKey({ id: "b", x: 1 }));
    expect(second.position[0] - first.position[0]).toBeCloseTo(KEYBOARD_UNIT_MM);
  });

  it("uses unit row offsets on the scene depth axis", () => {
    const first = buildKeyTransform(makeKey({ y: 2 }));
    const second = buildKeyTransform(makeKey({ y: 3 }));
    expect(second.position[2] - first.position[2]).toBeCloseTo(KEYBOARD_UNIT_MM);
  });

  it("creates a stable transform lookup keyed by key ID", () => {
    const keyboard = {
      keys: [makeKey({ id: "space", widthU: 6.25 })],
    } as KeyboardDefinition;
    const transforms = buildKeyboardTransforms(keyboard);
    expect(Object.keys(transforms)).toEqual(["space"]);
    expect(transforms.space.size[0]).toBeCloseTo(6.25 * KEYBOARD_UNIT_MM - KEY_GAP_MM);
  });
});
