"""Import every model so `Base.metadata` is complete (used by Alembic and tests)."""

from app.core.db import Base
from app.modules.auth.models import User
from app.modules.catalog.models import (
    CalendarDay,
    Depot,
    District,
    Outlet,
    OutletProfile,
    Product,
    ServiceAllowance,
    TravelRatio,
    UsualQuantity,
    Vehicle,
)
from app.modules.fleet.models import FuelLedger, VehicleDay
from app.modules.loading.models import Hold, RepairOption, Shortfall
from app.modules.ops.models import ClockSetting, ExceptionItem, Notification
from app.modules.orders.models import DriverNote, Order, OrderLine
from app.modules.planning.models import Deferral, Plan, PlanAck, PlanVersion, Stop, StopOrder, Trip
from app.modules.receipts.models import Issue, IssueLine, Receipt, ReceiptLine
from app.modules.sync.models import Event

__all__ = [
    "Base",
    "CalendarDay",
    "ClockSetting",
    "Deferral",
    "Depot",
    "District",
    "DriverNote",
    "Event",
    "ExceptionItem",
    "FuelLedger",
    "Hold",
    "Issue",
    "IssueLine",
    "Notification",
    "Order",
    "OrderLine",
    "Outlet",
    "OutletProfile",
    "Plan",
    "PlanAck",
    "PlanVersion",
    "Product",
    "Receipt",
    "ReceiptLine",
    "RepairOption",
    "ServiceAllowance",
    "Shortfall",
    "Stop",
    "StopOrder",
    "TravelRatio",
    "Trip",
    "User",
    "UsualQuantity",
    "Vehicle",
    "VehicleDay",
]
