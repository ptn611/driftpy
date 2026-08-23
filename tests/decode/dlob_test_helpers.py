from solders.pubkey import Pubkey

from typing import Optional
from driftpy.dlob.dlob import DLOB

from driftpy.types import (
    MarketType,
    Order,
    OrderStatus,
    OrderTriggerCondition,
    OrderType,
    PositionDirection,
)


def insert_order_to_dlob(
    dlob: DLOB,
    user_account: Pubkey,
    order_type: OrderType,
    market_type: MarketType,
    order_id: int,
    market_index: int,
    price: int,
    base_asset_amount: int,
    direction: PositionDirection,
    auction_start_price: int,
    auction_end_price: int,
    slot: Optional[int] = None,
    max_ts=0,
    offset=0,
    offset_type=0,
    post_only=False,
    auction_duration=10,
):
    slot = slot if slot is not None else 1
    order = Order(
        slot=slot,
        price=price,
        base_asset_amount=base_asset_amount,
        base_asset_amount_filled=0,
        quote_asset_amount_filled=0,
        trigger_price=0,
        auction_start_price=auction_start_price,
        auction_end_price=auction_end_price,
        max_ts=max_ts,
        offset=offset,
        offset_type=offset_type,
        order_id=order_id,
        market_index=market_index,
        status=OrderStatus.Open(),
        order_type=order_type,
        market_type=market_type,
        user_order_id=0,
        existing_position_direction=PositionDirection.Long(),
        direction=direction,
        reduce_only=False,
        post_only=post_only,
        immediate_or_cancel=False,
        trigger_condition=OrderTriggerCondition.Above(),
        auction_duration=auction_duration,
        posted_slot_tail=0,
        bit_flags=0,
        padding=[0],
    )
    dlob.insert_order(order, user_account, slot)


def insert_trigger_order_to_dlob(
    dlob: DLOB,
    user_account: Pubkey,
    order_type: OrderType,
    market_type: MarketType,
    order_id: int,
    market_index: int,
    price: int,
    base_asset_amount: int,
    direction: PositionDirection,
    trigger_price: int,
    trigger_condition: OrderTriggerCondition,
    auction_start_price: int,
    auction_end_price: int,
    slot: Optional[int] = None,
    max_ts=0,
    offset=0,
    offset_type=0,
):
    slot = slot or 1
    order = Order(
        slot=slot,
        price=price,
        base_asset_amount=base_asset_amount,
        base_asset_amount_filled=0,
        quote_asset_amount_filled=0,
        trigger_price=trigger_price,
        auction_start_price=auction_start_price,
        auction_end_price=auction_end_price,
        max_ts=max_ts,
        offset=offset,
        offset_type=offset_type,
        order_id=order_id,
        market_index=market_index,
        status=OrderStatus.Open(),
        order_type=order_type,
        market_type=market_type,
        user_order_id=0,
        existing_position_direction=PositionDirection.Long(),
        direction=direction,
        reduce_only=False,
        post_only=False,
        immediate_or_cancel=True,
        trigger_condition=trigger_condition,
        auction_duration=0,
        posted_slot_tail=0,
        bit_flags=0,
        padding=[0],
    )
    dlob.insert_order(order, user_account, slot)
