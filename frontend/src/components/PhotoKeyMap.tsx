import type { KeyboardDefinition } from "../types/domain";

export function PhotoKeyMap({ keyboard, selected, colors, disabled, onSelect }: {
  keyboard: KeyboardDefinition; selected: string; colors: Record<string, string>;
  disabled: boolean; onSelect: (key: string) => void;
}) {
  const width = Math.max(...keyboard.keys.map((key) => key.x + key.widthU));
  const height = Math.max(...keyboard.keys.map((key) => key.y + key.heightU));
  return <div className="photo-keymap-scroll">
    <div className="photo-keymap" aria-label="Photo color destination keys" style={{ width: width * 40, height: height * 40 }}>
      {keyboard.keys.map((key) => <button key={key.id} type="button" disabled={disabled}
        aria-label={`Pick photo color for ${key.id}`} aria-pressed={selected === key.id}
        title={`${key.legend || key.id}: ${colors[key.id] ?? "not assigned"}`}
        onClick={() => onSelect(key.id)} style={{ left: key.x * 40, top: key.y * 40,
          width: key.widthU * 40 - 3, height: key.heightU * 40 - 3 }}>
        <span className="key-color-dot" style={{ backgroundColor: colors[key.id] ?? "transparent" }} />
        <span>{key.legend || key.id}</span>
      </button>)}
    </div>
  </div>;
}
