from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supply, SupplyItem, SupplyEvent
from app.models.enums import SupplyStatus, SupplyEventType
from app.schemas.supply import SupplyCreate
from app.schemas.supply_event import SupplyEventCreate


async def create_supply(db: AsyncSession, data: SupplyCreate) -> Supply:
    """
    Создание закупки + позиций (БЕЗ commit внутри).
    commit делает роутер/верхний слой.

    unit_price_rub можно считать и тут, но даже если забыть —
    listener supply_item_listeners гарантирует заполнение.
    """
    supply = Supply(
        supplier_id=data.supplier_id,
        source=data.source,  # "RU" / "CN" (строка)
        status=SupplyStatus.draft,
        note=data.note,
    )
    db.add(supply)
    await db.flush()  # supply.id

    for item in data.items:
        db.add(
            SupplyItem(
                supply_id=supply.id,
                product_id=item.product_id,
                quantity=item.quantity,
                currency=item.currency,
                unit_price=item.unit_price,
                fx_rate=item.fx_rate,
                # unit_price_rub НЕ обязаны ставить — listener заполнит
            )
        )

    await db.flush()
    await db.refresh(supply)
    return supply


async def add_supply_event(db: AsyncSession, supply: Supply, data: SupplyEventCreate) -> Supply:
    """
    Сервис только создаёт событие.
    Статус supply и Batch'и изменит/создаст listener (before_flush).

    Здесь делаем МИНИМАЛЬНУЮ бизнес-валидацию RU/CN, чтобы:
    - RU закупка не могла получить CN события
    - CN закупка не могла получить RU-only события (если такие появятся)
    """
    source = (supply.source or "").strip().upper()

    # CN события (по текущему enum из админки)
    cn_only_events = {
        SupplyEventType.cargo_received,  # "Принят карго (Китай)"
        SupplyEventType.cargo_to_rf,     # "Отправлен из Китая в РФ"
    }

    # RU события (в текущем enum они общие, но оставим задел)
    # Сейчас "passed_to_tk" и "received_to_wh" допустимы и для RU, и для CN,
    # потому что после передачи в ТК цепочка у тебя общая.
    # Если позже введём RU-only события — добавим сюда.
    ru_only_events: set[SupplyEventType] = set()

    if source == "RU" and data.event_type in cn_only_events:
        raise ValueError("Нельзя добавлять события Китая к RU-закупке")

    if source == "CN" and data.event_type in ru_only_events:
        raise ValueError("Нельзя добавлять RU-события к CN-закупке")

    event = SupplyEvent(
        supply_id=supply.id,
        event_type=data.event_type,
        places_count=data.places_count,
        dest_warehouse_id=data.dest_warehouse_id,
        tracking_number=data.tracking_number,
        cost=data.cost,
        note=data.note,
    )
    db.add(event)

    await db.flush()
    await db.refresh(supply)
    return supply
