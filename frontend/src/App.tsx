import { useState } from "react";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { SavedWorkbench } from "./components/SavedWorkbench";
import { AiStatus } from "./components/AiStatus";
import { PhotoIntake } from "./components/PhotoIntake";
import type { ProductPatch } from "./api/photoReview";
import { demoKeyboard } from "./data/demoKeyboard";
import "./styles.css";

export default function App() {
  const [intake, setIntake] = useState<ProductPatch | null>(null);
  const [keyboard, setKeyboard] = useState(demoKeyboard);
  return (
    <main className="app-shell">
      <section className="hero compact-hero">
        <p className="eyebrow">LOCAL WORKBENCH</p>
        <h1>Build the keyboard<br />before you buy it.</h1>
        <p className="intro">
          Combine a keyboard and keycap set, then experiment with every key in a
          fast, interactive preview.
        </p>
        <ConnectionStatus />
      </section>

      <AiStatus />
      <PhotoIntake onApply={setIntake} keyboard={keyboard} />
      <SavedWorkbench incoming={intake} onKeyboardChange={setKeyboard} />
    </main>
  );
}
