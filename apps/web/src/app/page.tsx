import Link from "next/link";

import { ApiStatus } from "@/components/api-status";

const roles = [
  "Employee",
  "Procurement Specialist",
  "Manager",
  "Admin",
  "System Agent",
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-3xl flex-1 flex-col gap-10 px-6 py-16 sm:px-8">
        <nav className="flex justify-end gap-3 text-sm font-medium">
          <Link
            href="/login"
            className="rounded-lg border border-black/[.12] px-4 py-2 transition-colors hover:bg-black/[.04] dark:border-white/[.2] dark:hover:bg-white/[.06]"
          >
            Sign in
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg bg-foreground px-4 py-2 text-background transition-opacity hover:opacity-90"
          >
            Dashboard
          </Link>
        </nav>
        <header className="flex flex-col gap-3">
          <span className="text-sm font-medium uppercase tracking-widest text-zinc-500">
            ProcureFlow
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50 sm:text-4xl">
            Agentic Procurement &amp; Inventory Operations
          </h1>
          <p className="max-w-xl text-lg leading-8 text-zinc-600 dark:text-zinc-400">
            Detect low stock, delayed orders, and unusual price increases. An AI
            agent reviews the data and prepares a justified purchase
            recommendation for manager approval &mdash; it never completes a
            purchase on its own.
          </p>
        </header>

        <ApiStatus />

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium uppercase tracking-widest text-zinc-500">
            Roles
          </h2>
          <ul className="flex flex-wrap gap-2">
            {roles.map((role) => (
              <li
                key={role}
                className="rounded-full border border-black/[.08] px-3 py-1 text-sm text-zinc-700 dark:border-white/[.145] dark:text-zinc-300"
              >
                {role}
              </li>
            ))}
          </ul>
        </section>

      </main>
    </div>
  );
}
