"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type {
  PurchaseRequest,
  Recommendation,
  RecommendationDecision,
  ScanResult,
  Signal,
  SignalType,
} from "@/lib/types";

const WRITER_ROLES = ["procurement_specialist", "manager", "admin"];
// Onaylama/reddetme yalnizca manager/admin: docs/DATA_MODEL.md rol tablosu.
const REVIEW_ROLES = ["manager", "admin"];

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
  const [recommendations, setRecommendations] = useState<
    Record<string, Recommendation>
  >({});
  const [purchaseRequests, setPurchaseRequests] = useState<
    Record<string, PurchaseRequest>
  >({});
  const [generating, setGenerating] = useState<Record<string, boolean>>({});
  const [recError, setRecError] = useState<Record<string, string>>({});
  // Hangi sinyal icin hangi karar (approve/reject) islemde: butonlari ayri ayri disable etmek icin.
  const [deciding, setDeciding] = useState<Record<string, "approve" | "reject">>(
    {},
  );

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
  const canReview = REVIEW_ROLES.includes(role);

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

  async function handleGenerateRecommendation(signalId: string) {
    setGenerating((prev) => ({ ...prev, [signalId]: true }));
    setRecError((prev) => {
      const next = { ...prev };
      delete next[signalId];
      return next;
    });
    try {
      const rec = await apiFetch<Recommendation>(
        `/signals/${signalId}/recommend`,
        { method: "POST" },
      );
      setRecommendations((prev) => ({ ...prev, [signalId]: rec }));
    } catch (err) {
      setRecError((prev) => ({
        ...prev,
        [signalId]:
          err instanceof Error ? err.message : "Failed to generate recommendation",
      }));
    } finally {
      setGenerating((prev) => ({ ...prev, [signalId]: false }));
    }
  }

  async function handleDecision(
    signalId: string,
    recommendationId: string,
    decision: "approve" | "reject",
  ) {
    setDeciding((prev) => ({ ...prev, [signalId]: decision }));
    setRecError((prev) => {
      const next = { ...prev };
      delete next[signalId];
      return next;
    });
    try {
      const result = await apiFetch<RecommendationDecision>(
        `/recommendations/${recommendationId}/${decision}`,
        { method: "POST" },
      );
      setRecommendations((prev) => ({
        ...prev,
        [signalId]: result.recommendation,
      }));
      if (result.purchase_request) {
        setPurchaseRequests((prev) => ({
          ...prev,
          [signalId]: result.purchase_request as PurchaseRequest,
        }));
      }
      // Backend karar sonrasi sinyali 'handled' yapar; satiri hemen listeden
      // dusurmek yerine sonucu gorebilsinler diye lokal olarak isaretliyoruz.
      setSignals((prev) =>
        prev.map((s) => (s.id === signalId ? { ...s, status: "handled" } : s)),
      );
    } catch (err) {
      setRecError((prev) => ({
        ...prev,
        [signalId]:
          err instanceof Error ? err.message : `Failed to ${decision} recommendation`,
      }));
    } finally {
      setDeciding((prev) => {
        const next = { ...prev };
        delete next[signalId];
        return next;
      });
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
                {canScan && (
                  <th className="px-4 py-2 font-medium">Recommendation</th>
                )}
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => {
                const rec = recommendations[s.id];
                const pr = purchaseRequests[s.id];
                const isGenerating = generating[s.id] ?? false;
                const decidingAction = deciding[s.id];
                const rowError = recError[s.id];
                return (
                  <tr
                    key={s.id}
                    className={`border-t border-black/[.06] dark:border-white/[.08] ${
                      s.status === "handled" ? "opacity-60" : ""
                    }`}
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
                      {s.detected_at
                        ? s.detected_at.slice(0, 19).replace("T", " ")
                        : "—"}
                    </td>
                    {canScan && (
                      <td className="px-4 py-2 align-top">
                        {rec ? (
                          <div className="max-w-sm space-y-1.5">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                                rec.status === "approved"
                                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                                  : rec.status === "rejected"
                                    ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                                    : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                              }`}
                            >
                              {rec.status}
                            </span>
                            <p className="text-xs text-zinc-600 dark:text-zinc-400">
                              {rec.rationale}
                            </p>
                            <p className="text-xs text-zinc-500">
                              Qty: {rec.suggested_qty ?? "—"} · Supplier:{" "}
                              {rec.suggested_supplier_id ?? "—"}
                            </p>

                            {rec.status === "pending" && canReview && (
                              <div className="flex gap-2 pt-1">
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleDecision(s.id, rec.id, "approve")
                                  }
                                  disabled={Boolean(decidingAction)}
                                  className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                                >
                                  {decidingAction === "approve"
                                    ? "Approving…"
                                    : "Approve"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() =>
                                    handleDecision(s.id, rec.id, "reject")
                                  }
                                  disabled={Boolean(decidingAction)}
                                  className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 transition-opacity hover:opacity-80 disabled:opacity-50 dark:border-red-900/60 dark:text-red-300"
                                >
                                  {decidingAction === "reject"
                                    ? "Rejecting…"
                                    : "Reject"}
                                </button>
                              </div>
                            )}
                            {rec.status === "pending" && !canReview && (
                              <p className="text-xs text-zinc-400">
                                Awaiting manager approval.
                              </p>
                            )}

                            {rec.status === "approved" && (
                              <p className="text-xs text-emerald-700 dark:text-emerald-400">
                                {pr
                                  ? `Draft purchase request created (qty ${
                                      pr.lines[0]?.qty ?? rec.suggested_qty ?? "—"
                                    }).`
                                  : "Approved — draft purchase request created."}{" "}
                                <Link
                                  href="/dashboard/purchase-requests"
                                  className="underline underline-offset-2"
                                >
                                  View it
                                </Link>
                              </p>
                            )}
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleGenerateRecommendation(s.id)}
                            disabled={isGenerating}
                            className="rounded-lg border border-black/[.08] px-3 py-1.5 text-xs font-medium transition-opacity hover:opacity-80 disabled:opacity-50 dark:border-white/[.145]"
                          >
                            {isGenerating ? "Generating…" : "Generate recommendation"}
                          </button>
                        )}
                        {rowError && (
                          <p className="mt-1 text-xs text-red-600">{rowError}</p>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
