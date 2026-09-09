#!/usr/bin/env python3
"""Golden vectors generator — Migration packed Order.flags.

SINGLE SOURCE OF TRUTH cho tên field per-vector (r82). TS fallback mirror y hệt.
Encoding rules (pin r93-r120):
  - bytes -> hex lowercase, không prefix 0x
  - enums -> discriminant số
  - Option -> null | giá trị trực tiếp (không wrapper)
Quy ước an toàn:
  - Chỉ các sections generator sở hữu (signed_msg, order_flags_python,
    auction_vectors, router_vectors) được regen; các sections ngoại lai
    (order_flags_contract, user_account, user_tail — từ contract-side) được GIỮ
    NGUYÊN từ file hiện có. Chạy lại là idempotent: `git diff` phải trống.
  - Serialize với sort_keys=True để khớp byte với file đã commit.
"""
import json
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent / "golden_vectors.json"

STD_PREFIX = b"smsgv002"
DEL_PREFIX = b"dsmsv002"

# ---------------- helpers ----------------

def h(b: bytes) -> str:
    return b.hex()

def opt_bytes(v, size, signed=False):
    """Option<T> wire: tag byte + LE payload."""
    if v is None:
        return b"\x00"
    return b"\x01" + int(v).to_bytes(size, "little", signed=signed)

def enum_b(v):
    return int(v).to_bytes(1, "little")

def bool_b(v):
    return b"\x01" if v else b"\x00"

# OrderParams wire layout (driftpy decode_order_params_with_size mirror)
def pack_order_params(p):
    out = b""
    out += enum_b(p["order_type"])            # 0..4
    out += enum_b(p["market_type"])           # 0 Spot, 1 Perp
    out += enum_b(p["direction"])             # 0 Long, 1 Short
    out += enum_b(p.get("user_order_id", 0))
    out += struct.pack("<Q", p["base_asset_amount"])
    out += struct.pack("<Q", p.get("price", 0))
    out += struct.pack("<H", p["market_index"])
    out += bool_b(p.get("reduce_only", False))
    out += enum_b(p.get("post_only", 0))      # 0 None,1 MustPostOnly,2 TryPostOnly,3 Slide
    out += enum_b(p.get("bit_flags", 0))      # wire bit_flags 1-byte
    out += opt_bytes(p.get("max_ts"), 8, signed=True)
    out += opt_bytes(p.get("trigger_price"), 8)
    out += enum_b(p.get("trigger_condition", 0))
    out += opt_bytes(p.get("offset"), 4, signed=True)
    out += opt_bytes(p.get("offset_type"), 1)
    out += opt_bytes(p.get("auction_duration"), 1)
    out += opt_bytes(p.get("auction_start_price"), 8, signed=True)
    out += opt_bytes(p.get("auction_end_price"), 8, signed=True)
    out += opt_bytes(p.get("trigger_price_type"), 1)
    return out

def pack_std_tail(p):
    out = struct.pack("<H", p.get("sub_account_id", 0))
    out += struct.pack("<Q", p.get("slot", 100))
    out += p.get("uuid", b"\x01" * 8)
    tp = p.get("take_profit")
    if tp is None:
        out += b"\x00"
    else:
        out += b"\x01" + struct.pack("<QQ", tp["trigger_price"], tp["base_asset_amount"])
    sl = p.get("stop_loss")
    if sl is None:
        out += b"\x00"
    else:
        out += b"\x01" + struct.pack("<QQ", sl["trigger_price"], sl["base_asset_amount"])
    out += opt_bytes(p.get("max_margin_ratio"), 2)
    out += opt_bytes(p.get("builder_idx"), 1)
    out += opt_bytes(p.get("builder_fee_tenth_bps"), 2)
    out += opt_bytes(p.get("isolated_position_deposit"), 8)
    return out

