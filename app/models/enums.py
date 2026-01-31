import enum


class SupplyStatus(str, enum.Enum):
    draft = "draft"
    assembled = "assembled"
    in_transit = "in_transit"
    received = "received"
    cancelled = "cancelled"


class SupplyEventType(str, enum.Enum):
    supplier_paid_cny = "supplier_paid_cny"
    cargo_received = "cargo_received"
    cargo_to_rf = "cargo_to_rf"
    passed_to_tk = "passed_to_tk"
    received_to_wh = "received_to_wh"


class CarrierType(str, enum.Enum):
    cargo = "cargo"
    tk = "tk"


class MarketplaceType(str, enum.Enum):
    wb = "wb"
    ozon = "ozon"


class MarketplaceShipmentStatus(str, enum.Enum):
    draft = "draft"
    in_delivery = "in_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class MarketplaceShipmentEventType(str, enum.Enum):
    sent_to_delivery = "sent_to_delivery"   # списать со склада
    delivered_to_mp = "delivered_to_mp"     # просто закрыть статус
    cancelled = "cancelled"                 # вернуть на склад (если успели списать)
