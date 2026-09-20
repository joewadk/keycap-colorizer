import type { KeyboardDefinition, KeycapSet, KeyColorMap } from "../types/domain";

export function draftKey(keyboard: KeyboardDefinition, palette: KeycapSet): string {
  return JSON.stringify([keyboard.id, palette.id]);
}

export function adaptColors(mapping: KeyColorMap, from: KeycapSet, to: KeycapSet, keyboard: KeyboardDefinition): KeyColorMap {
  const keys = new Set(keyboard.keys.map((key) => key.id));
  const oldColors = new Map(from.colors.map((color) => [color.id, color.hex.toUpperCase()]));
  const newColors = new Map(to.colors.map((color) => [color.hex.toUpperCase(), color.id]));
  return Object.fromEntries(Object.entries(mapping).flatMap(([keyId, colorId]) => {
    const target = newColors.get(oldColors.get(colorId) ?? "");
    return keys.has(keyId) && target ? [[keyId, target]] : [];
  }));
}
