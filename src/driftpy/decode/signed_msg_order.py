from driftpy.types import (
    MarketType,
    OrderParams,
    OrderTriggerCondition,
    OrderType,
    PositionDirection,
    PostOnlyParams,
    SignedMsgOrderParamsMessage,
    SignedMsgTriggerOrderParams,
)


def _validate_option_tag(tag: int, field_name: str) -> int:
    """borsh Option tag must be 0 (None) or 1 (Some) — fail closed otherwise."""
    if tag not in (0, 1):
        raise ValueError(
            f"Invalid borsh Option tag {tag} for {field_name} (expected 0 or 1)"
        )
    return tag


def read_bool(byte: int) -> bool:
    return byte != 0


def read_uint8(buffer, offset):
    return buffer[offset]


def read_uint16_le(buffer, offset):
    return int.from_bytes(buffer[offset : offset + 2], byteorder="little")


def read_int32_le(buffer, offset, signed):
    return int.from_bytes(
        buffer[offset : offset + 4], byteorder="little", signed=signed
    )


def read_bigint64le(buffer, offset, signed):
    return int.from_bytes(
        buffer[offset : offset + 8], byteorder="little", signed=signed
    )


def decode_order_params(buffer: bytes) -> OrderParams:
    offset = 0

    def debug_read(size: int, field_name: str, signed: bool = False) -> bytes:
        nonlocal offset
        if offset + size > len(buffer):
            raise ValueError(
                f"Buffer overflow reading {field_name} at offset {offset}, need {size} bytes, buffer length {len(buffer)}"
            )
        value = buffer[offset : offset + size]
        offset += size
        return value

    order_type_num = int.from_bytes(debug_read(1, "order_type"), "little")
    order_type: OrderType
    if order_type_num == 0:
        order_type = OrderType.Market()
    elif order_type_num == 1:
        order_type = OrderType.Limit()
    elif order_type_num == 2:
        order_type = OrderType.TriggerMarket()
    elif order_type_num == 3:
        order_type = OrderType.TriggerLimit()
    elif order_type_num == 4:
        order_type = OrderType.Oracle()
    else:
        raise ValueError(f"Invalid order type: {order_type_num}")

    market_type_num = int.from_bytes(debug_read(1, "market_type"), "little")
    if market_type_num not in (0, 1):
        raise ValueError(f"Invalid market type: {market_type_num}")
    market_type: MarketType = (
        MarketType.Spot() if market_type_num == 0 else MarketType.Perp()
    )

    existing_position_direction_num = int.from_bytes(
        debug_read(1, "direction"), "little"
    )
    if existing_position_direction_num not in (0, 1):
        raise ValueError(
            f"Invalid position direction: {existing_position_direction_num}"
        )
    direction: PositionDirection = (
        PositionDirection.Long()
        if existing_position_direction_num == 0
        else PositionDirection.Short()
    )

    user_order_id = int.from_bytes(debug_read(1, "user_order_id"), "little")

    base_asset_amount = int.from_bytes(debug_read(8, "base_asset_amount"), "little")

    price = int.from_bytes(debug_read(8, "price"), "little")

    # marketIndex (u16)
    market_index = int.from_bytes(debug_read(2, "market_index"), "little")

    # reduceOnly (bool)
    reduce_only = int.from_bytes(debug_read(1, "reduce_only"), "little") == 1

    # PostOnlyParam (u8 enum)
    post_only_num = int.from_bytes(debug_read(1, "post_only"), "little")
    post_only: PostOnlyParams
    if post_only_num == 0:
        post_only = PostOnlyParams.NONE()
    elif post_only_num == 1:
        post_only = PostOnlyParams.MustPostOnly()
    elif post_only_num == 2:
        post_only = PostOnlyParams.TryPostOnly()
    elif post_only_num == 3:
        post_only = PostOnlyParams.Slide()
    else:
        raise ValueError(f"Invalid post-only param: {post_only_num}")

    # bitFlags (u8) — bit 0 = immediateOrCancel
    bit_flags = int.from_bytes(debug_read(1, "bit_flags"), "little")
    immediate_or_cancel = (bit_flags & 0b0000_0001) != 0

    # maxTs (option<i64>)
    max_ts_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "max_ts_present"), "little"), "max_ts"
    )
    max_ts = None
    if max_ts_present == 1:
        max_ts = int.from_bytes(debug_read(8, "max_ts"), "little", signed=True)

    # triggerPrice (option<u64>)
    trigger_price_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "trigger_price_present"), "little"),
        "trigger_price",
    )
    trigger_price = None
    if trigger_price_present == 1:
        trigger_price = int.from_bytes(debug_read(8, "trigger_price"), "little")

    # OrderTriggerCondition (u8 enum)
    trigger_condition_num = int.from_bytes(debug_read(1, "trigger_condition"), "little")
    trigger_condition: OrderTriggerCondition
    if trigger_condition_num == 0:
        trigger_condition = OrderTriggerCondition.Above()
    elif trigger_condition_num == 1:
        trigger_condition = OrderTriggerCondition.Below()
    elif trigger_condition_num == 2:
        trigger_condition = OrderTriggerCondition.TriggeredAbove()
    elif trigger_condition_num == 3:
        trigger_condition = OrderTriggerCondition.TriggeredBelow()
    else:
        raise ValueError(f"Invalid trigger condition: {trigger_condition_num}")

    # offset (option<i32>)
    order_offset_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "offset_present"), "little"), "offset"
    )
    order_offset = None
    if order_offset_present == 1:
        order_offset = int.from_bytes(debug_read(4, "offset"), "little", signed=True)

    # offsetType (option<u8>) — 0=Oracle, 1=Queue
    offset_type_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "offset_type_present"), "little"),
        "offset_type",
    )
    order_offset_type = None
    if offset_type_present == 1:
        order_offset_type = int.from_bytes(debug_read(1, "offset_type"), "little")

    # auctionDuration (option<u8>)
    auction_duration_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "auction_duration_present"), "little"),
        "auction_duration",
    )
    auction_duration = None
    if auction_duration_present == 1:
        auction_duration = int.from_bytes(debug_read(1, "auction_duration"), "little")

    # auctionStartPrice (option<i64>)
    auction_start_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "auction_start_present"), "little"),
        "auction_start_price",
    )
    auction_start_price = None
    if auction_start_present == 1:
        auction_start_price = int.from_bytes(
            debug_read(8, "auction_start_price"), "little", signed=True
        )

    # auctionEndPrice (option<i64>)
    auction_end_present = _validate_option_tag(
        int.from_bytes(debug_read(1, "auction_end_present"), "little"),
        "auction_end_price",
    )
    auction_end_price = None
    if auction_end_present == 1:
        auction_end_price = int.from_bytes(
            debug_read(8, "auction_end_price"), "little", signed=True
        )

    return OrderParams(
        order_type=order_type,
        market_type=market_type,
        direction=direction,
        user_order_id=user_order_id,
        base_asset_amount=base_asset_amount,
        price=price,
        market_index=market_index,
        reduce_only=reduce_only,
        post_only=post_only,
        bit_flags=bit_flags,
        max_ts=max_ts,
        trigger_price=trigger_price,
        trigger_condition=trigger_condition,
        offset=order_offset,
        offset_type=order_offset_type,
        auction_duration=auction_duration,
        auction_start_price=auction_start_price,
        auction_end_price=auction_end_price,
    )


