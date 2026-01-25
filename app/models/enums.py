import enum


class SupplyStatus(str, enum.Enum):
    draft = "draft"
    assembled = "assembled"
    in_transit = "in_transit"
    received = "received"
    cancelled = "cancelled"
class SupplyEventType(str, enum.Enum):
    cargo_received = "cargo_received"
    cargo_to_rf = "cargo_to_rf"
    passed_to_tk = "passed_to_tk"
    received_to_wh = "received_to_wh"
