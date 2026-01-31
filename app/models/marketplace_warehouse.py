from __future__ import annotations

from sqlalchemy import Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.models.enums import MarketplaceType


class MarketplaceWarehouse(Base):
    __tablename__ = "marketplace_warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    marketplace: Mapped[MarketplaceType] = mapped_column(
        Enum(MarketplaceType, name="marketplace_type"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
