from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Batch, Supply, SupplyEvent, SupplyItem
from app.models.enums import SupplyEventType
from app.services.logistics_cost_allocator import allocate_logistics_cost
from app.services.supply_events_map import (
    EVENT_TYPE_TO_STATUS,
    is_event_allowed_for_source,
    is_event_allowed_from_status,
)
from app.services.supply_transitions import validate_supply_transition


@event.listens_for(Session, "before_flush")
def supply_apply_status_and_batches(session: Session, flush_context, instances):
    """
    ЕДИНЫЙ источник истины для SupplyEvent:

    - Проверяет, что событие разрешено для ветки закупки (RU/CN)
    - Проверяет, что событие разрешено из текущего статуса
    - Меняет Supply.status по событию (через EVENT_TYPE_TO_STATUS)
    - Проверяет допустимость перехода (validate_supply_transition)

    Канон N2/N1:
    - passed_to_tk: фиксируем склад назначения (Supply.dest_warehouse_id) из события
    - received_to_wh:
        * dest_warehouse_id можно не передавать, если он уже в Supply.dest_warehouse_id
        * нельзя оприходовать дважды (если Batch уже создан)
        * нужны SupplyItem
        * создаём Batch
        * распределяем логистику по unit_cost_final
    """

    for obj in list(session.new):
        if not isinstance(obj, SupplyEvent):
            continue

        supply = session.get(Supply, obj.supply_id)
        if not supply:
            continue

        event_type = obj.event_type

        # 0) Строго: событие должно подходить ветке RU/CN
        if not is_event_allowed_for_source(getattr(supply, "source", None), event_type):
            raise ValueError(
                f"Event {event_type.value} is not allowed for supply source={getattr(supply, 'source', None)}"
            )

        # 1) КАНОН: фиксируем склад назначения на passed_to_tk
        if event_type == SupplyEventType.passed_to_tk:
            if not obj.dest_warehouse_id:
                raise ValueError("dest_warehouse_id is required for passed_to_tk (canon)")
            supply.dest_warehouse_id = obj.dest_warehouse_id
            session.add(supply)

        # 2) Preconditions для received_to_wh
        if event_type == SupplyEventType.received_to_wh:
            # dest_warehouse_id: берём из Supply, если не передан в событии
            if not obj.dest_warehouse_id:
                dest_from_supply = getattr(supply, "dest_warehouse_id", None)
                if not dest_from_supply:
                    raise ValueError(
                        "dest_warehouse_id is required (either in Supply or in event) for received_to_wh"
                    )
                obj.dest_warehouse_id = dest_from_supply
            else:
                # если передали в событии — синхронизируем в Supply, если там пусто
                if getattr(supply, "dest_warehouse_id", None) is None:
                    supply.dest_warehouse_id = obj.dest_warehouse_id
                    session.add(supply)

            # защита от дубля: если уже создавали партии по этой поставке
            with session.no_autoflush:
                existing = session.execute(
                    select(Batch.id).where(Batch.supply_id == supply.id).limit(1)
                ).first()
            if existing:
                raise ValueError("Batches already created for this supply")

            # items должны быть
            with session.no_autoflush:
                items = session.execute(
                    select(SupplyItem).where(SupplyItem.supply_id == supply.id)
                ).scalars().all()
            if not items:
                raise ValueError("Supply has no items")

        # 3) Строго: событие должно быть допустимо из текущего статуса
        if not is_event_allowed_from_status(supply.status, event_type):
            raise ValueError(
                f"Event {event_type.value} is not allowed from status {supply.status.value}"
            )

        # 4) Статус по карте событий
        new_status = EVENT_TYPE_TO_STATUS.get(event_type)
        if new_status is None:
            continue

        # 5) Идемпотентность: если статус уже такой — ок
        if new_status != supply.status:
            validate_supply_transition(supply.status, new_status)
            supply.status = new_status
            session.add(supply)

        # 6) Создание Batch + распределение логистики
        if event_type == SupplyEventType.received_to_wh:
            with session.no_autoflush:
                items = session.execute(
                    select(SupplyItem).where(SupplyItem.supply_id == supply.id)
                ).scalars().all()

            created_batches: list[Batch] = []
            for it in items:
                b = Batch(
                    supply_id=supply.id,
                    product_id=it.product_id,
                    warehouse_id=obj.dest_warehouse_id,
                    quantity=it.quantity,
                    unit_cost_final=it.unit_price_rub,
                )
                session.add(b)
                created_batches.append(b)

            total = Decimal("0")

            with session.no_autoflush:
                db_costs = session.execute(
                    select(SupplyEvent.cost).where(SupplyEvent.supply_id == supply.id)
                ).scalars().all()

            for c in db_costs:
                if c is not None:
                    total += Decimal(str(c))

            for e in session.new:
                if isinstance(e, SupplyEvent) and e.supply_id == supply.id and e.cost is not None:
                    total += Decimal(str(e.cost))

            if total > 0 and created_batches:
                allocate_logistics_cost(created_batches, total)
