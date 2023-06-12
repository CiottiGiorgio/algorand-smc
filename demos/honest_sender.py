"""
This file implements a demo for an honest sender.
"""
import asyncio
import logging
from asyncio import sleep

import websockets

from algorandsmc.errors import SMCCannotBeRefunded
from algorandsmc.sender import SENDER_ADDR, fund, pay, refund_channel, setup_channel

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import setupProposal


async def honest_sender() -> None:
    """Demo of an honest sender"""
    setup_proposal = setupProposal(
        # sender=SENDER_ADDR, nonce=1024, minRefundBlock=10_000, maxRefundBlock=10_500
        sender=SENDER_ADDR, nonce=1024, minRefundBlock=2150, maxRefundBlock=2200
    )

    # pylint: disable-next=no-member
    async with websockets.connect("ws://localhost:55000") as websocket:
        setup_response = await setup_channel(websocket, setup_proposal)
        await fund(setup_proposal, setup_response, 10_000_000)
        await pay(websocket, setup_proposal, setup_response, 1_000_000)
        await sleep(1.0)
        await pay(websocket, setup_proposal, setup_response, 2_000_000)
        # An honest sender should keep monitoring the chain in case of a dishonest recipient.
        # If however, the recipient correctly settled the channel, we shouldn't wait
        #  for the refund condition.

        # Since we are in an async context, leaving it would cancel the open websocket
        #  and that should trigger a settlement execution on the recipient side.
        # Therefore, even though the refund execution does not require a websocket, we choose to
        #  wait within the async context.
        # This also means that we don't care if the recipient closes the websocket with us
        #  because an honest sender should try to execute a refund regardless.
        # pylint: disable-next=duplicate-code
        try:
            await refund_channel(setup_proposal, setup_response)
        except SMCCannotBeRefunded:
            logging.info("Recipient settled the channel.")


if __name__ == "__main__":
    asyncio.run(honest_sender())
