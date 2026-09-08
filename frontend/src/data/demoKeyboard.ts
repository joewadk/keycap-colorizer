import type { KeyboardDefinition, KeyboardKey } from "../types/domain";

type Spec = [id: string, legend: string, width?: number];

const k = (id: string, legend: string, width = 1): Spec => [id, legend, width];
const letters = (values: string) => [...values].map((value) => k(value.toLowerCase(), value));

const rows: Spec[][] = [
  [
    k("grave", "`"), ...[..."1234567890"].map((n) => k(`digit-${n}`, n)),
    k("minus", "-"), k("equal", "="), k("backspace", "Backspace", 2),
    k("home", "Home"),
  ],
  [
    k("tab", "Tab", 1.5), ...letters("QWERTYUIOP"), k("bracket-left", "["),
    k("bracket-right", "]"), k("backslash", "\\", 1.5), k("page-up", "PgUp"),
  ],
  [
    k("caps-lock", "Caps", 1.75), ...letters("ASDFGHJKL"), k("semicolon", ";"),
    k("quote", "'"), k("enter", "Enter", 2.25), k("page-down", "PgDn"),
  ],
  [
    k("left-shift", "Shift", 2.25), ...letters("ZXCVBNM"), k("comma", ","),
    k("period", "."), k("slash", "/"), k("right-shift", "Shift", 1.75),
    k("arrow-up", "↑"), k("end", "End"),
  ],
  [
    k("left-control", "Ctrl", 1.25), k("left-meta", "Win", 1.25),
    k("left-alt", "Alt", 1.25), k("space", "", 6.25), k("right-alt", "Alt"),
    k("function", "Fn"), k("right-control", "Ctrl"), k("arrow-left", "←"),
    k("arrow-down", "↓"), k("arrow-right", "→"),
  ],
];

const modifierIds = new Set([
  "tab", "caps-lock", "backspace", "enter", "left-shift", "right-shift", "space",
  "left-control", "right-control", "left-meta", "left-alt", "right-alt", "function",
]);
const navIds = new Set(["home", "page-up", "page-down", "end"]);

function groups(id: string): string[] {
  const result = ["entire-keyboard"];
  if (id.length === 1 && /[a-z]/.test(id)) result.push("alphas");
  if (["w", "a", "s", "d"].includes(id)) result.push("wasd");
  if (id.startsWith("arrow-")) result.push("arrow-keys");
  if (navIds.has(id)) result.push("navigation-cluster");
  if (modifierIds.has(id)) result.push("modifiers");
  return result;
}

const keys: KeyboardKey[] = rows.flatMap((row, rowIndex) => {
  let x = 0;
  return row.map(([id, legend, width = 1], index) => {
    if (index === row.length - 1 && rowIndex < 3) x += 0.25;
    if (rowIndex === 3 && id === "arrow-up") x += 0.25;
    if (rowIndex === 4 && id === "arrow-left") x += 0.25;
    const value: KeyboardKey = {
      id,
      legend,
      row: rowIndex,
      x,
      y: rowIndex,
      widthU: width,
      heightU: 1,
      stabilizer: width >= 2,
      group: groups(id),
    };
    x += width;
    return value;
  });
});

export const demoKeyboard: KeyboardDefinition = {
  id: "demo-ansi-65",
  manufacturer: "Local Fixture",
  model: "ANSI 65 Preview",
  layoutType: "65",
  case: { color: "#303735", widthMm: 324, depthMm: 105, cornerRadiusMm: 6 },
  keys,
  features: { knob: false, screen: false, badge: false },
  sourceUrl: "https://example.com/fixtures/ansi-65",
};
