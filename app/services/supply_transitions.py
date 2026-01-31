# app/services/supply_transitions.py
from __future__ import annotations

from app.models.enums import SupplyStatus

# Канон v2:
# RU: draft -> in_transit -> received
# CN: draft -> assembled -> in_transit -> received
# + cancelled
ALLOWED_SUPPLY_TRANSITIONS: dict[SupplyStatus, set[SupplyStatus]] = {
    SupplyStatus.draft: {
        SupplyStatus.assembled,
        SupplyStatus.in_transit,
        SupplyStatus.cancelled,
    },
    SupplyStatus.assembled: {
        SupplyStatus.in_transit,
        SupplyStatus.cancelled,
    },
    SupplyStatus.in_transit: {
        SupplyStatus.received,
        # если надо разрешить отмену "в пути" — добавим позже
        # SupplyStatus.cancelled,
    },
    SupplyStatus.received: set(),
    SupplyStatus.cancelled: set(),
}


def validate_supply_transition(current: SupplyStatus, target: SupplyStatus) -> None:
    # статус не меняется — ОК (нужно для событий типа cargo_received)
    if current == target:
        return

    allowed = ALLOWED_SUPPLY_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid supply status transition: {current} → {target}")
