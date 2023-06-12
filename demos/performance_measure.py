"""
We will measure and compare performances of pure L1 and L2 by letting a sequence of (confirmed) payments run for
increasing time windows.
"""
import asyncio
import itertools
import logging
import time
import timeit
from asyncio import sleep

import websockets

from algorandsmc.errors import SMCCannotBeRefunded
from algorandsmc.sender import SENDER_ADDR, setup_channel, fund, pay, refund_channel
from algorandsmc.smc_pb2 import setupProposal


async def sender_smc(time_window: float):
    """Performance of a sender"""
    setup_proposal = setupProposal(
        # sender=SENDER_ADDR, nonce=1024, minRefundBlock=10_000, maxRefundBlock=10_500
        sender=SENDER_ADDR, nonce=1024, minRefundBlock=7000, maxRefundBlock=7050
    )

    # pylint: disable-next=no-member
    async with websockets.connect("ws://localhost:55000") as websocket:
        setup_response = await setup_channel(websocket, setup_proposal)
        await fund(setup_proposal, setup_response, 10_000_000)

        time_start = time.perf_counter()

        for amount in itertools.count(1):
            await pay(websocket, setup_proposal, setup_response, amount)
            if time.perf_counter() - time_start >= time_window:
                break

        time_end = time.perf_counter()

        print(f'{time_end - time_start = }')
        print(f'{amount = }')


if __name__ == "__main__":
    asyncio.run(sender_smc(5))
