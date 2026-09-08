export type LayoutType = "60" | "65" | "70" | "75" | "TKL" | "96" | "100" | "OTHER";

export interface KeyboardCase {
  color: string;
  material?: string | null;
  widthMm?: number | null;
  depthMm?: number | null;
  heightMm?: number | null;
  cornerRadiusMm?: number | null;
}

export interface KeyboardKey {
  id: string;
  legend: string;
  row: number;
  x: number;
  y: number;
  widthU: number;
  heightU: number;
  stabilizer: boolean;
  group: string[];
}

export interface KeyboardFeatures {
  knob: boolean;
  screen: boolean;
  badge: boolean;
}

export interface KeyboardDefinition {
  id: string;
  manufacturer: string;
  model: string;
  layoutType: LayoutType;
  case: KeyboardCase;
  keys: KeyboardKey[];
  features: KeyboardFeatures;
  sourceUrl: string;
}

export type KeycapProfile = "Cherry" | "OEM" | "XDA" | "DSA" | "SA" | "Unknown";
export type ColorSource = "manufacturer" | "image_sample" | "model_estimate";

export interface KeycapColor {
  id: string;
  name: string;
  hex: string;
  source: ColorSource;
  confidence?: number | null;
}

export interface SupportedKey {
  legend?: string | null;
  widthU: number;
  quantity?: number | null;
}

export interface KeycapSet {
  id: string;
  manufacturer: string;
  name: string;
  profile: KeycapProfile;
  colors: KeycapColor[];
  supportedKeys: SupportedKey[];
  sourceUrl: string;
}

export type KeyColorMap = Record<string, string>;

export interface Configuration {
  id: string;
  keyboardId: string;
  keycapSetId: string;
  keyColorMap: KeyColorMap;
  dateCreated: string;
  name?: string | null;
}
