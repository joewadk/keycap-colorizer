import type { Configuration, KeyboardDefinition, KeycapSet, KeyColorMap } from "../types/domain";
import type { CompatibilityResult } from "../types/compatibility";

export interface RestoredConfiguration {
  configuration: Configuration;
  keyboard: KeyboardDefinition;
  keycapSet: KeycapSet;
  compatibility: CompatibilityResult;
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`/api/${path}`, {
      signal: controller.signal,
      ...(body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(typeof error?.detail === "string" ? error.detail : `Local storage request failed (HTTP ${response.status}).`);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
      throw new Error("Local storage is unavailable. Start the backend and try again; your preview is unchanged.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function saveDesign(keyboard: KeyboardDefinition, keycapSet: KeycapSet, keyColorMap: KeyColorMap, name: string, caseColor?: string) {
  await request("products/manual", { kind: "keyboard", product: keyboard });
  await request("products/manual", { kind: "keycaps", product: keycapSet });
  return request<RestoredConfiguration>("configurations", { keyboardId: keyboard.id, keycapSetId: keycapSet.id, keyColorMap, name: name.trim() || null, caseColor });
}

export function listDesigns() {
  return request<Configuration[]>("configurations?limit=50");
}

export function restoreDesign(id: string) {
  return request<RestoredConfiguration>(`configurations/${encodeURIComponent(id)}`);
}
