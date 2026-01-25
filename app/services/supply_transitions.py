from app.models.enums import SupplyStatus


ALLOWED_SUPPLY_TRANSITIONS: dict[SupplyStatus, set[SupplyStatus]] = {
    SupplyStatus.draft: {
        SupplyStatus.assembled,
        SupplyStatus.cancelled,
    },
    SupplyStatus.assembled: {
        SupplyStatus.in_transit,
        SupplyStatus.cancelled,
    },
    SupplyStatus.in_transit: {
        SupplyStatus.received,
    },
    SupplyStatus.received: set(),
    SupplyStatus.cancelled: set(),
}


def validate_supply_transition(
        current: SupplyStatus,
        target: SupplyStatus,
) -> None:
    allowed = ALLOWED_SUPPLY_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Invalid supply status transition: {current} → {target}"
        )
