import type { CompatibilityResult } from "../types/compatibility";
import type { KeyboardDefinition, KeycapSet } from "../types/domain";

export type WorkflowStep =
  | "QUEUED" | "CHECKING_CACHE" | "FETCHING_PAGE" | "EXTRACTING_METADATA"
  | "CLASSIFYING_PRODUCT" | "ANALYZING_LAYOUT" | "EXTRACTING_COLORS"
  | "VALIDATING" | "SAVING" | "COMPLETE" | "NEEDS_REVIEW" | "FAILED";

export interface ProgressEvent {
  step: WorkflowStep;
  message: string;
  occurredAt: string;
}

export interface PageEvidenceSummary {
  sourceUrl: string;
  finalUrl: string;
  title?: string | null;
  warnings: string[];
}

export interface IntakeResult {
  keyboard: KeyboardDefinition;
  keycapSet: KeycapSet;
  compatibility: CompatibilityResult;
  warnings: string[];
  cachedProducts: Array<"keyboard" | "keycaps">;
}

export interface IntakeJob {
  id: string;
  status: "queued" | "running" | "complete" | "needs_review" | "failed";
  step: WorkflowStep;
  events: ProgressEvent[];
  message: string;
  result?: IntakeResult | null;
  reviewEvidence: PageEvidenceSummary[];
}

export interface FixtureCatalog {
  keyboardUrl: string;
  keycapUrl: string;
  message: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  try {
    const response = await fetch(`/api/${path}`, options);
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(typeof error?.detail === "string" ? error.detail : `Product intake failed (HTTP ${response.status}).`);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof TypeError || (error instanceof Error && error.name === "AbortError")) {
      throw new Error("Product intake service is unavailable. Start the backend and try again.");
    }
    throw error;
  }
}

export function fixtureCatalog(signal?: AbortSignal) {
  return request<FixtureCatalog>("ingestion/fixtures", { signal });
}

export function createIntake(keyboardUrl: string, keycapUrl: string, provider: "playwright" | "firecrawl", signal?: AbortSignal) {
  return request<IntakeJob>("products/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyboardUrl, keycapUrl, provider }),
    signal,
  });
}

export function intakeStatus(id: string, signal?: AbortSignal) {
  return request<IntakeJob>(`products/ingest/${encodeURIComponent(id)}`, { signal });
}
