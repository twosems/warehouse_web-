from sqladmin import ModelView

from app.models import (
    Product,
    Warehouse,
    Supplier,
    Supply,
    SupplyItem,
    SupplyEvent,
    Batch,
)


# --------------------
# Reference models
# --------------------

class ProductAdmin(ModelView, model=Product):
    name = "Product"
    name_plural = "Products"

    column_list = [Product.id, Product.name]
    column_searchable_list = [Product.name]
    column_sortable_list = [Product.id, Product.name]
    form_columns = [Product.name]


class WarehouseAdmin(ModelView, model=Warehouse):
    name = "Warehouse"
    name_plural = "Warehouses"

    column_list = [Warehouse.id, Warehouse.name]
    column_searchable_list = [Warehouse.name]
    column_sortable_list = [Warehouse.id, Warehouse.name]
    form_columns = [Warehouse.name]


class SupplierAdmin(ModelView, model=Supplier):
    name = "Supplier"
    name_plural = "Suppliers"

    column_list = [Supplier.id, Supplier.name, Supplier.contact, Supplier.note]
    column_searchable_list = [Supplier.name, Supplier.contact]
    column_sortable_list = [Supplier.id, Supplier.name]
    form_columns = [Supplier.name, Supplier.contact, Supplier.note]


# --------------------
# Supply flow models
# --------------------

class SupplyAdmin(ModelView, model=Supply):
    name = "Supply"
    name_plural = "Supplies"

    column_list = [
        Supply.id,
        Supply.source,
        Supply.status,
        Supply.supplier,
        Supply.created_at,
        Supply.note,
    ]
    column_searchable_list = [Supply.status, Supply.source]
    column_sortable_list = [Supply.id, Supply.created_at, Supply.status, Supply.source]
    form_columns = [Supply.supplier, Supply.source, Supply.status, Supply.note]


class SupplyItemAdmin(ModelView, model=SupplyItem):
    name = "Supply Item"
    name_plural = "Supply Items"

    column_list = [
        SupplyItem.id,
        SupplyItem.supply,
        SupplyItem.product,
        SupplyItem.quantity,
        SupplyItem.currency,
        SupplyItem.unit_price,
        SupplyItem.fx_rate,
        SupplyItem.unit_price_rub,
    ]
    column_sortable_list = [SupplyItem.id, SupplyItem.quantity]
    form_columns = [
        SupplyItem.supply,
        SupplyItem.product,
        SupplyItem.quantity,
        SupplyItem.currency,
        SupplyItem.unit_price,
        SupplyItem.fx_rate,
        SupplyItem.unit_price_rub,
    ]


class SupplyEventAdmin(ModelView, model=SupplyEvent):
    name = "Supply Event"
    name_plural = "Supply Events"

    column_list = [
        SupplyEvent.id,
        SupplyEvent.supply,
        SupplyEvent.event_type,
        SupplyEvent.places_count,
        SupplyEvent.dest_warehouse,
        SupplyEvent.tracking_number,
        SupplyEvent.cost,
        SupplyEvent.created_at,
        SupplyEvent.note,
    ]
    column_searchable_list = [SupplyEvent.event_type, SupplyEvent.tracking_number]
    column_sortable_list = [SupplyEvent.id, SupplyEvent.created_at, SupplyEvent.event_type]
    form_columns = [
        SupplyEvent.supply,
        SupplyEvent.event_type,
        SupplyEvent.places_count,
        SupplyEvent.dest_warehouse,
        SupplyEvent.tracking_number,
        SupplyEvent.cost,
        SupplyEvent.note,
    ]


class BatchAdmin(ModelView, model=Batch):
    name = "Batch"
    name_plural = "Batches"

    column_list = [
        Batch.id,
        Batch.supply,
        Batch.product,
        Batch.warehouse,
        Batch.quantity,
        Batch.unit_cost_final,
        Batch.created_at,
    ]
    column_sortable_list = [Batch.id, Batch.created_at, Batch.quantity]
    form_columns = [
        Batch.supply,
        Batch.product,
        Batch.warehouse,
        Batch.quantity,
        Batch.unit_cost_final,
    ]
