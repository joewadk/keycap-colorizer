export interface KeyFitIssue {
  key: string;
  requiredWidthU: number;
  reason: string;
}

export interface CompatibilityResult {
  status: "compatible" | "incompatible" | "unknown";
  compatible: boolean;
  missing: KeyFitIssue[];
  uncertain: KeyFitIssue[];
  warnings: string[];
}
