import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

vi.mock("../src/components/KeyboardWorkbench", () => ({
  KeyboardWorkbench: () => <section aria-label="keyboard workbench" />,
}));

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("connects to the local backend and renders the intake foundation", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", service: "keycap-configurator-api" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: /build the keyboard/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/keyboard product url/i)).toBeDisabled();
    expect(await screen.findByText("Local service connected")).toBeInTheDocument();
  });

  it("shows a useful offline state when the backend cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    render(<App />);
    expect(await screen.findByText("Local service unavailable")).toBeInTheDocument();
  });
});
