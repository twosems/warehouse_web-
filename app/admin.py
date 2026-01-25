from sqladmin import Admin

from app.core.db import engine
from app.admin_views import (
    ProductAdmin,
    WarehouseAdmin,
    SupplierAdmin,
    SupplyAdmin,
    SupplyItemAdmin,
    SupplyEventAdmin,
    BatchAdmin,
    StockAdmin,
)


def setup_admin(app):
    admin = Admin(app, engine)

    admin.add_view(ProductAdmin)
    admin.add_view(WarehouseAdmin)
    admin.add_view(SupplierAdmin)

    admin.add_view(SupplyAdmin)
    admin.add_view(SupplyItemAdmin)
    admin.add_view(SupplyEventAdmin)
    admin.add_view(BatchAdmin)
    admin.add_view(StockAdmin)
    return admin
