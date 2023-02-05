"""
File that implements all things related to the sender side of an SMC.
"""
import asyncio
import logging
from asyncio import sleep

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.mnemonic import to_private_key
from algosdk.transaction import PaymentTxn, wait_for_confirmation

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import setupProposal, setupResponse
from algorandsmc.templates import smc_lsig_refund, smc_msig
from algorandsmc.utils import get_sandbox_algod

logging.root.setLevel(logging.INFO)

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)


async def setup_channel(websocket, nonce: int, min_refund_block: int, max_refund_block: int):
    node_algod = get_sandbox_algod()

    await websocket.send(
        setupProposal(
            sender=SENDER_ADDR,
            nonce=nonce,
            minRefundBlock=min_refund_block,
            maxRefundBlock=max_refund_block,
        ).SerializeToString()
    )

    setup_response = setupResponse.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_response.recipient):
        raise ValueError("Recipient address is not a valid Algorand address.")

    logging.info(f"{setup_response = }")

    # Compiling msig template on the sender side.
    accepted_msig = smc_msig(
        SENDER_ADDR, setup_response.recipient, nonce, min_refund_block, max_refund_block
    )
    logging.info(f"{accepted_msig.address() = }")
    # Compiling lsig template on the sender side.
    accepted_refund_lsig = smc_lsig_refund(
        SENDER_ADDR, min_refund_block, max_refund_block
    )

    # Merging signatures for the lsig
    accepted_refund_lsig.sign_multisig(accepted_msig, SENDER_PRIVATE_KEY)
    accepted_refund_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature
    if not accepted_refund_lsig.verify():
        # Least incomprehensible sentence in this code.
        raise ValueError("Recipient multisig subsig of the refund lsig is not valid.")

    logging.info(f"{accepted_refund_lsig.verify() = }")

    # This last step is not technically required from the sender at this point in time.
    # However, for sake of simplicity, we choose to fund the msig right now.
    # It should be noted that is not necessary to fund it before sending any Layer-2 payment.
    # Bob should only check the balance of the msig when accepting payments since this step is not
    #  crucial to channel setup.
    # This is also why the initial amount of the channel is not exchanged.
    sp = node_algod.suggested_params()
    txid = node_algod.send_transaction(
        PaymentTxn(SENDER_ADDR, sp, accepted_msig.address(), 10_000_000).sign(
            SENDER_PRIVATE_KEY
        )
    )
    wait_for_confirmation(node_algod, txid)


async def pay(websocket, amount: int):
    logging.info("pay")


async def honest_sender():
    async with websockets.connect("ws://localhost:55000") as websocket:
        await setup_channel(websocket, 1024, 10_000, 10_500)
        await sleep(3.0)
        await pay(websocket, 1_000_000)


if __name__ == "__main__":
    asyncio.run(honest_sender())
