import asyncio

import websockets

from algorandsmc.smc_pb2 import setupProposal


async def sender(websocket):
    await websocket.send(setupProposal(nonce=1, minRefundBlock=1_000, maxRefundBlock=1_500).SerializeToString())


async def main():
    async with websockets.connect("ws://localhost:55000") as websocket:
        await sender(websocket)


if __name__ == "__main__":
    asyncio.run(main())
