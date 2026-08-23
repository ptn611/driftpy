from typing import Optional

from anchorpy import Program
from solders.pubkey import Pubkey
from solana.rpc.commitment import Commitment

from driftpy.accounts import DataAndSlot
from driftpy.decode.user import decode_user
from driftpy.types import UserAccount

from driftpy.accounts.ws.account_subscriber import WebsocketAccountSubscriber
from driftpy.accounts.types import UserAccountSubscriber


class WebsocketUserAccountSubscriber(
    WebsocketAccountSubscriber[UserAccount], UserAccountSubscriber
):
    def __init__(
        self,
        pubkey: Pubkey,
        program: Program,
        commitment: Commitment = Commitment("confirmed"),
        initial_data: Optional[DataAndSlot[UserAccount]] = None,
    ):
        # Packed Order layout: always decode via the manual decoder.
        super().__init__(pubkey, program, commitment, decode_user, initial_data)

    def get_user_account_and_slot(self) -> Optional[DataAndSlot[UserAccount]]:
        return self.data_and_slot
