import { useEffect, useState } from "react";
import { checkCompatibility } from "../api/compatibility";
import type { KeyboardDefinition, KeycapSet } from "../types/domain";
import type { CompatibilityResult } from "../types/compatibility";

type CheckState = { status: "loading" } | { status: "error"; message: string }
  | { status: "ready"; result: CompatibilityResult };

export function CompatibilityPanel({ keyboard, keycapSet }: {
  keyboard: KeyboardDefinition;
  keycapSet: KeycapSet;
}) {
  const [state, setState] = useState<CheckState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    if (!keycapSet.supportedKeys.length) return () => controller.abort();
    setState({ status: "loading" });
    checkCompatibility(keyboard, keycapSet, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setState({ status: "ready", result }); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setState({ status: "error", message: error instanceof Error ? error.message : "Could not check fit." });
      });
    return () => controller.abort();
  }, [keyboard, keycapSet, attempt]);

  const result = state.status === "ready" ? state.result : null;
  return (
    <section className="compatibility-panel" aria-label="Keycap compatibility" aria-live="polite">
      <h3>Keycap fit</h3>
      {!keycapSet.supportedKeys.length ? (
        <p>Fit not verified: this sample palette has no key inventory.</p>
      ) : state.status === "loading" ? (
        <p>Checking key sizes and quantities…</p>
      ) : state.status === "error" ? (
        <>
          <p>Fit check unavailable. {state.message} Check that the local backend is running.</p>
          <button className="chip" onClick={() => setAttempt((value) => value + 1)}>Retry fit check</button>
        </>
      ) : result && (
        <>
          <p>{result.status === "compatible" ? "Size and quantity checks passed."
            : result.status === "incompatible" ? "Some required keycaps are missing."
            : "Fit not verified: some kit details are incomplete."}</p>
          {result.missing.length > 0 && (
            <details open>
              <summary>{result.missing.length} missing keycaps</summary>
              <ul>{result.missing.map((issue) => (
                <li key={issue.key}>{issue.key} — {issue.requiredWidthU}u: {issue.reason}</li>
              ))}</ul>
            </details>
          )}
          {result.uncertain.length > 0 && (
            <details>
              <summary>{result.uncertain.length} keys need more information</summary>
              <ul>{result.uncertain.map((issue) => (
                <li key={issue.key}>{issue.key} — {issue.requiredWidthU}u: {issue.reason}</li>
              ))}</ul>
            </details>
          )}
          {result.warnings.map((warning) => <p key={warning}>{warning}</p>)}
        </>
      )}
      <p className="compatibility-note">You can keep experimenting with colors regardless of fit.</p>
    </section>
  );
}
