import { useState } from "react";

import { demoKeyboard } from "../data/demoKeyboard";
import { demoKeycapSet } from "../data/demoKeycapSet";
import { KeyboardScene } from "../renderer/KeyboardScene";
import type { KeyboardDefinition } from "../types/domain";
import {
  applyColor,
  clearSelection,
  initialConfiguratorState,
  resetKeyboard,
  resetSelectedKeys,
  selectGroup,
  selectKey,
} from "../state/configurator";

const previewColors = Object.fromEntries(
  demoKeycapSet.colors.map((color) => [color.id, color.hex]),
);

const groups = [
  ["alphas", "Alphas"],
  ["modifiers", "Modifiers"],
  ["function-row", "Function row"],
  ["arrow-keys", "Arrows"],
  ["navigation-cluster", "Navigation"],
  ["wasd", "WASD"],
  ["entire-keyboard", "Entire board"],
] as const;

export function KeyboardWorkbench({ keyboard = demoKeyboard }: { keyboard?: KeyboardDefinition } = {}) {
  const [state, setState] = useState(initialConfiguratorState);
  const [hoveredKeyId, setHoveredKeyId] = useState<string | null>(null);
  const activeGroup = groups.find(([id]) => {
    const members = keyboard.keys.filter((key) => key.group.includes(id));
    return members.length > 0 && members.length === state.selectedKeyIds.length
      && members.every((key) => state.selectedKeyIds.includes(key.id));
  });
  const selectedColor = state.selectedKeyIds.length > 0
    ? state.keyColorMap[state.selectedKeyIds[0]] ?? "bone"
    : null;
  const uniformColor = selectedColor && state.selectedKeyIds.every(
    (id) => (state.keyColorMap[id] ?? "bone") === selectedColor,
  ) ? selectedColor : null;
  const selectedLabel = state.selectedKeyIds.length <= 3
    ? state.selectedKeyIds.join(", ")
    : `${state.selectedKeyIds.slice(0, 3).join(", ")} +${state.selectedKeyIds.length - 3}`;

  return (
    <section className="workbench" aria-labelledby="preview-title">
      <div className="workbench-heading">
        <div>
          <p className="eyebrow">INTERACTIVE FIXTURE</p>
          <h2 id="preview-title">{keyboard.model}</h2>
        </div>
        <div className="selection-feedback">
          <p role="status" aria-label="Selection summary" aria-live="polite">
            {activeGroup?.[1] ?? "Selection"} · {state.selectedKeyIds.length} keys selected
          </p>
          <small>{hoveredKeyId ? `Hover: ${hoveredKeyId}` : selectedLabel || "Choose a key or group"}</small>
        </div>
      </div>

      <KeyboardScene
        keyboard={keyboard}
        selectedKeyIds={state.selectedKeyIds}
        keyColorMap={state.keyColorMap}
        colors={previewColors}
        onKeyHover={setHoveredKeyId}
        onKeyClick={(keyId, additive) => setState((current) => selectKey(current, keyId, additive))}
      />

      <div className="controls">
        <div>
          <p className="control-label">SELECT GROUP</p>
          <div className="chip-row">
            {groups.map(([id, label]) => (
              <button key={id} className="chip"
                disabled={!keyboard.keys.some((key) => key.group.includes(id))}
                title={keyboard.keys.some((key) => key.group.includes(id)) ? label : `${label} is not present on this keyboard`}
                aria-pressed={activeGroup?.[0] === id} onClick={() => {
                setHoveredKeyId(null);
                setState((current) => activeGroup?.[0] === id
                  ? clearSelection(current)
                  : selectGroup(current, keyboard.keys, id));
              }}>
                {label}
              </button>
            ))}
            <button
              className="chip"
              disabled={state.selectedKeyIds.length === 0}
              onClick={() => {
                setHoveredKeyId(null);
                setState(clearSelection);
              }}
            >
              Clear selection
            </button>
          </div>
        </div>
        <div>
          <p className="control-label">{demoKeycapSet.name.toUpperCase()}</p>
          <div className="swatch-row">
            {demoKeycapSet.colors.map((color) => (
              <button
                key={color.id}
                className="swatch"
                style={{ backgroundColor: color.hex }}
                aria-label={`Apply ${color.name}`}
                aria-pressed={uniformColor === color.id}
                title={`${color.name} · ${color.hex}`}
                disabled={state.selectedKeyIds.length === 0}
                onClick={() => setState((current) => applyColor(current, color.id))}
              />
            ))}
          </div>
          <p className="palette-feedback">
            {uniformColor
              ? demoKeycapSet.colors.filter((color) => color.id === uniformColor).map((color) => `${color.name} · ${color.hex}`)
              : state.selectedKeyIds.length ? "Mixed colors" : "Select keys to paint"}
          </p>
        </div>
      </div>
      <div className="reset-row">
        <button
          className="text-button"
          disabled={state.selectedKeyIds.length === 0}
          onClick={() => setState((current) => resetSelectedKeys(current))}
        >
          Reset selected
        </button>
        <button
          className="text-button"
          disabled={Object.keys(state.keyColorMap).length === 0}
          onClick={() => setState((current) => resetKeyboard(current))}
        >
          Reset board
        </button>
      </div>
      <p className="interaction-hint">Click a key to select · Shift-click for multiple · Drag to orbit · Scroll to zoom</p>
    </section>
  );
}
