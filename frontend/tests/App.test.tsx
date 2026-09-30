import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

vi.mock("../src/components/KeyboardWorkbench", () => ({
  KeyboardWorkbench: () => <section aria-label="keyboard workbench" />,
}));
vi.mock("../src/components/AiStatus", () => ({ AiStatus: () => <p>AI status</p> }));

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("connects to the local backend and renders the intake foundation", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      { ok: true, json: async () => ({ status: "ok", service: "keycap-configurator-api", version: "photo-review-2" }) } as Response,
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: /build the keyboard/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/keyboard product url/i)).toBeEnabled();
    expect(await screen.findByText("Local service connected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Read keyboard" })).toBeDisabled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Try demo keyboard" })).toBeEnabled());
  });

  it("shows a useful offline state when the backend cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    render(<App />);
    expect(await screen.findByText("Local service unavailable")).toBeInTheDocument();
  });
});
