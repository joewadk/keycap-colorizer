import { useEffect, useState } from "react";

import { fetchHealth } from "../api/health";

type ConnectionState = "checking" | "connected" | "offline";

export function ConnectionStatus() {
  const [state, setState] = useState<ConnectionState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(() => setState("connected"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState("offline");
      });
    return () => controller.abort();
  }, []);

  const labels: Record<ConnectionState, string> = {
    checking: "Checking local service…",
    connected: "Local service connected",
    offline: "Local service unavailable",
  };

  return (
    <p className={`status status--${state}`} role="status">
      <span aria-hidden="true" />
      {labels[state]}
    </p>
  );
}

