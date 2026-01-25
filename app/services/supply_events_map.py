from __future__ import annotations

from app.models.enums import SupplyEventType, SupplyStatus

# Маппинг: какое событие -> какой статус Supply
# Важно: ключи теперь Enum, а не строки.
EVENT_TYPE_TO_STATUS: dict[SupplyEventType, SupplyStatus] = {
    SupplyEventType.cargo_received: SupplyStatus.assembled,
    SupplyEventType.cargo_to_rf: SupplyStatus.in_transit,
    SupplyEventType.passed_to_tk: SupplyStatus.in_transit,
    SupplyEventType.received_to_wh: SupplyStatus.received,
}
