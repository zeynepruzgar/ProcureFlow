"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { PurchaseRequest } from "@/lib/types";

export default function PurchaseRequestsPage() {
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setRequests(await apiFetch<PurchaseRequest[]>("/purchase-requests"));
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load purchase requests",
        );
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Purchase Requests</h1>
      <p className="mt-1 text-zinc-500">
        Drafts created by the agent after a manager approved its recommendation.
        These are not real orders — a specialist still turns them into a
        purchase order.
      </p>

      <div className="mt-6 overflow-hidden rounded-xl border border-black/[.08] dark:border-white/[.145]">
        {loading ? (
          <p className="p-4 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : requests.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">
            No draft requests yet. Approve a recommendation on the Signals page
            to create one.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">Items</th>
                <th className="px-4 py-2 font-medium">Supplier</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Why</th>
                <th className="px-4 py-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((pr) => (
                <tr
                  key={pr.id}
                  className="border-t border-black/[.06] dark:border-white/[.08]"
                >
                  <td className="px-4 py-2 align-top">
                    {pr.lines.length === 0 ? (
                      <span className="text-zinc-500">—</span>
                    ) : (
                      <ul className="space-y-0.5">
                        {pr.lines.map((line, index) => (
                          <li key={`${pr.id}-${index}`} className="font-medium">
                            {line.product?.name ?? line.product_id ?? "Unknown"}
                            <span className="font-normal text-zinc-500">
                              {" "}
                              × {line.qty ?? "—"}
                              {line.product?.unit ? ` ${line.product.unit}` : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td className="px-4 py-2 align-top">
                    {pr.supplier?.name ?? pr.supplier_id ?? "—"}
                    {pr.supplier?.lead_time_days != null && (
                      <span className="block text-xs text-zinc-500">
                        {pr.supplier.lead_time_days} day lead time
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 align-top">
                    <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                      {pr.status}
                    </span>
                  </td>
                  <td className="max-w-sm px-4 py-2 align-top text-xs text-zinc-600 dark:text-zinc-400">
                    {pr.recommendation?.rationale ?? "—"}
                  </td>
                  <td className="px-4 py-2 align-top text-zinc-500">
                    {pr.created_at
                      ? pr.created_at.slice(0, 19).replace("T", " ")
                      : "—"}
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
