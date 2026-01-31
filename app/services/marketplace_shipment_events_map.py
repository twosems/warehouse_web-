from __future__ import annotations

from app.models.enums import MarketplaceShipmentEventType, MarketplaceShipmentStatus

EVENT_TYPE_TO_STATUS: dict[MarketplaceShipmentEventType, MarketplaceShipmentStatus] = {
    MarketplaceShipmentEventType.sent_to_delivery: MarketplaceShipmentStatus.in_delivery,
    MarketplaceShipmentEventType.delivered_to_mp: MarketplaceShipmentStatus.delivered,
    MarketplaceShipmentEventType.cancelled: MarketplaceShipmentStatus.cancelled,
}
