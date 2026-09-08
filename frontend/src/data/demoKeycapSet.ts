import type { KeycapSet } from "../types/domain";

export const demoKeycapSet: KeycapSet = {
  id: "demo-botanical-caps",
  manufacturer: "Local Fixture",
  name: "Botanical Workshop",
  profile: "Cherry",
  colors: [
    { id: "bone", name: "Bone", hex: "#D8DBD1", source: "manufacturer" },
    { id: "moss", name: "Moss", hex: "#78936A", source: "manufacturer" },
    { id: "forest", name: "Forest", hex: "#2F5141", source: "manufacturer" },
    { id: "clay", name: "Clay", hex: "#C5795E", source: "manufacturer" },
    { id: "charcoal", name: "Charcoal", hex: "#343A38", source: "manufacturer" },
  ],
  supportedKeys: [],
  sourceUrl: "https://example.com/fixtures/botanical-keycaps",
};

