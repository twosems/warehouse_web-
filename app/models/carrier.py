from __future__ import annotations

from sqlalchemy import Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base
from app.models.enums import CarrierType


class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    type: Mapped[CarrierType] = mapped_column(
        Enum(CarrierType, name="carrier_type"),
        nullable=False,
        index=True,
        comment="cargo / tk",
    )

    contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
