import type { KeyboardKey, KeyColorMap } from "../types/domain";

export interface ConfiguratorState {
  selectedKeyIds: string[];
  keyColorMap: KeyColorMap;
}

export const initialConfiguratorState: ConfiguratorState = {
  selectedKeyIds: [],
  keyColorMap: {},
};

export function selectKey(
  state: ConfiguratorState,
  keyId: string,
  additive = false,
): ConfiguratorState {
  if (!additive) {
    return { ...state, selectedKeyIds: [keyId] };
  }
  const selected = new Set(state.selectedKeyIds);
  selected.has(keyId) ? selected.delete(keyId) : selected.add(keyId);
  return { ...state, selectedKeyIds: [...selected] };
}

export function selectGroup(
  state: ConfiguratorState,
  keys: KeyboardKey[],
  group: string,
): ConfiguratorState {
  return {
    ...state,
    selectedKeyIds: keys.filter((key) => key.group.includes(group)).map((key) => key.id),
  };
}

export function applyColor(
  state: ConfiguratorState,
  colorId: string,
): ConfiguratorState {
  const assignments = Object.fromEntries(
    state.selectedKeyIds.map((keyId) => [keyId, colorId]),
  );
  return { ...state, keyColorMap: { ...state.keyColorMap, ...assignments } };
}

export function clearSelection(state: ConfiguratorState): ConfiguratorState {
  return { ...state, selectedKeyIds: [] };
}

export function resetSelectedKeys(state: ConfiguratorState): ConfiguratorState {
  const selected = new Set(state.selectedKeyIds);
  return {
    ...state,
    keyColorMap: Object.fromEntries(
      Object.entries(state.keyColorMap).filter(([keyId]) => !selected.has(keyId)),
    ),
  };
}

export function resetKeyboard(state: ConfiguratorState): ConfiguratorState {
  return { ...state, keyColorMap: {} };
}
