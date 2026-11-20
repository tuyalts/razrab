from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    occurred_at: datetime
    payload: dict = field(default_factory=dict)