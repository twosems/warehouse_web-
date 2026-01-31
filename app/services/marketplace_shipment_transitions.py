from app.models.enums import MarketplaceShipmentStatus

ALLOWED_MP_SHIPMENT_TRANSITIONS: dict[MarketplaceShipmentStatus, set[MarketplaceShipmentStatus]] = {
    MarketplaceShipmentStatus.draft: {
        MarketplaceShipmentStatus.in_delivery,
        MarketplaceShipmentStatus.cancelled,
    },
    MarketplaceShipmentStatus.in_delivery: {
        MarketplaceShipmentStatus.delivered,
        MarketplaceShipmentStatus.cancelled,
    },
    MarketplaceShipmentStatus.delivered: set(),
    MarketplaceShipmentStatus.cancelled: set(),
}


def validate_mp_shipment_transition(current: MarketplaceShipmentStatus, target: MarketplaceShipmentStatus) -> None:
    allowed = ALLOWED_MP_SHIPMENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid marketplace shipment status transition: {current} → {target}")
