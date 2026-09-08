import { useEffect, useState } from "react";

export function AiStatus() {
  const [message, setMessage] = useState("Checking optional AI configuration…");
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/capabilities", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Capabilities unavailable");
        const data: unknown = await response.json();
        if (!data || typeof data !== "object" || !("message" in data) || typeof data.message !== "string") {
          throw new Error("Invalid capabilities");
        }
        if (!controller.signal.aborted) setMessage(data.message);
      })
      .catch(() => {
        if (!controller.signal.aborted) setMessage("AI configuration unavailable while the local service is offline.");
      });
    return () => controller.abort();
  }, []);
  return <p className="phase-note" role="status">{message}</p>;
}
