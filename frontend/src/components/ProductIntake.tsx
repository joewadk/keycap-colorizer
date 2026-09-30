import { useEffect, useRef, useState } from "react";

import { createIntake, fixtureCatalog, intakeStatus, type IntakeJob, type IntakeResult } from "../api/ingestion";

interface ProductIntakeProps {
  onComplete: (result: IntakeResult) => void;
}

const pause = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const readerPreferenceKey = "keycap-colorizer.page-reader";

function savedReader(): "playwright" | "firecrawl" {
  try {
    return sessionStorage.getItem(readerPreferenceKey) === "firecrawl" ? "firecrawl" : "playwright";
  } catch {
    return "playwright";
  }
}

export function ProductIntake({ onComplete }: ProductIntakeProps) {
  const [keyboardUrl, setKeyboardUrl] = useState("");
  const [keycapUrl, setKeycapUrl] = useState("");
  const [provider, setProvider] = useState<"playwright" | "firecrawl">(savedReader);
  const [job, setJob] = useState<IntakeJob | null>(null);
  const [message, setMessage] = useState("Paste two public product links, or load the offline demo products.");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  async function useDemo() {
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true);
    setError(false);
    try {
      const fixture = await fixtureCatalog(controller.current.signal);
      setKeyboardUrl(fixture.keyboardUrl);
      setKeycapUrl(fixture.keycapUrl);
      setMessage(fixture.message);
    } catch (failure) {
      setError(true);
      setMessage(failure instanceof Error ? failure.message : "Could not load the demo products.");
    } finally {
      setBusy(false);
    }
  }

  async function analyze() {
    if (keyboardUrl.trim() === keycapUrl.trim()) {
      setError(true);
      setMessage("Use two different product pages: a keyboard in the first field and a keycap set in the second.");
      return;
    }
    controller.current?.abort();
    controller.current = new AbortController();
    const signal = controller.current.signal;
    setBusy(true);
    setError(false);
    setJob(null);
    setMessage("Starting local product intake…");
    try {
      let current = await createIntake(keyboardUrl, keycapUrl, provider, signal);
      setJob(current);
      while (current.status === "queued" || current.status === "running") {
        await pause(200);
        current = await intakeStatus(current.id, signal);
        setJob(current);
      }
      if (current.status === "complete" && current.result) {
        onComplete(current.result);
        setMessage(current.result.cachedProducts.length === 2
          ? "Loaded both normalized products from the local cache."
          : "Products analyzed and loaded into the workbench.");
      } else {
        setError(current.status === "failed");
        setMessage(`${current.message} The current preview was not changed.`);
      }
    } catch (failure) {
      if (!signal.aborted) {
        setError(true);
        setMessage(failure instanceof Error ? failure.message : "Product intake failed.");
      }
    } finally {
      if (!signal.aborted) setBusy(false);
    }
  }

  return <section className="intake" aria-labelledby="intake-title">
    <header>
      <span>01</span>
      <div><p className="eyebrow">PRODUCT INTAKE</p><h2 id="intake-title">Start with two links</h2></div>
    </header>
    <label>Keyboard product URL
      <input type="url" value={keyboardUrl} placeholder="https://…" disabled={busy}
        onChange={(event) => setKeyboardUrl(event.target.value)} />
    </label>
    <label>Keycap product URL
      <input type="url" value={keycapUrl} placeholder="https://…" disabled={busy}
        onChange={(event) => setKeycapUrl(event.target.value)} />
    </label>
    <label>Page reader
      <select value={provider} disabled={busy} onChange={(event) => {
        const reader = event.target.value as "playwright" | "firecrawl";
        setProvider(reader);
        try { sessionStorage.setItem(readerPreferenceKey, reader); } catch { /* Storage may be disabled. */ }
      }}>
        <option value="playwright">Playwright · local browser</option>
        <option value="firecrawl">Firecrawl · API key required</option>
      </select>
    </label>
    <p className="intake-message">{provider === "firecrawl"
      ? "Using Firecrawl. Uncached pages use your Firecrawl credits."
      : "Using Playwright on this computer. Choose Firecrawl above to use your Firecrawl account."}</p>
    <div className="intake-actions">
      <button type="button" className="secondary-button" disabled={busy} onClick={() => void useDemo()}>Use offline demo</button>
      <button type="button" disabled={busy || !keyboardUrl.trim() || !keycapUrl.trim()} onClick={() => void analyze()}>
        {busy && job ? "Analyzing…" : "Analyze products"}
      </button>
    </div>
    {job && <ol className="progress-list" aria-label="Product intake progress">
      {job.events.map((event, index) => <li key={`${event.occurredAt}-${index}`} className={index === job.events.length - 1 ? "current" : ""}>
        <span>{event.step.replaceAll("_", " ")}</span>{event.message}
      </li>)}
    </ol>}
    {job?.status === "needs_review" && job.reviewEvidence.map((evidence) =>
      <p className="review-evidence" key={evidence.sourceUrl}>Review: {evidence.title || evidence.finalUrl}</p>)}
    <p role={error ? "alert" : "status"} className="intake-message">{message}</p>
  </section>;
}
