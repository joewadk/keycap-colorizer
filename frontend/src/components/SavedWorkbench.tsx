import { useEffect, useState } from "react";
import type { ProductPatch } from "../api/photoReview";
import { demoKeyboard } from "../data/demoKeyboard";
import { demoKeycapSet } from "../data/demoKeycapSet";
import type { Configuration, KeyboardDefinition, KeycapSet, KeyColorMap } from "../types/domain";
import { boardPresets, boardColors } from "../data/presets";
import { adaptColors, draftKey } from "../state/presets";
import { listDesigns, restoreDesign, saveDesign } from "../api/storage";
import { KeyboardWorkbench } from "./KeyboardWorkbench";

interface SavedWorkbenchProps {
  incoming?: ProductPatch | null;
  initialKeyboard?: KeyboardDefinition;
  initialKeycapSet?: KeycapSet;
  onKeyboardChange?: (keyboard: KeyboardDefinition) => void;
}

export function SavedWorkbench({ initialKeyboard = demoKeyboard, initialKeycapSet = demoKeycapSet, incoming, onKeyboardChange }: SavedWorkbenchProps) {
  const [products, setProducts] = useState({ keyboard: initialKeyboard, keycapSet: initialKeycapSet, revision: 0 });
  const [keyColorMap, setKeyColorMap] = useState<KeyColorMap>({});
  const [caseColor, setCaseColor] = useState(initialKeyboard.case.color);
  const [drafts, setDrafts] = useState<Record<string, KeyColorMap>>({});
  const [name, setName] = useState("");
  const [designs, setDesigns] = useState<Configuration[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Designs are saved locally by the backend. Painting works even when it is offline.");
  const [error, setError] = useState(false);

  useEffect(() => { onKeyboardChange?.(products.keyboard); }, [products.keyboard, onKeyboardChange]);

  useEffect(() => {
    if (!incoming) return;
    if (incoming.targetKeyboardId && incoming.targetKeyboardId !== products.keyboard.id) {
      setError(true); setMessage("The board changed during photo review. Review per-key assignments for the current layout before applying."); return;
    }
    const keyboard = incoming.keyboard ?? products.keyboard;
    const keycapSet = incoming.keycapSet ?? products.keycapSet;
    const validKeys = new Set(keyboard.keys.map((key) => key.id));
    const validColors = new Set(keycapSet.colors.map((color) => color.id));
    const reviewed = Object.fromEntries(Object.entries(incoming.keyColorMap ?? {}).filter(([key, color]) => validKeys.has(key) && validColors.has(color)));
    setKeyColorMap({ ...adaptColors(keyColorMap, products.keycapSet, keycapSet, keyboard), ...reviewed });
    setProducts({ keyboard, keycapSet, revision: products.revision + 1 });
    if (incoming.caseColor) setCaseColor(incoming.caseColor);
    setError(false);
    setMessage("Reviewed product applied. Matching painted colors were retained. Save to keep this combination.");
  }, [incoming]);

  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError(false);
    try { await action(); }
    catch (failure) {
      setError(true);
      setMessage(failure instanceof Error ? failure.message : "Could not access saved designs.");
    } finally { setBusy(false); }
  }

  function switchPreset(keyboard: KeyboardDefinition, keycapSet: KeycapSet) {
    setDrafts((current) => ({ ...current, [draftKey(products.keyboard, products.keycapSet)]: keyColorMap }));
    const previousDraft = drafts[draftKey(keyboard, keycapSet)];
    setKeyColorMap(previousDraft ?? adaptColors(keyColorMap, products.keycapSet, keycapSet, keyboard));
    setProducts((current) => ({ keyboard, keycapSet, revision: current.revision + 1 }));
    setError(false);
    setMessage(previousDraft ? "Returned to your in-session draft. Save it to keep it after reload." :
      "New combination: matching keys with identical palette hex colors were carried over. Other keys use the default color. Your previous combination is kept as an in-session draft.");
  }

  return <>
    <section className="preset-controls" aria-labelledby="preset-title">
      <p className="eyebrow">QUICK EXPERIMENTS · NO PRODUCT LINKS NEEDED</p>
      <h2 id="preset-title">Choose a board size and case color</h2>
      <div className="preset-fields">
        <label>Board size<select value={products.keyboard.id} disabled={busy} onChange={(event) => {
          const board = boardPresets.find((entry) => entry.id === event.target.value);
          if (board) switchPreset(board, products.keycapSet);
        }}>
          {!boardPresets.some((board) => board.id === products.keyboard.id) &&
            <option value={products.keyboard.id}>{products.keyboard.model} (saved product)</option>}
          {boardPresets.map((board) => <option key={board.id} value={board.id}>
            {board.layoutType === "TKL" ? "ANSI TKL" : `ANSI ${board.layoutType}%`} · {board.keys.length} keys
          </option>)}
        </select></label>
        <label>Custom board color<input type="color" value={/^#[0-9a-fA-F]{6}$/.test(caseColor) ? caseColor : "#303735"}
          disabled={busy} onChange={(event) => setCaseColor(event.target.value)} /></label>
      </div>
      <div className="chip-row" aria-label="Board case colors">{boardColors.map(([name, hex]) =>
        <button className="chip" key={name} aria-label={`Board color ${name}`} aria-pressed={caseColor.toUpperCase() === hex}
          disabled={busy} onClick={() => setCaseColor(hex)}><span className="case-color-dot" style={{ backgroundColor: hex }} />{name}</button>
      )}</div>
      <p>Case color: {caseColor.toUpperCase()} · Changes the keyboard housing only, not the keycaps. Lighting affects its appearance.</p>
      <p>Generic ANSI layouts, not exact replicas of specific products. Board colors are visual choices, not manufacturer finish specifications.</p>
      <p>Switching sizes keeps the case color and remembers keycap drafts until reload. Save designs to keep them permanently.</p>
    </section>
    <KeyboardWorkbench key={products.revision} keyboard={products.keyboard} keycapSet={products.keycapSet}
      initialColorMap={keyColorMap} onColorMapChange={setKeyColorMap} caseColor={caseColor} />
    <section className="saved-designs" aria-labelledby="saved-designs-title">
      <h2 id="saved-designs-title">Save your combinations</h2>
      <label>Design name (optional)<input value={name} maxLength={200} onChange={(event) => setName(event.target.value)} /></label>
      <div className="chip-row">
        <button disabled={busy} onClick={() => void perform(async () => {
          const saved = await saveDesign(products.keyboard, products.keycapSet, keyColorMap, name, caseColor);
          setDesigns((current) => [saved.configuration, ...current].slice(0, 50));
          setSelected(saved.configuration.id);
          setMessage("Design saved locally. Edits made after clicking Save are not included in that snapshot.");
        })}>Save design</button>
        <button disabled={busy} onClick={() => void perform(async () => {
          const loaded = await listDesigns();
          setDesigns(loaded);
          setSelected(loaded[0]?.id ?? "");
          setMessage(loaded.length ? "Showing the latest 50 designs at most. Restoring replaces the current preview and unsaved edits." : "No saved designs yet.");
        })}>Load saved designs</button>
      </div>
      {designs.length > 0 && <>
        <label>Saved design<select value={selected} disabled={busy} onChange={(event) => setSelected(event.target.value)}>
          {designs.map((design) => <option key={design.id} value={design.id}>{design.name ?? "Untitled design"} — {new Date(design.dateCreated).toLocaleString()}</option>)}
        </select></label>
        <p>Restore replaces the preview, including unsaved color changes.</p>
        <button disabled={busy || !selected} onClick={() => void perform(async () => {
          const saved = await restoreDesign(selected);
          setKeyColorMap(saved.configuration.keyColorMap);
          setCaseColor(saved.configuration.caseColor ?? saved.keyboard.case.color);
          setName(saved.configuration.name ?? "");
          setProducts((current) => ({ keyboard: saved.keyboard, keycapSet: saved.keycapSet, revision: current.revision + 1 }));
          setMessage("Design restored, including its products and per-key colors.");
        })}>Restore selected design</button>
      </>}
      <p role={error ? "alert" : "status"}>{busy ? "Working with local storage…" : message}</p>
    </section>
  </>;
}
