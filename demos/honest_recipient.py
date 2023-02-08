"""
This file implements a demo for an honest recipient.
"""
import asyncio
import logging
from asyncio import TimeoutError as AsyncTimeoutError
from asyncio import wait_for
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from algorandsmc.errors import SMCBadFunding, SMCBadSetup, SMCBadSignature
from algorandsmc.recipient import RECIPIENT_ADDR, receive_payment, settle, setup_channel

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import Payment, SMCMethod
from algorandsmc.utils import get_sandbox_algod


async def honest_recipient(websocket) -> None:
    """
    Implements the time-dependent state machine for the honest recipient side.
    This machine can handle setup, payments and settlement depending on the time related or sender related
    events/conditions.

    :param websocket:
    """
    node_algod = get_sandbox_algod()
    method = SMCMethod.FromString(await websocket.recv())
    if not method.method == SMCMethod.SETUP_CHANNEL:
        raise ValueError("Expected channel setup method.")

    try:
        accepted_setup = await setup_channel(websocket)
    except SMCBadSetup as err:
        logging.error("%s", err)
        return

    last_payment: Optional[Payment] = None

    # The recipient wants to keep accepting payments but also monitor the lifetime of this
    # channel to settle it before the refund condition comes online.
    while True:
        try:
            method_message = await wait_for(websocket.recv(), 2.0)
        except AsyncTimeoutError:
            # No new payments last time we waited.
            pass
        except ConnectionClosed:
            # Sender has closed websocket.
            logging.error("Sender has closed the websocket.")
            break
        else:
            method = SMCMethod.FromString(method_message)
            if not method.method == SMCMethod.PAY:
                logging.error("Expected payment method.")
                break

            try:
                payment = await receive_payment(websocket, accepted_setup)
            except (SMCBadSignature, SMCBadFunding) as err:
                logging.error("Bad payment. %s", err)
                break
            else:
                if (
                    last_payment
                    and not payment.cumulativeAmount > last_payment.cumulativeAmount
                ):
                    # Sender misbehaved.
                    logging.error("Expected increasing payments.")
                    break
                logging.info("Payment accepted.")
                last_payment = payment

        chain_status = node_algod.status()
        # We want to have at least 5 blocks before sending the highest paying transaction.
        if chain_status["last-round"] >= accepted_setup.minRefundBlock - 5:
            break

    if last_payment:
        await settle(accepted_setup, last_payment)


async def main():
    """Entry point for the async flow"""
    logging.info("recipient: %s", RECIPIENT_ADDR)

    # pylint: disable-next=no-member
    async with websockets.serve(honest_recipient, "localhost", 55_000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
