from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __str__(self) -> str:
        return f"[{self.id}] {self.name}"
