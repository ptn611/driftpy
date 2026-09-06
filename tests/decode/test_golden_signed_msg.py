"""3d — SignedMsg golden vector consumers (mirror drift-rs decode::golden_signed_msg)."""
import json
from pathlib import Path

import pytest

from driftpy.decode.signed_msg_order import (
    decode_signed_msg_delegate_message,
    decode_signed_msg_order_params_message,
    decode_signed_msg_trigger_params,
)

FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_vectors.json"
)


def golden() -> dict:
    return json.loads(FIXTURE.read_text())


def test_standard_vectors_decode_faithful():
    for v in golden()["signed_msg"]["standard"]:
        wire = bytes.fromhex(v["wire_hex_prefixed"])
        assert wire[:8] == b"smsgv002"
        m = decode_signed_msg_order_params_message(wire)
        op = m.signed_msg_order_params
        OT = {0: "Market", 1: "Limit", 2: "TriggerMarket", 3: "TriggerLimit", 4: "Oracle"}
        MT = {0: "Spot", 1: "Perp"}
        D = {0: "Long", 1: "Short"}
        PO = {0: "NONE", 1: "MustPostOnly", 2: "TryPostOnly", 3: "Slide"}
        assert type(op.order_type).__name__.rsplit(".", 1)[-1] == OT[v["order_type"]]
        assert type(op.market_type).__name__.rsplit(".", 1)[-1] == MT[v["market_type"]]
        assert type(op.direction).__name__.rsplit(".", 1)[-1] == D[v["direction"]]
        assert op.bit_flags == v["bit_flags"]
        assert int(op.reduce_only) == v["reduce_only"]
        assert type(op.post_only).__name__.rsplit(".", 1)[-1] == PO[v["post_only"]]
        assert op.offset == v["offset"]
        assert op.offset_type == v["offset_type"]
        assert m.isolated_position_deposit == v["isolated_position_deposit"]
        assert (m.builder_idx is not None) == bool(v["has_builder"])
        assert op.market_index == v["market_index"]
        assert op.base_asset_amount == v["base_asset_amount"]
        assert m.sub_account_id == v["sub_account_id"]
        assert m.slot == v["slot"]


def test_delegate_vectors_payload_only_decode():
    # delegate decoder nhận PAYLOAD-ONLY (không prefix) — bất đối xứng có chủ ý
    for v in golden()["signed_msg"]["delegate"]:
        payload = bytes.fromhex(v["payload_hex"])
        decode_signed_msg_delegate_message(payload)  # must not raise
        wire = bytes.fromhex(v["wire_hex_prefixed"])
        assert wire[:8] == b"dsmsv002"
        assert wire[8:] == payload


def test_trigger_vectors_decode():
    for v in golden()["signed_msg"]["trigger"]:
        payload = bytes.fromhex(v["payload_hex"])
        t = decode_signed_msg_trigger_params(payload)
        assert t.trigger_price == v["trigger_price"]
        assert t.base_asset_amount == v["base_asset_amount"]


@pytest.mark.parametrize(
    "idx",
    range(10),
)
def test_abnormal_fail_closed_raise(idx):
    root = golden()["signed_msg"]["abnormal"]
    v = root[idx]
    if v["expect"] != "raise":
        pytest.skip("cross-invariant nhóm khác")
    payload = bytes.fromhex(v["payload_hex"])
    with pytest.raises(ValueError):
        decode_signed_msg_order_params_message(b"smsgv002" + payload)


def test_cross_invariant_abnormal_matches():
    consumed = 0
    for v in golden()["signed_msg"]["abnormal"]:
        if v["expect"] != "decode_ok_faithful":
            continue
        consumed += 1
        m = decode_signed_msg_order_params_message(
            b"smsgv002" + bytes.fromhex(v["payload_hex"])
        )
        op = m.signed_msg_order_params
        want_bit = v["expect_bit_0x20"] == 1
        assert (op.bit_flags & 0x20 != 0) == want_bit
        assert m.isolated_position_deposit == v["expect_isolated_position_deposit"]
    assert consumed >= 2
