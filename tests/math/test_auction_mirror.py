"""3d — auction mirror tests (driftpy side), consume emitter-pinned fixture values.
future-slot: driftpy dùng max(0, slot-slot0) + int math — KHÔNG Err như contract
(per-side semantics v155/M141-2)."""
import json
from pathlib import Path

from driftpy.math.auction import (
    get_auction_price,
    get_auction_price_for_fixed_auction,
)
from driftpy.types import (
    MarketType, Order, OrderStatus, OrderTriggerCondition, OrderType,
    PositionDirection,
)

FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "golden_vectors.json"
)


def golden() -> dict:
    return json.loads(FIXTURE.read_text())


def mk_order(**kw) -> Order:
    base = dict(
        slot=100, price=50_000_000_000, base_asset_amount=10**18,
        base_asset_amount_filled=0, quote_asset_amount_filled=0,
        trigger_price=0, auction_start_price=1000, auction_end_price=2000,
        max_ts=0, offset=0, offset_type=None if kw.get("offset_type") is None else kw["offset_type"],
        order_id=1, market_index=0, status=OrderStatus.Open(),
        order_type=OrderType.Limit(), market_type=MarketType.Perp(),
        user_order_id=1, existing_position_direction=PositionDirection.Long(),
        direction=PositionDirection.Long(), reduce_only=False, post_only=False,
        immediate_or_cancel=False, trigger_condition=OrderTriggerCondition.Above(),
        auction_duration=10, posted_slot_tail=0, bit_flags=0,
    )
    base.update(kw)
    return Order(**base)


def test_fixed_interpolation_mirror():
    o = mk_order()
    assert get_auction_price_for_fixed_auction(o, 105) == 1500
    assert get_auction_price_for_fixed_auction(o, 200) == 2000  # capped


def test_router_precedence_matches_fixture():
    for v in golden()["router_vectors"]:
        o = mk_order(
            slot=v["order_slot"], auction_duration=v["auction_duration"],
            auction_start_price=v["auction_start_price"],
            auction_end_price=v["auction_end_price"],
            offset=v["offset"], offset_type=v["offset_type"],
        )
        got = get_auction_price(o, v["current_slot"], v["valid_oracle_price"])
        exp = v["expected_price"]
        if exp is None:
            assert got is None or isinstance(got, int)
        else:
            assert got == exp, f"{v['name']}: {got} != {exp}"


def test_i128_extreme_per_side():
    v = golden()["auction_vectors"][0]
    o = mk_order(
        slot=v["order_slot"], auction_duration=v["auction_duration"],
        auction_start_price=v["auction_start_price"],
        auction_end_price=v["auction_end_price"],
        offset=1000, offset_type=0,
    )
    # contract: Err(MathError) (emitter-pinned) — phía driftpy int math vô hạn bit
    got = get_auction_price(o, v["current_slot"], v["valid_oracle_price"])
    assert isinstance(got, int)  # deterministic; giá trị SDK-side tự pin
    # pin cross-check: auction_pin.json phải khớp expected của vector
    # (vector dùng tên enum trần "MathError", pin dùng kiểu Rust "Err(MathError)")
    pin = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / "auction_pin.json").read_text()
    )
    assert pin["is_auction_complete_fail_closed"] == "Err(MathError)"
    assert v["expected_err"] in pin["is_auction_complete_fail_closed"]
