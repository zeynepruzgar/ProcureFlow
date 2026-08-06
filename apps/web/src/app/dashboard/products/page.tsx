"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { Product } from "@/lib/types";

const WRITER_ROLES = ["procurement_specialist", "manager", "admin"];

interface Me {
  role: string;
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [role, setRole] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    sku: "",
    name: "",
    unit: "pcs",
    min_stock_level: 0,
    reorder_qty: 0,
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Saf veri cekme (setState icermez) -> hem ilk yuklemede hem yenilemede kullanilir.
  const fetchProducts = useCallback(() => apiFetch<Product[]>("/products"), []);

  useEffect(() => {
    async function load() {
      try {
        const [items, me] = await Promise.all([
          fetchProducts(),
          apiFetch<Me>("/auth/me"),
        ]);
        setProducts(items);
        setRole(me.role);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load products");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [fetchProducts]);

  const canWrite = WRITER_ROLES.includes(role);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await apiFetch<Product>("/products", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setForm({ sku: "", name: "", unit: "pcs", min_stock_level: 0, reorder_qty: 0 });
      setProducts(await fetchProducts());
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create product");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
      <p className="mt-1 text-zinc-500">Catalog items tracked for stock and procurement.</p>

      {canWrite && (
        <form
          onSubmit={handleCreate}
          className="mt-6 grid gap-3 rounded-xl border border-black/[.08] bg-white p-4 dark:border-white/[.145] dark:bg-zinc-950 sm:grid-cols-6"
        >
          <input
            required
            placeholder="SKU"
            value={form.sku}
            onChange={(e) => setForm({ ...form, sku: e.target.value })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2] sm:col-span-1"
          />
          <input
            required
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2] sm:col-span-2"
          />
          <input
            placeholder="Unit"
            value={form.unit}
            onChange={(e) => setForm({ ...form, unit: e.target.value })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2]"
          />
          <input
            type="number"
            min={0}
            placeholder="Min stock"
            value={form.min_stock_level}
            onChange={(e) =>
              setForm({ ...form, min_stock_level: Number(e.target.value) })
            }
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2]"
          />
          <input
            type="number"
            min={0}
            placeholder="Reorder qty"
            value={form.reorder_qty}
            onChange={(e) => setForm({ ...form, reorder_qty: Number(e.target.value) })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2]"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-black sm:col-span-6"
          >
            {submitting ? "Adding…" : "Add product"}
          </button>
          {formError && (
            <p className="text-sm text-red-600 sm:col-span-6">{formError}</p>
          )}
        </form>
      )}

      <div className="mt-6 overflow-hidden rounded-xl border border-black/[.08] dark:border-white/[.145]">
        {loading ? (
          <p className="p-4 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-red-600">{error}</p>
        ) : products.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">No products yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">SKU</th>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Unit</th>
                <th className="px-4 py-2 text-right font-medium">Min stock</th>
                <th className="px-4 py-2 text-right font-medium">Reorder qty</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr
                  key={p.id}
                  className="border-t border-black/[.06] dark:border-white/[.08]"
                >
                  <td className="px-4 py-2 font-mono text-xs">{p.sku}</td>
                  <td className="px-4 py-2 font-medium">{p.name}</td>
                  <td className="px-4 py-2 text-zinc-500">{p.unit}</td>
                  <td className="px-4 py-2 text-right">{p.min_stock_level}</td>
                  <td className="px-4 py-2 text-right">{p.reorder_qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
