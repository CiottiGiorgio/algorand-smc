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
from algorandsmc.smc_pb2 import Payment, SMCMethod, setupProposal, setupResponse
from algorandsmc.templates import smc_lsig_refund, smc_msig
from algorandsmc.templates.lsig import smc_lsig_pay
from algorandsmc.utils import get_sandbox_algod

logging.root.setLevel(logging.INFO)

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)


async def setup_channel(
    websocket, nonce: int, min_refund_block: int, max_refund_block: int
) -> setupResponse:
    node_algod = get_sandbox_algod()

    await websocket.send(
        SMCMethod(method=SMCMethod.MethodEnum.SETUP_CHANNEL).SerializeToString()
    )
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

    return setup_response


async def pay(
    websocket,
    setup_response: setupResponse,
    cumulative_amount: int,
    nonce: int,
    min_block_refund: int,
    max_block_refund: int,
):
    await websocket.send(SMCMethod(method=SMCMethod.MethodEnum.PAY).SerializeToString())

    derived_msig = smc_msig(
        SENDER_ADDR, setup_response.recipient, nonce, min_block_refund, max_block_refund
    )
    payment_lsig_proposal = smc_lsig_pay(
        SENDER_ADDR, setup_response.recipient, cumulative_amount, min_block_refund
    )
    payment_lsig_proposal.sign_multisig(derived_msig, SENDER_PRIVATE_KEY)
    await websocket.send(
        Payment(
            cumulativeAmount=cumulative_amount,
            lsigSignature=payment_lsig_proposal.lsig.msig.subsigs[0].signature,
        ).SerializeToString()
    )


async def honest_sender():
    nonce = 1024
    min_block_refund, max_block_refund = 10_000, 10_500

    async with websockets.connect("ws://localhost:55000") as websocket:
        setup_response = await setup_channel(
            websocket, nonce, min_block_refund, max_block_refund
        )
        await sleep(1.0)
        await pay(
            websocket,
            setup_response,
            1_000_000,
            nonce,
            min_block_refund,
            max_block_refund,
        )
        await sleep(500.0)
        # await sleep(2.0)
        # await pay(websocket, setup_response.recipient, 2_000_000, accepted_msig, min_block_refund)


if __name__ == "__main__":
    asyncio.run(honest_sender())