def std_vector(name, params, expect_note=None):
    payload = pack_order_params(params) + pack_std_tail(params)
    vec = {
        "name": name,
        "wire_hex_prefixed": h(STD_PREFIX + payload),
        "payload_hex": h(payload),
        "order_type": params["order_type"],
        "market_type": params["market_type"],
        "direction": params["direction"],
        "bit_flags": params.get("bit_flags", 0),
        "reduce_only": 1 if params.get("reduce_only") else 0,
        "post_only": params.get("post_only", 0),
        "offset": params.get("offset"),
        "offset_type": params.get("offset_type"),
        "isolated_position_deposit": params.get("isolated_position_deposit"),
        "has_builder": 1 if params.get("builder_idx") is not None else 0,
        "market_index": params["market_index"],
        "base_asset_amount": params["base_asset_amount"],
        "price": params.get("price", 0),
        "user_order_id": params.get("user_order_id", 0),
        "sub_account_id": params.get("sub_account_id", 0),
        "slot": params.get("slot", 100),
    }
    if expect_note:
        vec["expect_note"] = expect_note
    return vec

def pack_del_tail(p):
    # Delegate message KHÔNG có sub_account_id (khác standard) — drift_idl.rs:3317
    out = struct.pack("<Q", p.get("slot", 100))
    out += p.get("uuid", b"\xAB" * 8)
    tp = p.get("take_profit")
    if tp is None:
        out += b"\x00"
    else:
        out += b"\x01" + struct.pack("<QQ", tp["trigger_price"], tp["base_asset_amount"])
    sl = p.get("stop_loss")
    if sl is None:
        out += b"\x00"
    else:
        out += b"\x01" + struct.pack("<QQ", sl["trigger_price"], sl["base_asset_amount"])
    out += opt_bytes(p.get("max_margin_ratio"), 2)
    out += opt_bytes(p.get("builder_idx"), 1)
    out += opt_bytes(p.get("builder_fee_tenth_bps"), 2)
    out += opt_bytes(p.get("isolated_position_deposit"), 8)
    return out

def delegate_vector(name, params, taker_pubkey_hex):
    payload = pack_order_params(params) + bytes.fromhex(taker_pubkey_hex) + pack_del_tail(params)
    return {
        "name": name,
        "wire_hex_prefixed": h(DEL_PREFIX + payload),
        "payload_hex": h(payload),
        "taker_pubkey": taker_pubkey_hex,
        "order_type": params["order_type"],
        "bit_flags": params.get("bit_flags", 0),
        "offset": params.get("offset"),
        "offset_type": params.get("offset_type"),
        "isolated_position_deposit": params.get("isolated_position_deposit"),
    }

# base params: Limit Perp Long, offset Some(1000)+Oracle, isolated Some
def base_params(**kw):
    p = dict(
        order_type=1, market_type=1, direction=0, user_order_id=1,
        base_asset_amount=10**18, price=50_000_000_000,
        market_index=0, reduce_only=False, post_only=0, bit_flags=0,
        max_ts=None, trigger_price=None, trigger_condition=0,
        offset=1000, offset_type=0, auction_duration=None,
        auction_start_price=None, auction_end_price=None,
        sub_account_id=0, slot=12345, uuid=b"\xAB" * 8,
        take_profit=None, stop_loss=None,
        max_margin_ratio=None, builder_idx=None, builder_fee_tenth_bps=None,
        isolated_position_deposit=None,
    )
    p.update(kw)
    return p

# ---------------- signed_msg.standard ----------------
standard = []
# 1. baseline: tất cả bit clear
standard.append(std_vector("std_base_all_clear", base_params()))
# 2-5. per-bit standalone set: 0x01 ioc, 0x02 oracle-trigger-market, 0x04 safe-trigger, 0x08 new-trigger-reduce-only
for bit, nm in [(0x01, "ioc"), (0x02, "oracle_trigger_market"), (0x04, "safe_trigger_order"), (0x08, "new_trigger_reduce_only")]:
    standard.append(std_vector(f"std_bit_{nm}", base_params(bit_flags=bit)))
# 6-7. has_builder set (+fee) và clear
standard.append(std_vector("std_has_builder_set",
    base_params(bit_flags=0x10, builder_idx=0, builder_fee_tenth_bps=10)))
# clear đã có ở base (has_builder=0) — thêm bản tường minh
standard.append(std_vector("std_has_builder_clear", base_params()))
# 8. isolated set (deposit Some)
standard.append(std_vector("std_isolated_set", base_params(isolated_position_deposit=5 * 10**17)))
# 9. cross-invariant lớp (b2): 0x20 CLEAR + deposit=Some -> decode trung thực cả hai phía
standard.append(std_vector("std_isolated_clear_deposit_some",
    base_params(bit_flags=0x00, isolated_position_deposit=7 * 10**16)))
