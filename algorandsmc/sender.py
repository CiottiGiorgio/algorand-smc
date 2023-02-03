"""
File that implements all things related to the sender side of an SMC.
"""
import asyncio

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.mnemonic import to_private_key

from algorandsmc.sigtemplates import smc_lsig, smc_msig

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import SMCMethod, setupProposal, setupResponse

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)


NONCE = 1024
MIN_REFUND_BLOCK = 10_000
MAX_REFUND_BLOCK = 11_000


async def sender(websocket):
    await websocket.send(
        SMCMethod(method=SMCMethod.MethodEnum.SETUP_CHANNEL).SerializeToString()
    )
    await websocket.send(
        setupProposal(
            sender=SENDER_ADDR,
            nonce=NONCE,
            minRefundBlock=MIN_REFUND_BLOCK,
            maxRefundBlock=MAX_REFUND_BLOCK,
        ).SerializeToString()
    )

    setup_response = setupResponse.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_response.recipient):
        raise ValueError

    print(setup_response)

    # Compiling msig template on the sender side.
    accepted_msig = smc_msig(
        SENDER_ADDR, setup_response.recipient, NONCE, MIN_REFUND_BLOCK, MAX_REFUND_BLOCK
    )
    # Compiling lsig template on the sender side.
    accepted_lsig = smc_lsig(SENDER_ADDR, MIN_REFUND_BLOCK, MAX_REFUND_BLOCK)

    # Merging signatures for the lsig
    accepted_lsig.sign_multisig(accepted_msig, SENDER_PRIVATE_KEY)
    accepted_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature
    if not accepted_lsig.verify():
        raise ValueError

    print(f"{accepted_lsig.verify() = }")

    # TODO: Sender should at this point fund the msig and send the TxID to recipient.


async def main():
    async with websockets.connect("ws://localhost:55000") as websocket:
        await sender(websocket)


if __name__ == "__main__":
    asyncio.run(main())
