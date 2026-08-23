import base58
from anchorpy.coder.accounts import _account_discriminator
from solana.rpc.types import MemcmpOpts

from driftpy.name import encode_name
from driftpy.types import MarketType, is_variant


def get_user_filter() -> MemcmpOpts:
    return MemcmpOpts(0, base58.b58encode(_account_discriminator("User")).decode())


# Tail-field offsets mirror the packed User layout in protocol-v2
# programs/drift/src/state/user.rs — orders[32] end at 4008, then the
# post-orders tail: idle @4094, has_open_order @4096, has_open_auction
# @4098, margin_mode @4099, pool_id @4100. Keep in sync with
# sdk/src/memcmp.ts and drift-rs crates/src/memcmp.rs.


def get_non_idle_user_filter() -> MemcmpOpts:
    return MemcmpOpts(4094, base58.b58encode(bytes([0])).decode())


def get_user_with_auction_filter() -> MemcmpOpts:
    return MemcmpOpts(4098, base58.b58encode(bytes([1])).decode())


def get_user_with_order_filter() -> MemcmpOpts:
    return MemcmpOpts(4096, base58.b58encode(bytes([1])).decode())


def get_user_without_order_filter() -> MemcmpOpts:
    return MemcmpOpts(4096, base58.b58encode(bytes([0])).decode())


def get_user_that_has_been_lp_filter() -> MemcmpOpts:
    # last_add_perp_lp_shares_ts byte 3 (LE i64 @4008)
    return MemcmpOpts(4011, base58.b58encode(bytes([99])).decode())


def get_user_with_name_filter(name: str) -> MemcmpOpts:
    encoded_name_bytes = encode_name(name)
    return MemcmpOpts(72, base58.b58encode(bytes(encoded_name_bytes)).decode())


def get_users_with_pool_id_filter(pool_id: int) -> MemcmpOpts:
    return MemcmpOpts(4100, base58.b58encode(bytes([pool_id])).decode())


def get_market_type_filter(market_type: MarketType) -> MemcmpOpts:
    if is_variant(market_type, "Perp"):
        return MemcmpOpts(
            0, base58.b58encode(_account_discriminator("PerpMarket")).decode()
        )
    else:
        return MemcmpOpts(
            0, base58.b58encode(_account_discriminator("SpotMarket")).decode()
        )


def get_user_stats_filter() -> MemcmpOpts:
    return MemcmpOpts(0, base58.b58encode(_account_discriminator("UserStats")).decode())


def get_user_stats_is_referred_filter() -> MemcmpOpts:
    # offset 188, bytes for 2
    return MemcmpOpts(188, base58.b58encode(bytes([2])).decode())


def get_user_stats_is_referred_or_referrer_filter() -> MemcmpOpts:
    # offset 188, bytes for 3
    return MemcmpOpts(188, base58.b58encode(bytes([3])).decode())


def get_signed_msg_user_orders_filter() -> MemcmpOpts:
    return MemcmpOpts(
        0, base58.b58encode(_account_discriminator("SignedMsgUserOrders")).decode()
    )