# 10. combo thực dụng: ioc + offset Queue
standard.append(std_vector("std_ioc_queue_offset",
    base_params(bit_flags=0x01, offset=-500, offset_type=1)))
# 11. market order full tail (tp+sl+mmr)
standard.append(std_vector("std_market_full_tail", base_params(
    order_type=0, price=0, bit_flags=0,
    take_profit={"trigger_price": 60_000_000_000, "base_asset_amount": 10**18},
    stop_loss={"trigger_price": 40_000_000_000, "base_asset_amount": 10**18},
    max_margin_ratio=1000)))

# ---------------- signed_msg.delegate ----------------
delegate = [
    delegate_vector("del_base_oracle_offset", base_params(),
        "11" * 32),
    delegate_vector("del_isolated_set_ioc", base_params(bit_flags=0x01, isolated_position_deposit=10**18),
        "22" * 32),
]

# ---------------- signed_msg.trigger (payload thuần 16B) ----------------
trigger = [
    {"name": "trg_basic", "payload_hex": h(struct.pack("<QQ", 55_000_000_000, 10**18)),
     "trigger_price": 55_000_000_000, "base_asset_amount": 10**18},
    {"name": "trg_zero_price", "payload_hex": h(struct.pack("<QQ", 0, 1)),
     "trigger_price": 0, "base_asset_amount": 1},
]

# ---------------- signed_msg.abnormal ----------------
abnormal = []
def raw_abn(name, payload, reason, expect="raise"):
    abnormal.append({"name": name, "payload_hex": h(payload), "reason": reason, "expect": expect})

good_payload = pack_order_params(base_params()) + pack_std_tail(base_params())
# (a) fail-closed: truncate
raw_abn("abn_truncated_header", good_payload[:10], "buffer < header")
raw_abn("abn_truncated_tail", good_payload[:-3], "thiếu 3 byte tail")
raw_abn("abn_empty", b"", "empty buffer")
# option tag=2 invalid
p = bytearray(good_payload)
op_len = len(pack_order_params(base_params()))
# max_ts tag nằm trong OrderParams — tìm vị trí: sau post_only+bit_flags (offset tĩnh theo layout)
# tính tay: 1+1+1+1+8+8+2+1+1+1 = 25 -> tag max_ts @25
p[25] = 2
raw_abn("abn_option_tag_2_max_ts", bytes(p), "option tag=2")
# reduce_only=2 (bool vượt range) @offset 22 (verify thực nghiệm)
p2 = bytearray(good_payload)
p2[22] = 2
raw_abn("abn_reduce_only_2", bytes(p2), "bool reduce_only=2")
# order_type=5 @0
p3 = bytearray(good_payload)
p3[0] = 5
raw_abn("abn_order_type_5", bytes(p3), "enum order_type vượt range")
# post_only=4 @23 (verify thực nghiệm)
p4 = bytearray(good_payload)
p4[23] = 4
raw_abn("abn_post_only_4", bytes(p4), "enum post_only vượt range")
# trigger_condition=4 @ (25+1+8+1)=35 khi max_ts=None: tag(1)+... layout: 26 tag trigger_price,27 tag trigger_condition? tính động bên dưới qua pack variant
pc = pack_order_params(base_params())
pc += pack_std_tail(base_params())
# tìm trigger_condition: sau max_ts tag(1@25) trigger_price tag(1@26) rồi condition @27
p5 = bytearray(pc)
p5[27] = 4
raw_abn("abn_trigger_condition_4", bytes(p5), "enum trigger_condition vượt range")
# (b) cross-invariant decode-được: 0x20 SET + deposit=None ; 0x20 CLEAR + deposit=Some
abnormal.append({
    "name": "abn_crossinv_isolated_set_deposit_none",
    "payload_hex": h(pack_order_params(base_params(bit_flags=0x20)) + pack_std_tail(base_params(bit_flags=0x20))),
    "reason": "0x20 SET + isolated_position_deposit=null",
    "expect": "decode_ok_faithful",
    "expect_bit_0x20": 1, "expect_isolated_position_deposit": None,
})
abnormal.append({
    "name": "abn_crossinv_isolated_clear_deposit_some",
    "payload_hex": h(pack_order_params(base_params(isolated_position_deposit=9 * 10**17)) + pack_std_tail(base_params(isolated_position_deposit=9 * 10**17))),
    "reason": "0x20 CLEAR + isolated_position_deposit=Some(v)",
    "expect": "decode_ok_faithful",
    "expect_bit_0x20": 0, "expect_isolated_position_deposit": 9 * 10**17,
})

