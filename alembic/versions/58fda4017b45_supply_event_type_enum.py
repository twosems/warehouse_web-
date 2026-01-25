"""supply event type enum

Revision ID: 58fda4017b45
Revises: 76fbb45b541e
Create Date: 2026-01-24 02:26:28.890660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58fda4017b45'
down_revision: Union[str, Sequence[str], None] = '76fbb45b541e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) создать enum-тип
    event_type_enum = sa.Enum(
        'cargo_received',
        'cargo_to_rf',
        'passed_to_tk',
        'received_to_wh',
        name='supply_event_type'
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # 2) изменить тип колонки с USING
    op.execute(
        "ALTER TABLE supply_events "
        "ALTER COLUMN event_type "
        "TYPE supply_event_type "
        "USING event_type::supply_event_type"
    )


def downgrade() -> None:
    # 1) вернуть строку
    op.alter_column(
        'supply_events',
        'event_type',
        existing_type=sa.Enum(
            'cargo_received',
            'cargo_to_rf',
            'passed_to_tk',
            'received_to_wh',
            name='supply_event_type'
        ),
        type_=sa.VARCHAR(length=30),
        nullable=False,
    )

    # 2) удалить enum-тип
    event_type_enum = sa.Enum(
        'cargo_received',
        'cargo_to_rf',
        'passed_to_tk',
        'received_to_wh',
        name='supply_event_type'
    )
    event_type_enum.drop(op.get_bind(), checkfirst=True)
