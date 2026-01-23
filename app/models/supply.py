from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Поставщик
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Источник закупки: RU / CN
    source: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
        comment="Source of supply: RU or CN",
    )

    # Текущий статус (СТРОГО из канона)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Примечание
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Связи
    supplier = relationship("Supplier")
