from sqladmin import Admin

from app.core.db import engine
from app.admin_views import (
    # Справочники
    ProductAdmin,
    WarehouseAdmin,
    SupplierAdmin,

    # Документы
    SupplyAdmin,
    SupplyItemAdmin,
    SupplyEventAdmin,

    # Учёт
    BatchAdmin,
    StockAdmin,
)


def setup_admin(app):
    admin = Admin(app, engine)

    # Справочники
    admin.add_view(ProductAdmin)
    admin.add_view(WarehouseAdmin)
    admin.add_view(SupplierAdmin)

    # Документы
    admin.add_view(SupplyAdmin)
    admin.add_view(SupplyItemAdmin)
    admin.add_view(SupplyEventAdmin)

    # Учёт
    admin.add_view(BatchAdmin)
    admin.add_view(StockAdmin)

    return admin
