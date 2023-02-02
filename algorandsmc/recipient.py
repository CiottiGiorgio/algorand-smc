import asyncio

import websockets

from algorandsmc.smc_pb2 import setupProposal


async def recipient(websocket):
    recv = await websocket.recv()
    print(setupProposal.FromString(recv))


async def main():
    async with websockets.serve(recipient, "localhost", 55000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
