# ProcureFlow Web

Next.js (App Router) frontend for ProcureFlow. TypeScript, Tailwind CSS,
shadcn/ui, and Supabase Auth.

## Local development

```bash
cd apps/web
npm install
npm run dev
```

- App: http://localhost:3000
- Sign in: http://localhost:3000/login
- Dashboard (protected): http://localhost:3000/dashboard

Copy `.env.example` to `.env.local` and fill in the Supabase values.

## Structure

```text
src/
  app/            # routes (/, /login, /dashboard)
  components/     # reusable UI components
  lib/supabase/   # browser + server Supabase clients
  proxy.ts        # session refresh + optimistic route protection
```

## Scripts

- `npm run dev` - start dev server
- `npm run build` - production build
- `npm run lint` - lint
