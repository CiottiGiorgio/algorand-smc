"""
This file implements a demo for an undercollateralized sender.
"""
import asyncio
import logging
from asyncio import sleep

import websockets

from algorandsmc.errors import SMCCannotBeRefunded
from algorandsmc.sender import SENDER_ADDR, fund, pay, refund_channel, setup_channel

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import setupProposal


async def undercollateralized_dishonest_sender() -> None:
    """
    Demo of a dishonest sender.
    This sender will try to submit a payment that is not covered on the Layer-1.
    """
    setup_proposal = setupProposal(
        sender=SENDER_ADDR, nonce=2048, minRefundBlock=10_000, maxRefundBlock=10_500
    )

    # pylint: disable-next=no-member
    async with websockets.connect("ws://localhost:55000") as websocket:
        setup_response = await setup_channel(websocket, setup_proposal)
        await fund(setup_proposal, setup_response, 10_000_000)
        await pay(websocket, setup_proposal, setup_response, 5_000_000)
        await sleep(1.0)
        await pay(websocket, setup_proposal, setup_response, 11_000_000)
        # pylint: disable-next=duplicate-code
        try:
            await refund_channel(setup_proposal, setup_response)
        except SMCCannotBeRefunded:
            logging.info("Recipient settled the channel.")


if __name__ == "__main__":
    asyncio.run(undercollateralized_dishonest_sender())
