from datetime import time
from typing import Optional

from driftpy.types import UserStatsAccount


def get_user_1w_rolling_volume_estimate(
    user_stats: UserStatsAccount, now: Optional[int] = None
) -> int:
    """Estimate user's rolling 1w volume combining maker/taker with linear decay.

    Returns value in QUOTE_PRECISION units.
    """
    now = now or int(time.time())

    one_week = 60 * 60 * 24 * 7
    since_last_taker = max(now - user_stats.last_taker_volume1w_ts, 0)
    since_last_maker = max(now - user_stats.last_maker_volume1w_ts, 0)

    taker_component = (
        user_stats.taker_volume1w * max(one_week - since_last_taker, 0)
    ) // one_week
    maker_component = (
        user_stats.maker_volume1w * max(one_week - since_last_maker, 0)
    ) // one_week

    return taker_component + maker_component
