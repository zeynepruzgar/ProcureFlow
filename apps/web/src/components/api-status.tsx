"use client";

import { useEffect, useState } from "react";

type Status = "loading" | "online" | "offline";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function check() {
      try {
        const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!active) return;
        setStatus("online");
        setVersion(data.version ?? null);
      } catch {
        if (!active) return;
        setStatus("offline");
      }
    }

    check();
    return () => {
      active = false;
    };
  }, []);

  const label =
    status === "loading"
      ? "Checking API…"
      : status === "online"
        ? `API online${version ? ` · v${version}` : ""}`
        : "API offline";

  const dotColor =
    status === "loading"
      ? "bg-amber-500"
      : status === "online"
        ? "bg-emerald-500"
        : "bg-red-500";

  return (
    <div className="flex items-center gap-2 rounded-lg border border-black/[.08] bg-white px-4 py-3 text-sm text-zinc-700 dark:border-white/[.145] dark:bg-zinc-950 dark:text-zinc-300">
      <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} aria-hidden />
      <span>{label}</span>
      <span className="ml-auto font-mono text-xs text-zinc-400">{API_URL}</span>
    </div>
  );
}