def decode_signed_msg_trigger_params(buffer: bytes) -> SignedMsgTriggerOrderParams:
    if len(buffer) < 16:
        raise ValueError(
            f"Buffer too short for trigger params: need 16 bytes, got {len(buffer)}"
        )

    trigger_price = int.from_bytes(buffer[0:8], "little")
    base_asset_amount = int.from_bytes(buffer[8:16], "little")

    return SignedMsgTriggerOrderParams(
        trigger_price=trigger_price, base_asset_amount=base_asset_amount
    )


def decode_signed_msg_order_params_message(
    buffer: bytes,
) -> SignedMsgOrderParamsMessage:
    signed_msg_order_params_buf = buffer[8:]
    offset = 0

    def read(size: int, field_name: str) -> bytes:
        nonlocal offset
        if offset + size > len(signed_msg_order_params_buf):
            raise ValueError(
                f"Buffer overflow reading {field_name} at offset {offset}, need {size} bytes, buffer length {len(signed_msg_order_params_buf)}"
            )
        value = signed_msg_order_params_buf[offset : offset + size]
        offset += size
        return value

    order_params, bytes_read = decode_order_params_with_size(
        signed_msg_order_params_buf
    )
    offset += bytes_read

    sub_account_id = int.from_bytes(read(2, "sub_account_id"), "little")

    slot = int.from_bytes(read(8, "slot"), "little")

    uuid = read(8, "uuid")

    take_profit_present = _validate_option_tag(
        int.from_bytes(read(1, "take_profit"), "little"), "take_profit"
    )
    take_profit = None
    if take_profit_present == 1:
        take_profit = decode_signed_msg_trigger_params(read(16, "take_profit"))

    stop_loss_present = _validate_option_tag(
        int.from_bytes(read(1, "stop_loss"), "little"), "stop_loss"
    )
    stop_loss = None
    if stop_loss_present == 1:
        stop_loss = decode_signed_msg_trigger_params(read(16, "stop_loss"))

    max_margin_ratio_present = _validate_option_tag(
        int.from_bytes(read(1, "max_margin_ratio"), "little"), "max_margin_ratio"
    )
    max_margin_ratio = None
    if max_margin_ratio_present == 1:
        max_margin_ratio = int.from_bytes(read(2, "max_margin_ratio"), "little")

    builder_idx_present = _validate_option_tag(
        int.from_bytes(read(1, "builder_idx"), "little"), "builder_idx"
    )
    builder_idx = None
    if builder_idx_present == 1:
        builder_idx = int.from_bytes(read(1, "builder_idx"), "little")

    builder_fee_tenth_bps_present = _validate_option_tag(
        int.from_bytes(read(1, "builder_fee_tenth_bps"), "little"),
        "builder_fee_tenth_bps",
    )
    builder_fee_tenth_bps = None
    if builder_fee_tenth_bps_present == 1:
        builder_fee_tenth_bps = int.from_bytes(
            read(2, "builder_fee_tenth_bps"), "little"
        )

    return SignedMsgOrderParamsMessage(
        signed_msg_order_params=order_params,
        sub_account_id=sub_account_id,
        slot=slot,
        uuid=uuid,
        take_profit_order_params=take_profit,
        stop_loss_order_params=stop_loss,
        max_margin_ratio=max_margin_ratio,
        builder_idx=builder_idx,
        builder_fee_tenth_bps=builder_fee_tenth_bps,
    )


