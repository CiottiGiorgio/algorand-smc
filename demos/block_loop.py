"""
This file implements a script that will submit a transaction periodically.
This is used for the sandbox in dev mode to have the blocks advance at a predictable speed.
"""
import asyncio
import logging
from asyncio import sleep

from algosdk.account import address_from_private_key
from algosdk.mnemonic import to_private_key
from algosdk.transaction import PaymentTxn

from algorandsmc.utils import get_sandbox_algod

logging.root.setLevel(logging.INFO)


LOOP_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
LOOP_PRIVATE_KEY = to_private_key(LOOP_PRIVATE_KEY_MNEMONIC)
LOOP_ADDR = address_from_private_key(LOOP_PRIVATE_KEY)


async def block_loop():
    """Sends a dummy transaction every second to generate a new block"""

    node_algod = get_sandbox_algod()

    while True:
        sugg_params = node_algod.suggested_params()
        node_algod.send_transaction(
            PaymentTxn(LOOP_ADDR, sugg_params, LOOP_ADDR, 0).sign(LOOP_PRIVATE_KEY)
        )
        logging.info("Block advanced.")
        await sleep(1.0)


if __name__ == "__main__":
    try:
        asyncio.run(block_loop())
    except KeyboardInterrupt:
        pass
