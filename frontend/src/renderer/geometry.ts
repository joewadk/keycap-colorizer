import type { KeyboardDefinition, KeyboardKey } from "../types/domain";

export const KEYBOARD_UNIT_MM = 19.05;
export const KEY_GAP_MM = 1.05;
export const KEYCAP_HEIGHT_MM = 8;

export interface KeyTransform {
  position: [number, number, number];
  size: [number, number, number];
}

export function buildKeyTransform(key: KeyboardKey): KeyTransform {
  const width = key.widthU * KEYBOARD_UNIT_MM - KEY_GAP_MM;
  const depth = key.heightU * KEYBOARD_UNIT_MM - KEY_GAP_MM;

  return {
    position: [
      (key.x + key.widthU / 2) * KEYBOARD_UNIT_MM,
      KEYCAP_HEIGHT_MM / 2,
      (key.y + key.heightU / 2) * KEYBOARD_UNIT_MM,
    ],
    size: [width, KEYCAP_HEIGHT_MM, depth],
  };
}

export function buildKeyboardTransforms(
  keyboard: KeyboardDefinition,
): Record<string, KeyTransform> {
  return Object.fromEntries(
    keyboard.keys.map((key) => [key.id, buildKeyTransform(key)]),
  );
}

