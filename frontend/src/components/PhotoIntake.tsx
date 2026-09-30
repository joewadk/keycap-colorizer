import { useEffect, useRef, useState } from "react";
import { reviewRequest, type Crop, type Kind, type Layout, type ProductPatch, type Proposal, type Review } from "../api/photoReview";
import type { KeyboardDefinition } from "../types/domain";
import { demoKeyboard } from "../data/demoKeyboard";
import { PhotoKeyMap } from "./PhotoKeyMap";

function stored(key: string, fallback = "") {
  try { return sessionStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
function remember(key: string, value: string) {
  try { sessionStorage.setItem(key, value); } catch { /* Storage is optional. */ }
}
const fullCrop: Crop = { left: 0, top: 0, right: 1, bottom: 1 };

function ProductReview({ kind, provider, ready, onApply, keyboard }: {
  kind: Kind; provider: string; ready: boolean; onApply: (patch: ProductPatch) => void; keyboard: KeyboardDefinition;
}) {
  const label = kind === "keyboard" ? "Keyboard" : "Keycaps";
  const [url, setUrl] = useState(() => stored(`keycap-colorizer.${kind}-url`));
  const [review, setReview] = useState<Review | null>(null);
  const [name, setName] = useState("");
  const [variant, setVariant] = useState("");
  const [layout, setLayout] = useState<Layout | "">("");
  const [imageIndex, setImageIndex] = useState(0);
  const [imageReady, setImageReady] = useState(false);
  const [crop, setCrop] = useState<Crop>(fullCrop);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [explicit, setExplicit] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const [mode, setMode] = useState("quick");
  const [strategy, setStrategy] = useState("scheme");
  const [fitWarnings, setFitWarnings] = useState<string[]>([]);
  const perKey = kind === "keycaps" && mode !== "palette";
  const quick = kind === "keycaps" && mode === "quick";
  const [destination, setDestination] = useState(keyboard.keys[0].id);
  const [assignments, setAssignments] = useState<Record<string, { sampleId: string; colorId: string; hex: string }>>({});
  const targetLayout = ({ "65": "ANSI_65", "75": "ANSI_75", "TKL": "ANSI_TKL" } as Record<string, Layout>)[keyboard.layoutType];
  const controller = useRef<AbortController | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (kind === "keycaps") { controller.current?.abort(); setBusy(false); setAssignments({}); setDestination(keyboard.keys[0].id); invalidate(); }
  }, [keyboard.id]);

  function invalidate(clearQuick = true) {
    setProposal(null); setExplicit(false); setSelected([]);
    if (quick && clearQuick) { setAssignments({}); setFitWarnings([]); }
  }
  function chooseImage(index: number) {
    setImageIndex(index); setImageReady(false); setCrop(fullCrop); invalidate();
  }
  function receive(value: Review) {
    setReview(value); setName(value.title.slice(0, 200)); setVariant(""); setLayout(value.layout ?? "");
    chooseImage(0);
  }
  async function perform(action: (signal: AbortSignal) => Promise<void>, status: string) {
    controller.current?.abort();
    const next = new AbortController(); controller.current = next;
    setBusy(true); setError(false); setMessage(status);
    try { await action(next.signal); }
    catch (failure) {
      if (!next.signal.aborted) {
        setError(true);
        setMessage(failure instanceof Error ? failure.message : "Local service unavailable. Start the backend and try again.");
      }
    } finally { if (!next.signal.aborted) setBusy(false); }
  }
  async function read(source: string) {
    // Clear previous evidence so a failed new URL cannot leave the old product looking current.
    setReview(null); setAssignments({}); invalidate();
    await perform(async (signal) => {
      const value = await reviewRequest<Review>("reviews", { kind, url: source, provider }, signal);
      receive(value);
      setMessage(`${label} ready for review. Choose the photo matching the variant you want.`);
    }, `Reading ${label.toLowerCase()} with ${provider === "firecrawl" ? "Firecrawl" : "Playwright"}…`);
  }
  async function upload(file: File) {
    if (file.size > 8_000_000) { setError(true); setMessage("Photo exceeds the 8 MB limit."); return; }
    await perform(async (signal) => {
      const current = review ?? await reviewRequest<Review>("reviews", { kind, url, manual: true }, signal);
      const result = await reviewRequest<{ review: Review; imageIndex: number }>(`reviews/${current.id}/upload`, file, signal);
      if (!review) receive(result.review); else setReview(result.review);
      chooseImage(result.imageIndex);
      setMessage("Photo uploaded locally. Crop the surface you want to sample.");
    }, "Loading your photo…");
  }
  const colors = explicit ? review?.colors ?? [] : proposal?.colors ?? [];
  const validCrop = crop.left < crop.right && crop.top < crop.bottom;
  async function apply(layoutOnly = false, mapped = false) {
    if (!review) return;
    await perform(async (signal) => {
      const result = await reviewRequest<ProductPatch>(`reviews/${review.id}/confirm`, {
        name, variant, layout: mapped ? targetLayout : layout || null,
        sampleId: layoutOnly || mapped ? null : proposal?.id ?? null,
        useExplicitColors: !layoutOnly && !mapped && explicit,
        colorIds: layoutOnly || mapped ? [] : selected,
        keySamples: mapped ? Object.fromEntries(Object.entries(assignments).map(([key, { sampleId, colorId }]) => [key, { sampleId, colorId }])) : {},
      }, signal);
      onApply(mapped ? { ...result, targetKeyboardId: keyboard.id } : result);
      setMessage(layoutOnly ? "Keyboard layout applied. The current case color is retained until you apply a sampled color."
        : `${label} applied to the preview. Save your design below to keep it.`);
    }, "Applying reviewed product…");
  }

  return <article className="product-review" aria-label={`${label} review`}>
    <h3>{label}</h3>
    <label>{kind === "keyboard" ? "Keyboard product URL" : "Keycap product URL"}
      <input type="url" value={url} disabled={busy} onChange={(event) => {
        setUrl(event.target.value); remember(`keycap-colorizer.${kind}-url`, event.target.value);
        setReview(null); setAssignments({}); invalidate(); setMessage("");
      }} />
    </label>
    <div className="chip-row">
      <button disabled={!ready || busy || !url.trim()} onClick={() => void read(url)}>Read {kind}</button>
      <button className="secondary-button" disabled={!ready || busy} onClick={() => fileInput.current?.click()}>Upload {kind} photo</button>
      <button className="text-button" disabled={!ready || busy} onClick={() => {
        const demo = `https://fixtures.keycap.test/products/${kind === "keyboard" ? "ansi-75" : "botanical-keycaps"}`;
        setUrl(demo); remember(`keycap-colorizer.${kind}-url`, demo); void read(demo);
      }}>Try demo {kind}</button>
    </div>
    <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="visually-hidden"
      aria-label={`Upload ${kind} image file`} disabled={!ready || busy} onChange={(event) => {
        const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = "";
      }} />
    {review && <>
      <label>{label} name<input maxLength={200} value={name} disabled={busy} onChange={(e) => setName(e.target.value)} /></label>
      <label>{label} variant / finish<input maxLength={200} value={variant} disabled={busy} list={`${kind}-variants`}
        placeholder="Name the variant shown in your selected photo" onChange={(e) => setVariant(e.target.value)} /></label>
      <datalist id={`${kind}-variants`}>{review.variants.map((value, index) => <option key={index} value={value} />)}</datalist>
      <p className="intake-message">Photos can show different variants. Confirm that your photo matches the finish above.</p>
      {kind === "keyboard" && <>
        <label>Reviewed keyboard layout<select value={layout} disabled={busy} onChange={(e) => setLayout(e.target.value as Layout | "")}>
          <option value="">Choose a supported layout</option><option value="ANSI_65">ANSI 65%</option>
          <option value="ANSI_75">ANSI 75%</option><option value="ANSI_TKL">ANSI TKL</option>
        </select></label>
        <button disabled={busy || !name.trim() || !layout} onClick={() => void apply(true)}>Preview keyboard layout</button>
      </>}
      {review.images.length > 0 && <>
        <label>{label} photo<select value={imageIndex} disabled={busy} onChange={(e) => chooseImage(Number(e.target.value))}>
          {review.images.map((image, index) => <option key={index} value={index}>Photo {index + 1}{image.alt ? ` · ${image.alt.slice(0, 90)}` : ""}</option>)}
        </select></label>
        <p className="intake-message">{review.images.length} photos available · loaded only when selected.</p>
        {kind === "keycaps" && <>
          <label>Keycap picking mode<select value={mode} disabled={busy}
            onChange={(e) => { setMode(e.target.value); invalidate(false); }}>
            <option value="quick" disabled={!targetLayout}>Quick select · fit photo colors</option>
            <option value="per-key" disabled={!targetLayout}>Manual · per-key colors · ANSI {keyboard.layoutType}</option>
            <option value="palette">Shared palette</option>
          </select></label>
          {perKey && <>
            <p>{keyboard.model} · {keyboard.keys.length} keys. {quick
              ? "Choose a photo below, then Quick fit colors to suggest a complete scheme. Click any destination key to switch to manual corrections."
              : "Choose a destination key, then click its surface in the photo or drag a crop. Sample, review, and assign its color."}</p>
            <PhotoKeyMap keyboard={keyboard} selected={destination} disabled={busy}
              colors={Object.fromEntries(Object.entries(assignments).map(([key, value]) => [key, value.hex]))}
              onSelect={(key) => { setMode("per-key"); setDestination(key); invalidate(false); }} />
            <p role="status">Picking for {destination} · {Object.keys(assignments).length} / {keyboard.keys.length} keys assigned</p>
            <p className="intake-message">Assignments stay with this board; changing boards clears this review map. Unassigned keys keep matching colors where possible, otherwise use the first reviewed color.</p>
            <div className="chip-row">
              <button disabled={busy || !assignments[destination]} onClick={() => setAssignments((current) => {
                const next = { ...current }; delete next[destination]; return next;
              })}>Clear assignment for {destination}</button>
              <button disabled={busy || !Object.keys(assignments).length} onClick={() => setAssignments({})}>Clear photo assignments</button>
              {!quick && <button disabled={busy || !name.trim() || !Object.keys(assignments).length} onClick={() => void apply(false, true)}>Apply per-key colors</button>}
            </div>
          </>}
        </>}
        {quick && <label>Quick fit method<select value={strategy} disabled={busy} onChange={(e) => { setStrategy(e.target.value); invalidate(); }}>
          <option value="scheme">Best-fit color scheme · any photo</option>
          <option value="positions">Match positions · same layout, top-down photo</option>
        </select></label>}
        <p className="intake-message">{kind === "keyboard" ? "Crop only the keyboard housing, avoiding keys, shadows, and background."
          : quick ? strategy === "positions" ? "Crop once to the outer key edges. Use a straight-on photo of the same layout; perspective photos will not match reliably."
            : "Start with the whole photo, or optionally crop around the keycaps to exclude the case and background. Quick fit proposes colors for letters, modifiers, and accents—not an exact photo reconstruction."
          : "Crop the keycap surfaces, avoiding the case and background."} Drag a rectangle or adjust the crop percentages.</p>
        <div className="crop-photo" onPointerDown={(event) => {
          if (busy || !imageReady) return;
          const box = event.currentTarget.getBoundingClientRect();
          dragStart.current = { x: (event.clientX - box.left) / box.width, y: (event.clientY - box.top) / box.height };
          event.currentTarget.setPointerCapture(event.pointerId);
        }} onPointerUp={(event) => {
          const start = dragStart.current; dragStart.current = null;
          if (!start) return;
          const box = event.currentTarget.getBoundingClientRect();
          const x = Math.max(0, Math.min(1, (event.clientX - box.left) / box.width));
          const y = Math.max(0, Math.min(1, (event.clientY - box.top) / box.height));
          if (Math.abs(start.x - x) < .01 || Math.abs(start.y - y) < .01) {
            if (perKey && !quick) {
              setCrop({ left: Math.max(0, x - .02), top: Math.max(0, y - .03), right: Math.min(1, x + .02), bottom: Math.min(1, y + .03) }); invalidate();
            }
            return;
          }
          setCrop({ left: Math.min(start.x, x), top: Math.min(start.y, y), right: Math.max(start.x, x), bottom: Math.max(start.y, y) }); invalidate();
        }} onPointerCancel={() => { dragStart.current = null; }}>
          <img key={`${review.id}-${imageIndex}`} src={`/api/ingestion/reviews/${review.id}/images/${imageIndex}`}
            alt={`${label} photo to crop`} draggable={false} onLoad={() => { setImageReady(true); setError(false); }}
            onError={() => { setImageReady(false); setError(true); setMessage("Could not load this photo. Choose another photo or upload one from your computer."); }} />
          {imageReady && validCrop && <div className="crop-outline" style={{ left: `${crop.left * 100}%`, top: `${crop.top * 100}%`, width: `${(crop.right - crop.left) * 100}%`, height: `${(crop.bottom - crop.top) * 100}%` }} />}
        </div>
        <div className="crop-fields">{(["left", "top", "right", "bottom"] as const).map((edge) => <label key={edge}>{label} crop {edge} (%)
          <input type="number" min={0} max={100} step={1} value={Math.round(crop[edge] * 100)} disabled={busy}
            onChange={(e) => { setCrop({ ...crop, [edge]: Math.max(0, Math.min(100, Number(e.target.value))) / 100 }); invalidate(); }} />
        </label>)}</div>
        {quick ? <>
          <button disabled={busy || !validCrop || !imageReady || !targetLayout} onClick={() => void perform(async (signal) => {
            const result = await reviewRequest<Proposal & { keyColorMap: Record<string, string> }>(`reviews/${review.id}/quick-fit`, { imageIndex, crop, layout: targetLayout, strategy }, signal);
            if (signal.aborted) return;
            const hexes = Object.fromEntries(result.colors.map((color) => [color.id, color.hex]));
            setAssignments(Object.fromEntries(Object.entries(result.keyColorMap).filter(([key]) => keyboard.keys.some((entry) => entry.id === key))
              .map(([key, colorId]) => [key, { sampleId: result.id, colorId, hex: hexes[colorId] }])));
            setFitWarnings(result.warnings); setProposal(null);
            setMessage("Quick-fit suggestion ready. Review the colored key map, apply it, or click a key to correct it manually. Running Quick fit again replaces the draft assignments.");
          }, "Fitting photo colors to your keyboard…")}>Quick fit colors</button>
          {fitWarnings.map((note, index) => <p className="intake-message" key={index}>{note}</p>)}
          <button disabled={busy || !name.trim() || !Object.keys(assignments).length} onClick={() => void apply(false, true)}>Apply suggested colors</button>
        </> : <button disabled={busy || !validCrop || !imageReady} onClick={() => void perform(async (signal) => {
          const result = await reviewRequest<Proposal>(`reviews/${review.id}/sample`, { imageIndex, crop }, signal);
          setProposal(result); setExplicit(false);
          setSelected(kind === "keyboard" || perKey ? [result.colors[0].id] : result.colors.map((color) => color.id));
          setMessage("Review the proposed colors before applying them.");
        }, "Sampling the selected crop…")}>Sample {kind === "keyboard" ? "case" : "keycap"} colors</button>}
      </>}
      {kind === "keycaps" && !perKey && review.colors.length > 0 && <button disabled={busy} onClick={() => {
        setExplicit(true); setProposal(null); setSelected(review.colors.map((color) => color.id));
      }}>Use listed color codes</button>}
      {colors.length > 0 && <div className="color-proposals" aria-label={`${label} color proposals`}>
        <p>{kind === "keyboard" ? "Choose one case color." : perKey ? `Choose the color for ${destination}.` : "Keep the keycap colors you want."}</p>
        <div className="chip-row">{colors.map((color) => <button className="chip" key={color.id} disabled={busy}
          aria-label={`${label} sample ${color.hex}`} aria-pressed={selected.includes(color.id)} onClick={() => {
            setSelected(kind === "keyboard" || perKey ? [color.id] : selected.includes(color.id) ? selected.filter((id) => id !== color.id) : [...selected, color.id]);
          }}><span className="case-color-dot" style={{ backgroundColor: color.hex }} />{color.hex}</button>)}</div>
        {proposal?.warnings.map((warning) => <p className="intake-message" key={warning}>{warning}</p>)}
        {perKey && proposal ? <button disabled={busy || selected.length !== 1} onClick={() => {
          const color = colors.find((entry) => entry.id === selected[0]);
          if (color) { setAssignments((current) => ({ ...current, [destination]: { sampleId: proposal.id, colorId: color.id, hex: color.hex } }));
            setMessage(`${color.hex} assigned to ${destination}. Pick another key or apply per-key colors.`); }
        }}>Assign selected color to {destination}</button>
          : <button disabled={busy || !name.trim() || !selected.length || (kind === "keyboard" && !layout)} onClick={() => void apply()}>Apply reviewed {kind}</button>}
      </div>}
      <details><summary>Product evidence and limitations</summary>
        <p className="intake-message">{review.sourceUrl}</p>
        {review.warnings.map((note, index) => <p className="intake-message" key={index}>{note}</p>)}
      </details>
    </>}
    <p role={error ? "alert" : "status"} className="intake-message">{message}</p>
  </article>;
}