# ---------------- order_flags_python: FULL Order 88-byte thủ công ----------------
# layout (user.rs Order): slot8 price8 base8 base_filled8 quote_filled8 trigger_price8
#   auction_start8(i64) auction_end8(i64) max_ts8(i64) offset4(i32) order_id4(u16->u32)
#   market2 user_order_id1 auction_duration1 posted_slot_tail1 flags[3]  == 88
ORDER_SIZE = 88
FLAGS_OFFSET = 85

def pack_flags_byte0(status, order_type, market_type, direction, existing_dir):
    assert status in (0, 1, 2, 3) and order_type < 8 and market_type in (0, 1) and direction in (0, 1)
    b = status & 0b11
    b |= (order_type & 0b111) << 2
    b |= (market_type & 1) << 5
    b |= (direction & 1) << 6
    b |= (existing_dir & 1) << 7
    return b

def pack_flags_byte1(reduce_only, post_only_bool, ioc, offset_type_oracle, trigger_condition, reserved=0, trigger_price_type=0):
    # V-FIX cross-check r169: contract quy ước offset_type discriminant (Oracle=0, Queue=1)
    # -> bit SET tương ứng Queue, bit CLEAR là Oracle (contract là trọng tài)
    b = (1 if reduce_only else 0)
    b |= (1 if post_only_bool else 0) << 1
    b |= (1 if ioc else 0) << 2
    b |= (0 if offset_type_oracle else 1) << 3
    b |= (trigger_condition & 0b11) << 4
    b |= (trigger_price_type & 0b1) << 6  # TriggerPriceType: 0=Oracle, 1=Last
    b |= reserved & 0b1000_0000  # bit 7 reserved (b6 là trigger_price_type)
    return b

def pack_order(o):
    f0 = pack_flags_byte0(o.get("status", 1), o["order_type"], o["market_type"], o["direction"], o.get("existing_position_direction", 0))
    f1 = pack_flags_byte1(o.get("reduce_only", False), o.get("post_only", False), o.get("ioc", False),
                           o.get("offset_type_oracle", False), o.get("trigger_condition", 0), o.get("flags1_reserved", 0),
                           o.get("trigger_price_type", 0))
    f2 = o.get("legacy_bit_flags", 0)
    buf = b""
    buf += struct.pack("<Q", o["slot"])
    buf += struct.pack("<Q", o["price"])
    buf += struct.pack("<Q", o["base_asset_amount"])
    buf += struct.pack("<Q", o.get("base_asset_amount_filled", 0))
    buf += struct.pack("<Q", o.get("quote_asset_amount_filled", 0))
    buf += struct.pack("<Q", o.get("trigger_price", 0))
    buf += struct.pack("<q", o.get("auction_start_price", 0))
    buf += struct.pack("<q", o.get("auction_end_price", 0))
    buf += struct.pack("<q", o.get("max_ts", 0))
    buf += struct.pack("<i", o["offset"])
    buf += struct.pack("<I", o["order_id"])
    buf += struct.pack("<H", o["market_index"])
    buf += bytes([o.get("user_order_id", 1)])
    buf += bytes([o.get("auction_duration", 0)])
    buf += bytes([o.get("posted_slot_tail", 0)])
    buf += bytes([f0, f1, f2])
    assert len(buf) == ORDER_SIZE, len(buf)
    return buf

def of_vec(name, o, **ctx):
    buf = pack_order(o)
    v = {"name": name, "hex": h(buf), "flags": [buf[85], buf[86], buf[87]], **o}
    for k, val in ctx.items():
        v[k] = val
    return v

order_flags_python = []
_seq = iter(range(1, 99))
def oid():
    return next(_seq)

# 1. base limit perp long
order_flags_python.append(of_vec("of_base_limit_perp_long", dict(
    slot=1000, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0,
    offset_type_oracle=True)))
