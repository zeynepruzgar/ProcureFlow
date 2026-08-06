"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { StockLevel } from "@/lib/types";

export default function InventoryPage() {
  const [items, setItems] = useState<StockLevel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<StockLevel[]>("/stock");
        setItems(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load stock");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Inventory</h1>
      <p className="mt-1 text-zinc-500">
        Current stock levels. Rows below the minimum are highlighted.
      </p>

      <div className="mt-6 overflow-hidden rounded-xl border border-black/[.08] dark:border-white/[.145]">
        {loading ? (
          <p className="p-4 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : items.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">No stock records yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">Product</th>
                <th className="px-4 py-2 font-medium">SKU</th>
                <th className="px-4 py-2 font-medium">Location</th>
                <th className="px-4 py-2 text-right font-medium">Quantity</th>
                <th className="px-4 py-2 text-right font-medium">Min level</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => {
                const min = s.product?.min_stock_level ?? 0;
                const isLow = s.quantity < min;
                return (
                  <tr
                    key={s.id}
                    className={`border-t border-black/[.06] dark:border-white/[.08] ${
                      isLow ? "bg-red-50 dark:bg-red-950/30" : ""
                    }`}
                  >
                    <td className="px-4 py-2 font-medium">
                      {s.product?.name ?? s.product_id}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {s.product?.sku ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-zinc-500">{s.location}</td>
                    <td className="px-4 py-2 text-right font-medium">
                      {s.quantity}
                      {isLow && (
                        <span className="ml-2 inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-300">
                          Low
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right text-zinc-500">{min}</td>
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