export function PhotoIntake({ onApply, keyboard = demoKeyboard }: { onApply: (patch: ProductPatch) => void; keyboard?: KeyboardDefinition }) {
  const [provider, setProvider] = useState(() => stored("keycap-colorizer.page-reader") === "firecrawl" ? "firecrawl" : "playwright");
  const [ready, setReady] = useState(false);
  const [version, setVersion] = useState("Checking backend photo-review support…");
  useEffect(() => {
    const controller = new AbortController();
    reviewRequest<{ version: string }>("version", undefined, controller.signal).then((result) => {
      if (result.version !== "photo-review-2") throw new Error("Version mismatch");
      setReady(true); setVersion(`Backend connected · ${result.version}`);
    }).catch(() => {
      if (!controller.signal.aborted) setVersion("Photo review is unavailable in the running backend. Stop the app, run start.ps1 or start.sh again, then reload this page.");
    });
    return () => controller.abort();
  }, []);
  return <section className="photo-intake" aria-labelledby="intake-title">
    <h2 id="intake-title">Review your products and colors</h2>
    <p>Read either product independently, or upload a photo. Apply a keyboard layout immediately, then choose photos and crop surfaces to review their colors.</p>
    <p role={ready ? "status" : "alert"}>{version}</p>
    <label>Page reader<select value={provider} onChange={(e) => { setProvider(e.target.value); remember("keycap-colorizer.page-reader", e.target.value); }}>
      <option value="playwright">Playwright · local browser</option><option value="firecrawl">Firecrawl · uses credits for uncached pages</option>
    </select></label>
    <div className="review-columns">
      <ProductReview kind="keyboard" provider={provider} ready={ready} onApply={onApply} keyboard={keyboard} />
      <ProductReview kind="keycaps" provider={provider} ready={ready} onApply={onApply} keyboard={keyboard} />
    </div>
  </section>;
}
