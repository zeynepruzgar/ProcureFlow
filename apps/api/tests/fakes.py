"""Testler arasi paylasilan sahte Supabase istemcisi.

Gercek `supabase-py` Client'in kullandigimiz kadar bir alt kumesini taklit
eder: table(...).select/insert/update(...).eq/in_/order/limit(...).execute().
Bellekte, tablo basina bir liste tutar; boylece agent grafigini (interrupt +
resume dahil) gercek bir Postgres/Supabase olmadan uctan uca test edebiliriz.

Not: pytest bu dosyayi bir test modulu olarak ALGILAMAZ (adi test_*.py degil),
sadece diger test dosyalarindan import edilir.
"""

from __future__ import annotations

import uuid
from typing import Any


class FakeResult:
    def __init__(self, data: list[dict[str, Any]]):
        self.data = data


class FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self._mode: str | None = None
        self._payload: dict[str, Any] | None = None
        self._order_col: str | None = None
        self._desc = False
        self._limit: int | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> FakeQuery:
        self._mode = "select"
        return self

    def insert(self, payload: dict[str, Any]) -> FakeQuery:
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> FakeQuery:
        self._mode = "update"
        self._payload = payload
        return self

    def eq(self, col: str, val: Any) -> FakeQuery:
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col: str, vals: Any) -> FakeQuery:
        self._filters.append(("in", col, set(vals)))
        return self

    def order(self, col: str, desc: bool = False) -> FakeQuery:
        self._order_col = col
        self._desc = desc
        return self

    def limit(self, n: int) -> FakeQuery:
        self._limit = n
        return self

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "in" and row.get(col) not in val:
                return False
        return True

    def execute(self) -> FakeResult:
        if self._mode == "insert":
            row = dict(self._payload or {})
            row.setdefault("id", str(uuid.uuid4()))
            row.setdefault("created_at", "2026-08-16T00:00:00Z")
            self._rows.append(row)
            return FakeResult([row])

        if self._mode == "update":
            matched = [r for r in self._rows if self._matches(r)]
            for row in matched:
                row.update(self._payload or {})
            return FakeResult(matched)

        matched = [r for r in self._rows if self._matches(r)]
        if self._order_col:
            matched = sorted(
                matched, key=lambda r: r.get(self._order_col), reverse=self._desc
            )
        if self._limit is not None:
            matched = matched[: self._limit]
        return FakeResult(matched)


class FakeSupabaseClient:
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            k: list(v) for k, v in (seed or {}).items()
        }

    def table(self, name: str) -> FakeQuery:
        rows = self._tables.setdefault(name, [])
        return FakeQuery(rows)

    def rows(self, name: str) -> list[dict[str, Any]]:
        """Test assertion'lari icin dogrudan tablo icerigine erisim."""
        return self._tables.setdefault(name, [])
