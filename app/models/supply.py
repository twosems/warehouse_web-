from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base
from app.models.enums import SupplyStatus


class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # RU / CN
    source: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
        comment="Source of supply: RU or CN",
    )

    dest_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Destination warehouse фиксируется на passed_to_tk",
    )

    cargo_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
        comment="Cargo delivery cost (known in RF before passing to TK)",
    )

    status: Mapped[SupplyStatus] = mapped_column(
        Enum(SupplyStatus, name="supply_status"),
        nullable=False,
        index=True,
        default=SupplyStatus.draft,
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    supplier = relationship("Supplier", backref="supplies")

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
      # Человекочитаемое имя закупки для админки и связанных списков
       supplier_name: str | None = None
       try:
        supplier_name = getattr(self.supplier, "name", None)
       except Exception:
           supplier_name = None

       source = (self.source or "").upper()
       created = self.created_at.strftime("%Y-%m-%d") if self.created_at else ""
       supplier_part = supplier_name or f"Поставщик #{self.supplier_id}"
       status = self.status.value if self.status else ""

       return f"Закупка #{self.id} | {source} | {supplier_part} | Статус: {status} | {created}"

