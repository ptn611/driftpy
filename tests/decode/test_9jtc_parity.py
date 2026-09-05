"""3d M144-1 — 9Jtc.hex real-fixture cross-SDK mirror (driftpy side)."""
from pathlib import Path

from driftpy.decode.user import decode_user

HEX = Path(__file__).resolve().parents[3] / "drift-rs" / "res" / "9Jtc.hex"


def test_9jtc_hex_decode_user_tail_fields():
    buf = bytes.fromhex(HEX.read_text().strip())
    assert len(buf) == 4104
    # pre-check tail layout mới có mặt (pool_id@4098 v.v. đọc được, không lệch offset)
    u = decode_user(buf)
    # giá trị tail thực của fixture này: account cũ, chưa đụng lp/pool
    assert u.pool_id == 0
    assert int(u.has_open_order) in (0, 1)
    assert u.last_add_perp_lp_shares_ts >= 0
    # field phân biệt đọc không panic + determinism: decode lần 2 same result
    u2 = decode_user(buf)
    assert str(u) == str(u2)
