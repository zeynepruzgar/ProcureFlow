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

        <footer className="mt-auto text-sm text-zinc-500">
          Phase 0 &mdash; project scaffold. See the roadmap in{" "}
          <code className="rounded bg-black/[.06] px-1.5 py-0.5 font-mono text-[0.9em] dark:bg-white/[.08]">
            docs/ROADMAP.md
          </code>
          .
        </footer>
      </main>
    </div>
  );
}
