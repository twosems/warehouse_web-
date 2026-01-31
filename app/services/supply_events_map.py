from __future__ import annotations

from app.models.enums import SupplyEventType, SupplyStatus


def normalize_supply_source(source: str | None) -> str | None:
    """
    Приводим source к канону.
    Иногда в базе/форме может оказаться "RUB" — считаем это RU.
    """
    if not source:
        return None
    s = source.strip().upper()
    if s in {"RU", "RUB"}:
        return "RU"
    if s == "CN":
        return "CN"
    return s


# Какие события разрешены для каждой ветки (RU / CN)
ALLOWED_EVENTS_BY_SOURCE: dict[str, set[SupplyEventType]] = {
    "RU": {
        SupplyEventType.passed_to_tk,
        SupplyEventType.received_to_wh,
    },
    "CN": {
        SupplyEventType.supplier_paid_cny,
        SupplyEventType.cargo_received,
        SupplyEventType.cargo_to_rf,
        # после ТК логика общая
        SupplyEventType.passed_to_tk,
        SupplyEventType.received_to_wh,
    },
}

# Из каких статусов можно создавать конкретное событие
ALLOWED_FROM_STATUS_BY_EVENT: dict[SupplyEventType, set[SupplyStatus]] = {
    # CN: draft -> assembled -> in_transit -> received
    SupplyEventType.supplier_paid_cny: {SupplyStatus.draft},
    SupplyEventType.cargo_received: {SupplyStatus.draft, SupplyStatus.assembled},  # мягко (идемпотентно)
    SupplyEventType.cargo_to_rf: {SupplyStatus.assembled},

    # RU: draft -> in_transit -> received
    SupplyEventType.passed_to_tk: {SupplyStatus.draft},
    SupplyEventType.received_to_wh: {SupplyStatus.in_transit},
}

# Маппинг событие -> статус (имя ждёт listener: EVENT_TYPE_TO_STATUS)
EVENT_TYPE_TO_STATUS: dict[SupplyEventType, SupplyStatus] = {
    # CN
    SupplyEventType.supplier_paid_cny: SupplyStatus.assembled,
    SupplyEventType.cargo_received: SupplyStatus.assembled,
    SupplyEventType.cargo_to_rf: SupplyStatus.in_transit,

    # RU + общий финал
    SupplyEventType.passed_to_tk: SupplyStatus.in_transit,
    SupplyEventType.received_to_wh: SupplyStatus.received,
}


def is_event_allowed_for_source(source: str | None, event_type: SupplyEventType) -> bool:
    src = normalize_supply_source(source)
    if not src:
        return False
    allowed = ALLOWED_EVENTS_BY_SOURCE.get(src)
    return bool(allowed and event_type in allowed)


def is_event_allowed_from_status(current_status: SupplyStatus, event_type: SupplyEventType) -> bool:
    allowed = ALLOWED_FROM_STATUS_BY_EVENT.get(event_type)
    return bool(allowed and current_status in allowed)


def allowed_events_for_supply(source: str | None, status: SupplyStatus | None) -> set[SupplyEventType]:
    """
    То, что нужно для админки: список EventType, который:
    - разрешён для ветки (RU/CN)
    - разрешён из текущего статуса закупки
    """
    src = normalize_supply_source(source)
    if not src or status is None:
        return set()

    by_source = ALLOWED_EVENTS_BY_SOURCE.get(src, set())
    result: set[SupplyEventType] = set()

    for et in by_source:
        if is_event_allowed_from_status(status, et):
            result.add(et)

    return result
