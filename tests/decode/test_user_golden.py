"""3d — decode_user offline trên user_account vectors + negative stored-flags."""
import json
from pathlib import Path

import pytest

from driftpy.decode.user import decode_user

FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_vectors.json"
)


def golden() -> dict:
    return json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("idx", range(2))
def test_decode_user_offline_matches_fixture(idx):
    accounts = golden()["user_account"]
    v = accounts[idx]
    buf = bytes.fromhex(v["hex"])
    assert len(buf) == 4104
    u = decode_user(buf)
    assert u.pool_id == v["pool_id"]
    assert type(u.margin_mode).__name__.rsplit(".", 1)[-1] == {
        0: "Default", 1: "HighLeverage", 2: "HighLeverageMaintenance",
    }[v["margin_mode"]]
    assert bool(u.idle) == (v["idle"] == 1)
    assert bool(u.has_open_order) == (v["has_open_order"] == 1)
    assert u.last_add_perp_lp_shares_ts == v["lp_ts"]
    off = v.get("reserved_bits_flags_offset")
    if off is not None:
        assert (buf[off] & 0xC0) == 0xC0


def test_negative_stored_flags_order_type_invalid():
    v = next(
        x
        for x in golden()["user_account"]
        if x.get("scenario") == "open_order_reserved_margin2"
    )
    buf = bytearray(bytes.fromhex(v["hex"]))
    f0 = 8 + 1184 + 85  # orders[0].flags[0] — offset_of(User,orders)=1184 (pin drift-rs)
    buf[f0] = (buf[f0] & ~0b0001_1100) | (5 << 2)
    u = decode_user(bytes(buf))
    # grep-source-first đã chốt (decode/user.py:158-161): unpack None -> SKIP order,
    # KHÔNG panic; orders list rỗng
    assert u.orders == []


def test_negative_stored_flags_margin_mode_reserved():
    v = golden()["user_account"][0]
    buf = bytearray(bytes.fromhex(v["hex"]))
    flags_off = 8 + 4091  # User.flags[0] — offset_of(User,flags)=4091 (PACKING_PLAN §3.1)
    # set margin_mode bits (bits1-2) to 0b11 = discriminant 3 → on-chain
    # MarginMode::try_from returns Err → off-chain decode must raise, not
    # silently fall back to Default.
    buf[flags_off] = (buf[flags_off] & ~0b0000_0110) | (3 << 1)
    with pytest.raises(ValueError, match="margin_mode discriminant"):
        decode_user(bytes(buf))


def test_negative_short_buffer_fail_closed():
    good = bytes.fromhex(golden()["user_account"][0]["hex"])
    for cut in (100, 4000, 4103):
        with pytest.raises(Exception):
            decode_user(good[:cut])
