from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.models.enums import SupplyStatus


class Supply(Base):
    __tablename__ = "supplies"

    # --- PK ---
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # --- Поставщик ---
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Источник закупки ---
    # RU / CN (пока строка, enum сделаем позже при необходимости)
    source: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
        comment="Source of supply: RU or CN",
    )

    # --- Статус поставки (канонический enum) ---
    status: Mapped[SupplyStatus] = mapped_column(
        Enum(SupplyStatus, name="supply_status"),
        nullable=False,
        index=True,
        default=SupplyStatus.draft,
    )

    # --- Примечание ---
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --- Дата создания ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # --- Связи ---
    supplier = relationship(
        "Supplier",
        backref="supplies",
    )

    items = relationship(
        "SupplyItem",
        back_populates="supply",
        cascade="all, delete-orphan",
    )

    events = relationship(
        "SupplyEvent",
        back_populates="supply",
        cascade="all, delete-orphan",
        order_by="SupplyEvent.created_at",
    )

    def __str__(self) -> str:
        return f"Supply #{self.id} | {self.source} | {self.status}"
