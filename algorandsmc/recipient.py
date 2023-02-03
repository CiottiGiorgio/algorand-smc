import asyncio

import websockets

from algorandsmc.smc_pb2 import setupProposal, SMCMethod


async def setup_channel(websocket):
    setup_proposal = setupProposal.FromString(await websocket.recv())
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
