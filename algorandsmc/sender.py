"""
File that implements all things related to the sender side of an SMC.
"""
import asyncio

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.mnemonic import to_private_key

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import SMCMethod, setupProposal, setupResponse

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)


async def sender(websocket):
    await websocket.send(
        SMCMethod(method=SMCMethod.MethodEnum.SETUP_CHANNEL).SerializeToString()
    )
    await websocket.send(
        setupProposal(
            sender=SENDER_ADDR, nonce=1024, minRefundBlock=10_000, maxRefundBlock=11_000
        ).SerializeToString()
    )

    setup_response = setupResponse.FromString(await websocket.recv())
    if not is_valid_address(setup_response.recipient):
        raise ValueError

    print(setup_response)
    # TODO: Sender could dryrun the lsig + sender signature + recipient signature to
    #  verify that they will be able in the future to be refunded.


async def main():
    async with websockets.connect("ws://localhost:55000") as websocket:
        await sender(websocket)


if __name__ == "__main__":
    asyncio.run(main())
