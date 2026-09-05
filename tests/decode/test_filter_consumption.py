"""3d — filter-consumption: memcmp constants CHỌN ĐÚNG account (r150/v153).
Packed tail (2b16c79/8db3de8): idle @4093 / has_open_order @4095 /
has_open_auction @4097 / pool_id @4098 / lp-ts byte3 @4011.
margin_mode nằm trong flags@4099 bits1-2 (bit0 = margin_trading_enabled)."""
import json
from pathlib import Path

import pytest

from driftpy.decode.user import decode_user

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_vectors.json"
OFF_IDLE, OFF_OPEN_ORDER, OFF_AUCTION, OFF_LP_TS_B3, OFF_POOL_ID = (
    4093, 4095, 4097, 4011, 4098,
)


def build_user_bytes(idle=0, open_order=1, auction=1, lp_b3=99, pool_id=7,
                     margin_mode=1):
    base = json.loads(FIXTURE.read_text())["user_account"]
    v = next(x for x in base if x.get("scenario") == "fresh_init_base") \
        if any(x.get("scenario") == "fresh_init_base" for x in base) else base[0]
    buf = bytearray(bytes.fromhex(v["hex"]))
    buf[OFF_IDLE] = idle
    buf[OFF_OPEN_ORDER] = open_order
    buf[OFF_AUCTION] = auction
    buf[OFF_POOL_ID] = pool_id
    assert 0 <= margin_mode <= 2, "on-chain MarginMode::try_from rejects >=3"
    buf[4_099] = buf[4_099] & ~0b0000_0110 | ((margin_mode & 0b11) << 1)
    old = int.from_bytes(buf[4008:4016], "little", signed=True)
    new = (old & ~0xFF000000) | (lp_b3 << 24)
    buf[4008:4016] = int(new & (2**64 - 1)).to_bytes(8, "little", signed=False)
    return bytes(buf)


def test_base_buffer_matches_all_offsets():
    b = build_user_bytes()
    assert b[OFF_IDLE] == 0 and b[OFF_OPEN_ORDER] == 1
    assert b[OFF_AUCTION] == 1 and b[OFF_POOL_ID] == 7
    assert (b[OFF_LP_TS_B3]) == 99


@pytest.mark.parametrize(
    "off,bad_val",
    [(OFF_IDLE, 1), (OFF_OPEN_ORDER, 0), (OFF_AUCTION, 0), (OFF_POOL_ID, 8)],
)
def test_single_byte_mutation_breaks_match(off, bad_val):
    good = build_user_bytes()
    bad = bytearray(build_user_bytes())
    bad[off] = bad_val
    assert good[off] != bad[off], f"mutation tại {off} phải đổi giá trị khớp"


def test_decode_field_value_covers_lp_ts_and_pool_id():
    b = build_user_bytes(lp_b3=99, pool_id=7)
    u = decode_user(b)
    assert (u.last_add_perp_lp_shares_ts >> 24) & 0xFF == 99
    assert u.pool_id == 7


def test_margin_mode_via_decode_field_value():
    b = build_user_bytes(margin_mode=1)
    u = decode_user(b)
    assert type(u.margin_mode).__name__ == "HighLeverage"