# 2. market perp short ioc
order_flags_python.append(of_vec("of_market_short_ioc", dict(
    slot=1001, price=0, base_asset_amount=5 * 10**17, offset=0, order_id=oid(),
    market_index=0, order_type=0, market_type=1, direction=1, ioc=True)))
# 3. limit spot reduce_only post_only
order_flags_python.append(of_vec("of_spot_reduce_postonly", dict(
    slot=1002, price=100_000_000, base_asset_amount=10**6, offset=0, order_id=oid(),
    market_index=1, order_type=1, market_type=0, direction=1, reduce_only=True, post_only=True)))
# 4. trigger market above
order_flags_python.append(of_vec("of_trigger_market_above", dict(
    slot=1003, price=0, base_asset_amount=10**18, trigger_price=60_000_000_000, offset=0,
    order_id=oid(), market_index=0, order_type=2, market_type=1, direction=0, trigger_condition=0)))
# 5. trigger limit below
order_flags_python.append(of_vec("of_trigger_limit_below", dict(
    slot=1004, price=40_000_000_000, base_asset_amount=10**18, trigger_price=40_000_000_000,
    offset=0, order_id=oid(), market_index=0, order_type=3, market_type=1, direction=1, trigger_condition=1)))
# 6. oracle order với auction
order_flags_python.append(of_vec("of_oracle_auction", dict(
    slot=1005, price=0, base_asset_amount=10**18, auction_start_price=49_000_000_000,
    auction_end_price=51_000_000_000, offset=0, order_id=oid(), market_index=0,
    order_type=4, market_type=1, direction=0, auction_duration=50)))
# 7. has_builder set (legacy bit 0x10)
order_flags_python.append(of_vec("of_has_builder_set", dict(
    slot=1006, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x10), expect_legacy_has_builder=1))
# 8. has_builder clear tường minh
order_flags_python.append(of_vec("of_has_builder_clear", dict(
    slot=1007, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x00), expect_legacy_has_builder=0))
# 9. isolated set (legacy bit 0x20)
order_flags_python.append(of_vec("of_isolated_set", dict(
    slot=1008, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x20), expect_legacy_is_isolated=1))
# 10. isolated clear
order_flags_python.append(of_vec("of_isolated_clear", dict(
    slot=1009, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x00), expect_legacy_is_isolated=0))
# 11. offset=None≡0 + offset_type Oracle (router fixed-price biên)
order_flags_python.append(of_vec("of_offset_zero_oracle_fixed", dict(
    slot=1010, price=52_000_000_000, base_asset_amount=10**18, offset=0, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True)))
# 12. offset≠0 + offset_type Queue (vẫn oracle-offset branch theo has_oracle_price_offset)
order_flags_python.append(of_vec("of_offset_queue_nonzero", dict(
    slot=1011, price=50_000_000_000, base_asset_amount=10**18, offset=-250, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=1, offset_type_oracle=False)))
# 13. status variants + existing_direction
order_flags_python.append(of_vec("of_status_variants", dict(
    slot=1012, price=50_000_000_000, base_asset_amount=10**18, offset=0, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, status=3, existing_position_direction=1)))
# 14. RESERVED-BIT flags[1]|=0x80 (mutate sau pack — setter không tạo được; b6 là trigger_price_type)
_rv = dict(slot=1013, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
           market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
           flags1_reserved=0x80)
_rb = pack_order(_rv)
assert (_rb[86] & 0x80) == 0x80 and (_rb[86] & 0x40) == 0
_v = {"name": "of_reserved_bits_80", "hex": h(_rb), "flags": [_rb[85], _rb[86], _rb[87]], **_rv}
_v["reserved_bits_flags_offset"] = FLAGS_OFFSET + 1  # 86 — offset TRONG vector
_v["expect_reserved_preserved"] = 1
order_flags_python.append(_v)
# 15. legacy bit_flags đủ 6 bit thấp set (0x3F) — per-bit flags[2] coverage set-side
order_flags_python.append(of_vec("of_legacy_bits_3f_set", dict(
    slot=1014, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x3F), expect_legacy_mask_set=0x3F))
