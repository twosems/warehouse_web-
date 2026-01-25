"""supply status enum

Revision ID: 76fbb45b541e
Revises: 2fe4405d2ede
Create Date: 2026-01-24 01:56:40.091761
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '76fbb45b541e'
down_revision: Union[str, Sequence[str], None] = '2fe4405d2ede'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ создаём enum ТИП
    supply_status_enum = sa.Enum(
        'draft',
        'assembled',
        'in_transit',
        'received',
        'cancelled',
        name='supply_status'
    )
    supply_status_enum.create(op.get_bind(), checkfirst=True)

    # 2️⃣ меняем тип колонки + USING
    op.execute(
        "ALTER TABLE supplies "
        "ALTER COLUMN status "
        "TYPE supply_status "
        "USING status::supply_status"
    )


def downgrade() -> None:
    # 1️⃣ возвращаем VARCHAR
    op.alter_column(
        'supplies',
        'status',
        existing_type=sa.Enum(
            'draft',
            'assembled',
            'in_transit',
            'received',
            'cancelled',
            name='supply_status'
        ),
        type_=sa.VARCHAR(length=50),
        nullable=False,
    )

    # 2️⃣ удаляем enum тип
    supply_status_enum = sa.Enum(
        'draft',
        'assembled',
        'in_transit',
        'received',
        'cancelled',
        name='supply_status'
    )
    supply_status_enum.drop(op.get_bind(), checkfirst=True)
