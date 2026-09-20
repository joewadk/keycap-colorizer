import type { KeyboardDefinition } from "../types/domain";
import generatedBoards from "./boardPresets.json";
import { demoKeyboard } from "./demoKeyboard";

// JSON snapshots are generated from backend canonical templates; backend tests enforce parity.
// Keep the original 65% fixture unchanged so previously saved immutable products still import.
export const boardPresets: KeyboardDefinition[] = [demoKeyboard, ...generatedBoards as KeyboardDefinition[]];

export const boardColors = [
  ["Black", "#111111"], ["Charcoal", "#333333"], ["Silver", "#BFC3C7"],
  ["White", "#F5F5F5"], ["Cream", "#E8DDC5"], ["Navy", "#253B63"],
  ["Green", "#2F5141"], ["Red", "#A93434"], ["Purple", "#71549A"],
] as const;
