from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class SupplyEvent(Base):
    __tablename__ = "supply_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supply_id: Mapped[int] = mapped_column(
        ForeignKey("supplies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Тип события:
    # cargo_received  - "Принят карго" (Китай) -> places_count обязателен
    # cargo_to_rf     - "Доставляется в Россию" (опционально как событие, если нужно)
    # passed_to_tk    - "Передан в ТК" -> dest_warehouse_id обязателен
    # received_to_wh  - "Оприходован" (можно фиксировать событием)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Количество мест (коробки/паллеты). Для России вводится при passed_to_tk,
    # для Китая вводится при cargo_received.
    places_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Склад назначения (ТОЛЬКО при событии passed_to_tk)
    dest_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Трекинг (карго или ТК)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Стоимость события (например: стоимость карго или стоимость ТК)
    cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Примечание к событию
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    supply = relationship("Supply")
    dest_warehouse = relationship("Warehouse")
