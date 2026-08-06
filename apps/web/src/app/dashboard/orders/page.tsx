"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { Order } from "@/lib/types";

function statusClasses(status: string): string {
  switch (status) {
    case "delivered":
      return "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300";
    case "delayed":
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    case "cancelled":
      return "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400";
    default:
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
  }
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<Order[]>("/orders");
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load orders");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Purchase Orders</h1>
      <p className="mt-1 text-zinc-500">Open and historical orders with suppliers.</p>

      <div className="mt-6 overflow-hidden rounded-xl border border-black/[.08] dark:border-white/[.145]">
        {loading ? (
          <p className="p-4 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : orders.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">No orders yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">Supplier</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Expected delivery</th>
                <th className="px-4 py-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr
                  key={o.id}
                  className="border-t border-black/[.06] dark:border-white/[.08]"
                >
                  <td className="px-4 py-2 font-medium">{o.supplier?.name ?? o.supplier_id}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusClasses(o.status)}`}
                    >
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-zinc-500">
                    {o.expected_delivery_date ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-zinc-500">
                    {o.created_at ? o.created_at.slice(0, 10) : "—"}
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