def read_bytes(buffer, offset, size):
    if offset + size > len(buffer):
        raise ValueError(
            f"Buffer overflow at offset {offset}, need {size} bytes, buffer length {len(buffer)}"
        )
    value = buffer[offset : offset + size]
    return value, offset + size


def decode_order_params_with_size(buffer: bytes) -> tuple[OrderParams, int]:
    offset = 0

    def read(size: int, field_name: str) -> bytes:
        nonlocal offset
        if offset + size > len(buffer):
            raise ValueError(
                f"Buffer overflow reading {field_name} at offset {offset}, need {size} bytes, buffer length {len(buffer)}"
            )
        value = buffer[offset : offset + size]
        offset += size
        return value

    # Read order_type (u8)
    order_type_num = int.from_bytes(read(1, "field"), "little")

    if order_type_num == 0:
        order_type = OrderType.Market()
    elif order_type_num == 1:
        order_type = OrderType.Limit()
    elif order_type_num == 2:
        order_type = OrderType.TriggerMarket()
    elif order_type_num == 3:
        order_type = OrderType.TriggerLimit()
    elif order_type_num == 4:
        order_type = OrderType.Oracle()
    else:
        raise ValueError(f"Invalid order type: {order_type_num}")

    # Read market_type (u8)
    market_type_num = int.from_bytes(read(1, "field"), "little")
    if market_type_num not in (0, 1):
        raise ValueError(f"Invalid market type: {market_type_num}")
    market_type = (
        MarketType.Spot() if market_type_num == 0 else MarketType.Perp()
    )

    # Read direction (u8)
    direction_num = int.from_bytes(read(1, "field"), "little")
    if direction_num not in (0, 1):
        raise ValueError(f"Invalid position direction: {direction_num}")
    direction = (
        PositionDirection.Long() if direction_num == 0 else PositionDirection.Short()
    )

    # Read user_order_id (u8)
    user_order_id = int.from_bytes(read(1, "field"), "little")

    # Read base_asset_amount (u64)
    base_asset_amount = int.from_bytes(read(8, "field"), "little")

    # Read price (u64)
    price = int.from_bytes(read(8, "field"), "little")

    # Read market_index (u16)
    market_index = int.from_bytes(read(2, "field"), "little")

    # Read reduce_only (bool)
    reduce_only = int.from_bytes(read(1, "field"), "little") == 1

    # Read post_only (u8 enum)
    post_only_num = int.from_bytes(read(1, "field"), "little")

    if post_only_num == 0:
        post_only = PostOnlyParams.NONE()
    elif post_only_num == 1:
        post_only = PostOnlyParams.MustPostOnly()
    elif post_only_num == 2:
        post_only = PostOnlyParams.TryPostOnly()
    elif post_only_num == 3:
        post_only = PostOnlyParams.Slide()
    else:
        raise ValueError(f"Invalid post-only param: {post_only_num}")

    # bitFlags (u8) — bit 0 = immediateOrCancel
    bit_flags = int.from_bytes(read(1, "field"), "little")

    # Read max_ts (option<i64>)
    max_ts_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "max_ts"
    )

    max_ts = None
    if max_ts_present == 1:
        max_ts = int.from_bytes(read(8, "field"), "little", signed=True)

    # Read trigger_price (option<u64>)
    trigger_price_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "trigger_price"
    )

    trigger_price = None
    if trigger_price_present == 1:
        trigger_price = int.from_bytes(read(8, "field"), "little")

    # Read trigger_condition (u8 enum)
    trigger_condition_num = int.from_bytes(read(1, "field"), "little")

    if trigger_condition_num == 0:
        trigger_condition = OrderTriggerCondition.Above()
    elif trigger_condition_num == 1:
        trigger_condition = OrderTriggerCondition.Below()
    elif trigger_condition_num == 2:
        trigger_condition = OrderTriggerCondition.TriggeredAbove()
    elif trigger_condition_num == 3:
        trigger_condition = OrderTriggerCondition.TriggeredBelow()
    else:
        raise ValueError(f"Invalid trigger condition: {trigger_condition_num}")

    # Read offset (option<i32>)
    order_offset_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "offset"
    )

    order_offset = None
    if order_offset_present == 1:
        order_offset = int.from_bytes(read(4, "offset"), "little", signed=True)

    # Read offset_type (option<u8>) — 0=Oracle, 1=Queue
    offset_type_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "offset_type"
    )

    order_offset_type = None
    if offset_type_present == 1:
        order_offset_type = int.from_bytes(read(1, "field"), "little")

    # Read auction_duration (option<u8>)
    auction_duration_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "auction_duration"
    )

    auction_duration = None
    if auction_duration_present == 1:
        auction_duration = int.from_bytes(read(1, "field"), "little")

    # Read auction_start_price (option<i64>)
    auction_start_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "auction_start_price"
    )

    auction_start_price = None
    if auction_start_present == 1:
        auction_start_price = int.from_bytes(read(8, "auction_start_price"), "little", signed=True)

    # Read auction_end_price (option<i64>)
    auction_end_present = _validate_option_tag(
        int.from_bytes(read(1, "field"), "little"), "auction_end_price"
    )

    auction_end_price = None
    if auction_end_present == 1:
        auction_end_price = int.from_bytes(read(8, "auction_end_price"), "little", signed=True)

    return OrderParams(
        order_type=order_type,
        market_type=market_type,
        direction=direction,
        user_order_id=user_order_id,
        base_asset_amount=base_asset_amount,
        price=price,
        market_index=market_index,
        reduce_only=reduce_only,
        post_only=post_only,
        bit_flags=bit_flags,
        max_ts=max_ts,
        trigger_price=trigger_price,
        trigger_condition=trigger_condition,
        offset=order_offset,
        offset_type=order_offset_type,
        auction_duration=auction_duration,
        auction_start_price=auction_start_price,
        auction_end_price=auction_end_price,
    ), offset
