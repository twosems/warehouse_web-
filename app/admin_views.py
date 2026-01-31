from __future__ import annotations

from sqladmin import ModelView
from wtforms import SelectField

from app.models import (
    Product,
    Warehouse,
    Supplier,
    Supply,
    SupplyItem,
    SupplyEvent,
    Batch,
    Stock,
)

from app.models.enums import (
    SupplyStatus,
    SupplyEventType,
)

# ====================
# RU labels (UI only)
# ====================

SUPPLY_STATUS_RU = {
    SupplyStatus.draft: "Черновик",
    SupplyStatus.assembled: "Собрано",
    SupplyStatus.in_transit: "Доставляется на склад",
    SupplyStatus.received: "На складе",
    SupplyStatus.cancelled: "Отменена",
}

SUPPLY_EVENT_TYPE_RU = {
    SupplyEventType.passed_to_tk: "Передан в ТК (РФ)",
    SupplyEventType.received_to_wh: "Оприходован на склад",

    # CN-ветка
    SupplyEventType.supplier_paid_cny: "Оплата поставщику (CNY)",
    SupplyEventType.cargo_received: "Принят карго (Китай)",
    SupplyEventType.cargo_to_rf: "Отправлен из Китая в РФ",
}


def _ru(mapping: dict, value) -> str:
    if value is None:
        return ""
    return mapping.get(value, str(value))


# ====================
# Справочники
# ====================

class ProductAdmin(ModelView, model=Product):
    category = "Справочники"
    name = "Товар"
    name_plural = "Товары"

    column_list = [Product.id, Product.name]
    form_columns = [Product.name]


class WarehouseAdmin(ModelView, model=Warehouse):
    category = "Справочники"
    name = "Склад"
    name_plural = "Склады"

    column_list = [Warehouse.id, Warehouse.name]
    form_columns = [Warehouse.name]


class SupplierAdmin(ModelView, model=Supplier):
    category = "Справочники"
    name = "Поставщик"
    name_plural = "Поставщики"

    column_list = [Supplier.id, Supplier.name, Supplier.contact]
    form_columns = [Supplier.name, Supplier.contact, Supplier.note]


# ====================
# Документы — Закупки
# ====================

class SupplyAdmin(ModelView, model=Supply):
    category = "Документы"
    name = "Закупка"
    name_plural = "Закупки"

    column_list = [
        Supply.id,
        Supply.source,
        Supply.status,
        Supply.supplier,
        Supply.created_at,
        Supply.note,
    ]

    column_formatters = {
        "status": lambda obj, name: _ru(SUPPLY_STATUS_RU, getattr(obj, name)),
    }

    form_overrides = {
        "status": SelectField,
        "source": SelectField,
    }

    form_args = {
        "status": {
            "choices": [
                (SupplyStatus.draft.value, SUPPLY_STATUS_RU[SupplyStatus.draft]),
                (SupplyStatus.in_transit.value, SUPPLY_STATUS_RU[SupplyStatus.in_transit]),
                (SupplyStatus.received.value, SUPPLY_STATUS_RU[SupplyStatus.received]),
                (SupplyStatus.cancelled.value, SUPPLY_STATUS_RU[SupplyStatus.cancelled]),
            ],
            "coerce": lambda v: SupplyStatus(v) if v else None,
        },
        "source": {
            "choices": [
                ("RU", "RU — закупка в РФ"),
                ("CN", "CN — закупка в Китае"),
            ],
        },

    }


    form_columns = [
        Supply.supplier,
        Supply.source,
        Supply.status,
        Supply.note,
    ]


class SupplyItemAdmin(ModelView, model=SupplyItem):
    category = "Документы"
    name = "Позиция закупки"
    name_plural = "Позиции закупок"

    column_list = [
        SupplyItem.id,
        SupplyItem.supply,
        SupplyItem.product,
        SupplyItem.quantity,
        SupplyItem.unit_price_rub,
    ]

    form_columns = [
        SupplyItem.supply,
        SupplyItem.product,
        SupplyItem.quantity,
        SupplyItem.currency,
        SupplyItem.unit_price,
        SupplyItem.fx_rate,
    ]


class SupplyEventAdmin(ModelView, model=SupplyEvent):
    category = "Документы"
    name = "Событие закупки"
    name_plural = "События закупок"
    form_include_js = ["/static/admin/supply_event_filter.js"]

    column_list = [
        SupplyEvent.id,
        SupplyEvent.supply,
        SupplyEvent.event_type,
        SupplyEvent.places_count,
        SupplyEvent.dest_warehouse,
        SupplyEvent.tracking_number,
        SupplyEvent.cost,
        SupplyEvent.created_at,
    ]

    column_formatters = {
        "event_type": lambda obj, name: _ru(SUPPLY_EVENT_TYPE_RU, getattr(obj, name)),
    }

    form_overrides = {
        "event_type": SelectField,
    }

    form_args = {
        "event_type": {
            "choices": [
                (SupplyEventType.supplier_paid_cny.value, SUPPLY_EVENT_TYPE_RU[SupplyEventType.supplier_paid_cny]),
                (SupplyEventType.cargo_received.value, SUPPLY_EVENT_TYPE_RU[SupplyEventType.cargo_received]),
                (SupplyEventType.cargo_to_rf.value, SUPPLY_EVENT_TYPE_RU[SupplyEventType.cargo_to_rf]),
                (SupplyEventType.passed_to_tk.value, SUPPLY_EVENT_TYPE_RU[SupplyEventType.passed_to_tk]),
                (SupplyEventType.received_to_wh.value, SUPPLY_EVENT_TYPE_RU[SupplyEventType.received_to_wh]),
            ],
            "coerce": lambda v: SupplyEventType(v) if v else None,
        }
    }


    form_columns = [
        SupplyEvent.supply,
        SupplyEvent.event_type,
        SupplyEvent.places_count,
        SupplyEvent.dest_warehouse,
        SupplyEvent.tracking_number,
        SupplyEvent.cost,
        SupplyEvent.note,
    ]


# ====================
# Учёт
# ====================

class BatchAdmin(ModelView, model=Batch):
    category = "Учёт"
    name = "Партия"
    name_plural = "Партии"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Batch.id,
        Batch.supply,
        Batch.product,
        Batch.warehouse,
        Batch.quantity,
        Batch.unit_cost_final,
        Batch.created_at,
    ]


class StockAdmin(ModelView, model=Stock):
    category = "Учёт"
    name = "Остаток"
    name_plural = "Остатки"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Stock.id,
        Stock.warehouse,
        Stock.product,
        Stock.qty,
        Stock.updated_at,
    ]
