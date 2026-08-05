# Supabase

Database schema, Row Level Security (RLS) policies, and seed data for ProcureFlow.

Populated in **Phase 1** (see [../docs/ROADMAP.md](../docs/ROADMAP.md)). The data
model is defined in [../docs/DATA_MODEL.md](../docs/DATA_MODEL.md).

## Planned layout

```text
supabase/
  migrations/   # SQL migrations (schema + RLS)
  seed.sql      # demo data (products, suppliers, stock, orders, prices)
```

## Notes

- Auth is handled by Supabase Auth; app roles live in `profiles.role`.
- RLS is enabled on every table; the agent uses a restricted role that can only
  write `recommendations` and `purchase_requests (draft)`.
