import type { KeycapColor, KeyboardDefinition, KeycapSet } from "../types/domain";

export interface ProductPatch {
  keyboard?: KeyboardDefinition | null;
  keycapSet?: KeycapSet | null;
  caseColor?: string | null;
  keyColorMap?: Record<string, string>;
  targetKeyboardId?: string;
  warnings: string[];
}
export type Kind = "keyboard" | "keycaps";
export type Layout = "ANSI_65" | "ANSI_75" | "ANSI_TKL";
export interface Review {
  id: string; kind: Kind; title: string; sourceUrl: string;
  images: { url: string; alt: string }[]; variants: string[];
  layout: Layout | null; colors: KeycapColor[]; warnings: string[]; cached: boolean;
}
export interface Crop { left: number; top: number; right: number; bottom: number }
export interface Proposal { id: string; colors: KeycapColor[]; warnings: string[]; imageIndex: number; crop: Crop }

export async function reviewRequest<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener("abort", cancel, { once: true });
  if (signal?.aborted) controller.abort();
  const timeout = setTimeout(cancel, 90_000);
  try {
    const response = await fetch(`/api/ingestion/${path}`, {
      signal: controller.signal,
      ...(body === undefined ? {} : {
        method: "POST",
        headers: body instanceof File ? { "Content-Type": "application/octet-stream" } : { "Content-Type": "application/json" },
        body: body instanceof File ? body : JSON.stringify(body),
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(typeof error?.detail === "string" ? error.detail : `Product review failed (HTTP ${response.status}).`);
    }
    return await response.json() as T;
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted) throw new Error("Product review timed out. Try again or upload a photo.");
    throw error;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", cancel);
  }
}
