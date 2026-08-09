"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { ScanResult, Signal, SignalType } from "@/lib/types";

const WRITER_ROLES = ["procurement_specialist", "manager", "admin"];

interface Me {
  role: string;
}

function typeLabel(type: SignalType): string {
  switch (type) {
    case "low_stock":
      return "Low stock";
    case "delayed_order":
      return "Delayed order";
    case "price_spike":
      return "Price spike";
  }
}

function severityClasses(severity: string): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    case "medium":
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
    default:
      return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300";
  }
}

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanSummary, setScanSummary] = useState<string | null>(null);

  const fetchSignals = useCallback(
    () => apiFetch<Signal[]>("/signals?status=open"),
    [],
  );

  useEffect(() => {
    async function loadList() {
      try {
        setSignals(await fetchSignals());
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load signals");
      } finally {
        setLoading(false);
      }
    }
    async function loadRole() {
      try {
        const me = await apiFetch<Me>("/auth/me");
        setRole(me.role);
      } catch {
        // rol yoksa Scan Now gizli kalir
      }
    }
    void loadList();
    void loadRole();
  }, [fetchSignals]);

  const canScan = WRITER_ROLES.includes(role);

  async function handleScan() {
    setScanning(true);
    setScanSummary(null);
    setError(null);
    try {
      const result = await apiFetch<ScanResult>("/signals/scan", {
        method: "POST",
      });
      setSignals(result.open_signals);
      setScanSummary(
        `Scan complete: ${result.created} created, ${result.updated} updated, ${result.closed} closed.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Signals</h1>
          <p className="mt-1 text-zinc-500">
            Issues detected by rule-based scans (low stock, delayed orders,
            price spikes).
          </p>
        </div>
        {canScan && (
          <button
            type="button"
            onClick={handleScan}
            disabled={scanning}
            className="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-black"
          >
            {scanning ? "Scanning…" : "Scan now"}
          </button>
        )}
      </div>

      {scanSummary && (
        <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
          {scanSummary}
        </p>
      )}

      <div className="mt-6 overflow-hidden rounded-xl border border-black/[.08] dark:border-white/[.145]">
        {loading ? (
          <p className="p-4 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : signals.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">
            No open signals. Run a scan to detect issues from current inventory
            and order data.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Severity</th>
                <th className="px-4 py-2 font-medium">Entity ID</th>
                <th className="px-4 py-2 font-medium">Detected</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr
                  key={s.id}
                  className="border-t border-black/[.06] dark:border-white/[.08]"
                >
                  <td className="px-4 py-2 font-medium">{typeLabel(s.type)}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${severityClasses(s.severity)}`}
                    >
                      {s.severity}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-zinc-500">
                    {s.entity_id}
                  </td>
                  <td className="px-4 py-2 text-zinc-500">
                    {s.detected_at ? s.detected_at.slice(0, 19).replace("T", " ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
