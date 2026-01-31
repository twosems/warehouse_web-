from __future__ import annotations

from datetime import datetime

from sqlalchemy import event, select, func
from sqlalchemy.orm import Session

from app.models import MarketplaceShipment, MarketplaceShipmentEvent, MarketplaceShipmentItem, Stock
from app.models.enums import MarketplaceShipmentEventType
from app.services.marketplace_shipment_events_map import EVENT_TYPE_TO_STATUS
from app.services.marketplace_shipment_transitions import validate_mp_shipment_transition


@event.listens_for(Session, "before_flush")
def mp_shipment_apply_status_and_stock(session: Session, flush_context, instances):
    """
    ЕДИНЫЙ источник истины по событиям MarketplaceShipmentEvent:

    - Меняет MarketplaceShipment.status по событию
    - Проверяет допустимость перехода
    - На событии sent_to_delivery: списывает товар со склада (Stock.qty уменьшается)
    - На cancelled: если ранее было списание, возвращает товар (Stock.qty увеличивается)

    Важно:
    - Списание делаем один раз: повторное sent_to_delivery запрещаем.
    """

    for obj in list(session.new):
        if not isinstance(obj, MarketplaceShipmentEvent):
            continue

        with session.no_autoflush:
            shipment = session.get(MarketplaceShipment, obj.shipment_id)
            if shipment is None:
                raise ValueError("MarketplaceShipment not found for event")

            target_status = EVENT_TYPE_TO_STATUS[obj.event_type]
            validate_mp_shipment_transition(shipment.status, target_status)

            # --- Защита от двойного "sent_to_delivery" ---
            if obj.event_type == MarketplaceShipmentEventType.sent_to_delivery:
                already_sent = session.execute(
                    select(func.count(MarketplaceShipmentEvent.id)).where(
                        MarketplaceShipmentEvent.shipment_id == shipment.id,
                        MarketplaceShipmentEvent.event_type == MarketplaceShipmentEventType.sent_to_delivery,
                        )
                ).scalar_one()

                # already_sent учитывает события в БД, но не текущий obj (он в session.new)
                if already_sent > 0:
                    raise ValueError("Shipment already sent to delivery (double stock write-off forbidden)")

                # списываем по позициям
                items = session.execute(
                    select(MarketplaceShipmentItem).where(MarketplaceShipmentItem.shipment_id == shipment.id)
                ).scalars().all()

                if not items:
                    raise ValueError("Cannot send shipment to delivery without items")

                for it in items:
                    stock = session.execute(
                        select(Stock).where(
                            Stock.warehouse_id == shipment.source_warehouse_id,
                            Stock.product_id == it.product_id,
                            )
                    ).scalar_one_or_none()

                    if stock is None:
                        raise ValueError("Stock row not found for shipment item (cannot write off)")

                    new_qty = int(stock.qty) - int(it.quantity)
                    if new_qty < 0:
                        raise ValueError("Stock cannot be negative (not enough items)")

                    stock.qty = new_qty
                    stock.updated_at = datetime.utcnow()
                    session.add(stock)

            # --- Cancel: если списание было, возвращаем ---
            if obj.event_type == MarketplaceShipmentEventType.cancelled:
                was_sent = session.execute(
                    select(func.count(MarketplaceShipmentEvent.id)).where(
                        MarketplaceShipmentEvent.shipment_id == shipment.id,
                        MarketplaceShipmentEvent.event_type == MarketplaceShipmentEventType.sent_to_delivery,
                        )
                ).scalar_one()

                # возвращаем только если реально было списание ранее
                if was_sent > 0:
                    items = session.execute(
                        select(MarketplaceShipmentItem).where(MarketplaceShipmentItem.shipment_id == shipment.id)
                    ).scalars().all()

                    for it in items:
                        stock = session.execute(
                            select(Stock).where(
                                Stock.warehouse_id == shipment.source_warehouse_id,
                                Stock.product_id == it.product_id,
                                )
                        ).scalar_one_or_none()

                        if stock is None:
                            # если по какой-то причине строки нет — создадим (чтобы возврат не потерялся)
                            stock = Stock(
                                warehouse_id=shipment.source_warehouse_id,
                                product_id=it.product_id,
                                qty=0,
                            )
                            session.add(stock)

                        stock.qty = int(stock.qty) + int(it.quantity)
                        stock.updated_at = datetime.utcnow()
                        session.add(stock)

            # apply status at the end
            shipment.status = target_status
            session.add(shipment)
