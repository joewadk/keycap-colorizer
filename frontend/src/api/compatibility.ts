import type { KeyboardDefinition, KeycapSet } from "../types/domain";
import type { CompatibilityResult } from "../types/compatibility";

export async function checkCompatibility(
  keyboard: KeyboardDefinition,
  keycapSet: KeycapSet,
  signal: AbortSignal,
): Promise<CompatibilityResult> {
  const response = await fetch("/api/compatibility/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyboard, keycapSet }),
    signal,
  });
  if (!response.ok) throw new Error(`Fit check failed (${response.status}).`);
  return response.json() as Promise<CompatibilityResult>;
}
