"""Packed Order.flags decode — mirrors TS SDK decode/order.ts and Rust crates/src/decode/order.rs.

Keep in sync with programs/drift/src/state/user.rs flags module.
"""
from driftpy.types import (
    MarketType,
    OrderStatus,
    OrderTriggerCondition,
    OrderType,
    PositionDirection,
    TriggerPriceType,
)

# Mirrors TS ORDER_FLAGS_LAYOUT
ORDER_FLAGS_LAYOUT = {
    "STATUS": {"byte": 0, "shift": 0, "mask": 0b0000_0011},
    "ORDER_TYPE": {"byte": 0, "shift": 2, "mask": 0b0001_1100},
    "MARKET_TYPE": {"byte": 0, "shift": 5, "mask": 0b0010_0000},
    "DIRECTION": {"byte": 0, "shift": 6, "mask": 0b0100_0000},
    "EXISTING_POSITION_DIRECTION": {"byte": 0, "shift": 7, "mask": 0b1000_0000},
    "REDUCE_ONLY": {"byte": 1, "shift": 0, "mask": 0b0000_0001},
    "POST_ONLY": {"byte": 1, "shift": 1, "mask": 0b0000_0010},
    "IMMEDIATE_OR_CANCEL": {"byte": 1, "shift": 2, "mask": 0b0000_0100},
    "OFFSET_TYPE": {"byte": 1, "shift": 3, "mask": 0b0000_1000},
    "TRIGGER_CONDITION": {"byte": 1, "shift": 4, "mask": 0b0011_0000},
    "TRIGGER_PRICE_TYPE": {"byte": 1, "shift": 6, "mask": 0b0100_0000},
    "BIT_FLAGS_BYTE": 2,
}

ORDER_SIZE_BYTES = 88
ORDER_FLAGS_COUNT = 3


def _get_bits(flags, layout):
    return (flags[layout["byte"]] & layout["mask"]) >> layout["shift"]


ORDER_STATUS_VARIANTS = [
    OrderStatus.Init(),
    OrderStatus.Open(),
    OrderStatus.Filled(),
    OrderStatus.Canceled(),
]

ORDER_TYPE_VARIANTS = [
    OrderType.Market(),
    OrderType.Limit(),
    OrderType.TriggerMarket(),
    OrderType.TriggerLimit(),
    OrderType.Oracle(),
]

ORDER_TRIGGER_CONDITION_VARIANTS = [
    OrderTriggerCondition.Above(),
    OrderTriggerCondition.Below(),
    OrderTriggerCondition.TriggeredAbove(),
    OrderTriggerCondition.TriggeredBelow(),
]


def unpack_order_flags(flags):
    """Fail-closed: returns None if status/order_type discriminant invalid."""
    status_raw = _get_bits(flags, ORDER_FLAGS_LAYOUT["STATUS"])
    order_type_raw = _get_bits(flags, ORDER_FLAGS_LAYOUT["ORDER_TYPE"])
    if status_raw >= len(ORDER_STATUS_VARIANTS) or order_type_raw >= len(
        ORDER_TYPE_VARIANTS
    ):
        return None

    direction_raw = _get_bits(flags, ORDER_FLAGS_LAYOUT["DIRECTION"])

    return {
        "status": ORDER_STATUS_VARIANTS[status_raw],
        "order_type": ORDER_TYPE_VARIANTS[order_type_raw],
        "market_type": MarketType.Spot()
        if _get_bits(flags, ORDER_FLAGS_LAYOUT["MARKET_TYPE"]) == 0
        else MarketType.Perp(),
        "direction": PositionDirection.Long()
        if direction_raw == 0
        else PositionDirection.Short(),
        "existing_position_direction": PositionDirection.Long()
        if _get_bits(flags, ORDER_FLAGS_LAYOUT["EXISTING_POSITION_DIRECTION"]) == 0
        else PositionDirection.Short(),
        "reduce_only": _get_bits(flags, ORDER_FLAGS_LAYOUT["REDUCE_ONLY"]) != 0,
        "post_only": _get_bits(flags, ORDER_FLAGS_LAYOUT["POST_ONLY"]) != 0,
        "immediate_or_cancel": _get_bits(
            flags, ORDER_FLAGS_LAYOUT["IMMEDIATE_OR_CANCEL"]
        )
        != 0,
        "trigger_condition": ORDER_TRIGGER_CONDITION_VARIANTS[
            _get_bits(flags, ORDER_FLAGS_LAYOUT["TRIGGER_CONDITION"])
        ],
        # offset_type: 0=Oracle, 1=Queue — keep as int for now (driftpy has no OffsetType)
        "offset_type": _get_bits(flags, ORDER_FLAGS_LAYOUT["OFFSET_TYPE"]),
        # trigger_price_type: Oracle=0, Last=1 (IntEnum == int, fail-closed:
        # the 1-bit mask only ever yields 0/1)
        "trigger_price_type": TriggerPriceType(
            _get_bits(flags, ORDER_FLAGS_LAYOUT["TRIGGER_PRICE_TYPE"])
        ),
        "bit_flags": flags[ORDER_FLAGS_LAYOUT["BIT_FLAGS_BYTE"]],
    }
