import { ConnectionStatus } from "./components/ConnectionStatus";
import { KeyboardWorkbench } from "./components/KeyboardWorkbench";
import { AiStatus } from "./components/AiStatus";
import "./styles.css";

export default function App() {
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

      <section className="intake" aria-labelledby="intake-title">
        <header>
          <span>01</span>
          <div>
            <p className="eyebrow">PRODUCT INTAKE</p>
            <h2 id="intake-title">Start with two links</h2>
          </div>
        </header>
        <label>
          Keyboard product URL
          <input type="url" placeholder="https://…" disabled />
        </label>
        <label>
          Keycap product URL
          <input type="url" placeholder="https://…" disabled />
        </label>
        <button disabled>Analyze products</button>
        <p className="phase-note">Product ingestion arrives in a later phase.</p>
        <AiStatus />
      </section>
      <KeyboardWorkbench />
    </main>
  );
}