# 16. legacy bit_flags 0 — clear-side cho cả 6 bit
order_flags_python.append(of_vec("of_legacy_bits_clear", dict(
    slot=1015, price=50_000_000_000, base_asset_amount=10**18, offset=1000, order_id=oid(),
    market_index=0, order_type=1, market_type=1, direction=0, offset_type_oracle=True,
    legacy_bit_flags=0x00), expect_legacy_mask_set=0))
# 17. trigger_price_type Last (flags[1] b6 = 1) — reverse tripwire cho #14 (append CUỐI để oid khớp contract)
order_flags_python.append(of_vec("of_last_trigger_bit", dict(
    slot=1016, price=50_000_000_000, base_asset_amount=10**18, trigger_price=60_000_000_000,
    offset=1000, order_id=oid(), market_index=0, order_type=2, market_type=1, direction=0,
    offset_type_oracle=True, trigger_condition=0, trigger_price_type=1),
    expect_trigger_price_type=1))
# 18. spot trigger_price_type Last (mirror #17 trên base spot market)
order_flags_python.append(of_vec("of_spot_last_trigger_bit", dict(
    slot=1017, price=50_000_000_000, base_asset_amount=10**18, trigger_price=60_000_000_000,
    offset=1000, order_id=oid(), market_index=1, order_type=2, market_type=0, direction=0,
    offset_type_oracle=True, trigger_condition=0, trigger_price_type=1),
    expect_trigger_price_type=1))

# ---------------- auction_vectors / router_vectors ----------------
# expected_* là pins từ contract emitter (d2) — KHÔNG để None: test
# test_auction_mirror đối chiếu strict khi expected có giá trị.
auction_vectors = [
    {"name": "auc_i128_extreme", "order_slot": 2**63, "current_slot": 2**64 - 2, "auction_duration": 255,
     "auction_start_price": 2**62, "auction_end_price": -(2**62), "valid_oracle_price": 2**61,
     "expected_auction_price": None, "expected_err": "MathError",
     "note": "expected do contract emitter tính tại (d2)"},
]
router_vectors = [
    {"name": "rt_lim_offset_oracle", "order_type": 1, "offset": 1000, "offset_type": 0,
     "order_slot": 1000, "current_slot": 1005, "auction_duration": 10,
     "auction_start_price": 1_000_000, "auction_end_price": 2_000_000, "valid_oracle_price": 9_999_999,
     "expected_branch": "oracle-offset", "expected_price": 11499999},
    {"name": "rt_lim_offset_queue", "order_type": 1, "offset": 1000, "offset_type": 1,
     "order_slot": 1000, "current_slot": 1005, "auction_duration": 10,
     "auction_start_price": 1_000_000, "auction_end_price": 2_000_000, "valid_oracle_price": 9_999_999,
     "expected_branch": "oracle-offset", "expected_price": 1500000},
    {"name": "rt_lim_zero_offset_oracle", "order_type": 1, "offset": 0, "offset_type": 0,
     "order_slot": 1000, "current_slot": 1005, "auction_duration": 10,
     "auction_start_price": 1_000_000, "auction_end_price": 2_000_000, "valid_oracle_price": 9_999_999,
     "expected_branch": "fixed", "expected_price": 1500000},
]

# Sections generator KHÔNG sở hữu (từ contract-side / nguồn khác): giữ nguyên từ
# file hiện có để chạy lại generator là idempotent, không bao giờ xóa dữ liệu.
FOREIGN_SECTIONS = ("order_flags_contract", "user_account", "user_tail")
foreign = {}
if OUT.exists():
    _prev = json.loads(OUT.read_text())
    for _k in FOREIGN_SECTIONS:
        foreign[_k] = _prev.get(_k, [])

doc = {
    "signed_msg": {
        "standard": standard,
        "delegate": delegate,
        "trigger": trigger,
        "abnormal": abnormal,
    },
    "user_tail": foreign.get("user_tail", []),
    "user_account": foreign.get("user_account", []),
    "order_flags_python": order_flags_python,
    "order_flags_contract": foreign.get("order_flags_contract", []),
    "auction_vectors": auction_vectors,
    "router_vectors": router_vectors,
}

OUT.write_text(json.dumps(doc, indent=1, sort_keys=True))
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
print("standard:", len(standard), "| delegate:", len(delegate), "| trigger:", len(trigger),
      "| abnormal:", len(abnormal), "| order_flags_python:", len(order_flags_python))
