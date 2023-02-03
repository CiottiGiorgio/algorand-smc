import asyncio

import websockets

from algorandsmc.smc_pb2 import SMCMethod, setupProposal


SENDER_ADDR = "DWV4424IVCT6JGNFG33ZVRGYYTQHHF2MZOLA7NG5CLIO6AXETJZQMI7JAU"


async def sender(websocket):
    await websocket.send(SMCMethod(method=SMCMethod.MethodEnum.SETUP_CHANNEL).SerializeToString())
    await websocket.send(setupProposal(sender=SENDER_ADDR, nonce=1024, minRefundBlock=10_000, maxRefundBlock=11_000).SerializeToString())


async def main():
    async with websockets.connect("ws://localhost:55000") as websocket:
        await sender(websocket)


if __name__ == "__main__":
    asyncio.run(main())
