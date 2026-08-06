"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type { Supplier } from "@/lib/types";

const WRITER_ROLES = ["procurement_specialist", "manager", "admin"];

interface Me {
  role: string;
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [role, setRole] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    contact_email: "",
    lead_time_days: 7,
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Saf veri cekme (setState icermez) -> hem ilk yuklemede hem yenilemede kullanilir.
  const fetchSuppliers = useCallback(() => apiFetch<Supplier[]>("/suppliers"), []);

  useEffect(() => {
    // Liste ve rol ayri ayri yuklenir: rol cagrisi basarisiz olsa bile
    // liste yine gorunur (sadece ekleme formu gizli kalir).
    async function loadList() {
      try {
        setSuppliers(await fetchSuppliers());
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load suppliers");
      } finally {
        setLoading(false);
      }
    }
    async function loadRole() {
      try {
        const me = await apiFetch<Me>("/auth/me");
        setRole(me.role);
      } catch {
        // rol alinamazsa yazma yetkisi varsayilan olarak kapali
      }
    }
    void loadList();
    void loadRole();
  }, [fetchSuppliers]);

  const canWrite = WRITER_ROLES.includes(role);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await apiFetch<Supplier>("/suppliers", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          contact_email: form.contact_email || null,
        }),
      });
      setForm({ name: "", contact_email: "", lead_time_days: 7 });
      setSuppliers(await fetchSuppliers());
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create supplier");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold tracking-tight">Suppliers</h1>
      <p className="mt-1 text-zinc-500">Vendors and their lead times.</p>

      {canWrite && (
        <form
          onSubmit={handleCreate}
          className="mt-6 grid gap-3 rounded-xl border border-black/[.08] bg-white p-4 dark:border-white/[.145] dark:bg-zinc-950 sm:grid-cols-6"
        >
          <input
            required
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2] sm:col-span-2"
          />
          <input
            type="email"
            placeholder="Contact email"
            value={form.contact_email}
            onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2] sm:col-span-2"
          />
          <input
            type="number"
            min={0}
            placeholder="Lead time (days)"
            value={form.lead_time_days}
            onChange={(e) =>
              setForm({ ...form, lead_time_days: Number(e.target.value) })
            }
            className="rounded-lg border border-black/[.12] bg-transparent px-3 py-2 text-sm dark:border-white/[.2]"
          />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-black"
          >
            {submitting ? "Adding…" : "Add"}
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
        ) : suppliers.length === 0 ? (
          <p className="p-4 text-sm text-zinc-500">No suppliers yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-black/[.03] text-left text-zinc-500 dark:bg-white/[.04]">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Contact</th>
                <th className="px-4 py-2 text-right font-medium">Lead time (days)</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr
                  key={s.id}
                  className="border-t border-black/[.06] dark:border-white/[.08]"
                >
                  <td className="px-4 py-2 font-medium">{s.name}</td>
                  <td className="px-4 py-2 text-zinc-500">{s.contact_email ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{s.lead_time_days}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        s.is_active
                          ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
                          : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                      }`}
                    >
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
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
