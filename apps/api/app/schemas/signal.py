from typing import Literal

from pydantic import BaseModel

SignalType = Literal["low_stock", "delayed_order", "price_spike"]
Severity = Literal["low", "medium", "high"]
SignalStatus = Literal["open", "handled"]


class Signal(BaseModel):
    id: str
    type: SignalType
    entity_id: str
    severity: Severity
    status: SignalStatus
    detected_at: str | None = None


class ScanResult(BaseModel):
    """POST /scan yaniti: kac sinyal olusturuldu/guncellendi/kapatildi."""

    created: int
    updated: int
    closed: int
    open_signals: list[Signal]
