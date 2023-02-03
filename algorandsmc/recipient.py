import asyncio

import websockets
from algosdk.encoding import is_valid_address

from algorandsmc.smc_pb2 import setupProposal, SMCMethod


RECIPIENT_ADDR = "QPKVS55LXLVR5AGHLE4B5T5HTXJSFP5ZBVEWVN5DGPC4FV267AVU35ZZEI"


async def setup_channel(websocket):
    setup_proposal = setupProposal.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_proposal.sender):
        raise ValueError
    
    print(setup_proposal)


async def receive_payment(websocket):
    pass


async def recipient(websocket):
    method: SMCMethod = SMCMethod.FromString(await websocket.recv())
    match method.method:
        case SMCMethod.MethodEnum.SETUP_CHANNEL:
            await setup_channel(websocket)
        case SMCMethod.MethodEnum.PAY:
            await receive_payment(websocket)


async def main():
    async with websockets.serve(recipient, "localhost", 55000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
