"""
File that implements all things related to the recipient side of an SMC.
"""
import asyncio
import logging
from asyncio import Lock, wait_for, TimeoutError

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.mnemonic import to_private_key
from websockets.exceptions import ConnectionClosed

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import setupProposal, setupResponse, SMCMethod, Payment
from algorandsmc.templates import smc_lsig_refund, smc_msig
from algorandsmc.utils import get_sandbox_algod

logging.root.setLevel(logging.INFO)

RECIPIENT_PRIVATE_KEY_MNEMONIC = (
    "question middle cube wire breeze choose rival accident disorder wood "
    "park erosion uphold shine picnic industry diagram attack magnet park "
    "evoke music auto above gas"
)
RECIPIENT_PRIVATE_KEY = to_private_key(RECIPIENT_PRIVATE_KEY_MNEMONIC)
RECIPIENT_ADDR = address_from_private_key(RECIPIENT_PRIVATE_KEY)

# This is the minimum lifetime of a channel that the recipient is willing to accept.
# The channel should last at least 2_000 blocks starting from the current one.
MIN_ACCEPTED_LIFETIME = 2_000
# Recipient has no opinion on how long should the refund windows be.
# Recipient should remember the channel that he has signed lsigs for and avoid accepting them anyway.
# Recipient cannot be tricked into opening a new channel for which there is an already-signed lsig that happens
#  earlier than the one proposed because the setup parameters change the C account. Therefore, they also change
#  the whole msig account and so it is safe to open a new channel so long as _any_ parameter changes.


OPEN_CHANNELS = set()
OC_LOCK = Lock()


async def setup_channel(websocket):
    node_algod = get_sandbox_algod()

    setup_proposal: setupProposal = setupProposal.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_proposal.sender):
        raise ValueError("Sender address is not a valid Algorand address.")
    # Refund condition should be sound.
    if not setup_proposal.minRefundBlock <= setup_proposal.maxRefundBlock:
        raise ValueError("Refund condition can never happen.")

    chain_status = node_algod.status()
    # Should be at the very most 5 seconds per block. More than that and we can say that we are out of sync.
    # if not chain_status["time-since-last-round"] < 6 * 10**9:
    #     raise Exception("Recipient knowledge of the chain is not synchronized.")
    # Channel lifetime should be enough.
    if (
        not setup_proposal.minRefundBlock
        >= chain_status["last-round"] + MIN_ACCEPTED_LIFETIME
    ):
        raise ValueError("Channel lifetime is not reasonable.")

    logging.info(f"{setup_proposal = }")

    # Compiling msig template on the recipient side.
    proposed_msig = smc_msig(
        setup_proposal.sender,
        RECIPIENT_ADDR,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    logging.info(f"{proposed_msig.address() = }")
    async with OC_LOCK:
        if proposed_msig.address() in OPEN_CHANNELS:
            raise ValueError("This channel is already open.")

    # Compiling lsig template on the recipient side.
    proposed_refund_lsig = smc_lsig_refund(
        setup_proposal.sender,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    # Signing the lsig with the msig only on the recipient side.
    # Crucially, the lsig MUST not be signed using the recipient secret key directly.
    # That would allow the sender to close out the recipient balance in the future.
    # TODO: Create a test that validates that the lsig CANNOT be used on the recipient account in the future.
    #  Also, create a test that validates that the lsig CAN be used on the msig account in the future.
    #  As it turns out, this is tricky to do because a dryrun will not match the correct signature against
    #  the sender account.
    #  https://github.com/algorand/go-algorand/issues/3953#issuecomment-1197423517
    #  Instead, the sandbox correctly refuses to process a transaction with lsig where
    #  the lsig was not signed by the msig.
    proposed_refund_lsig.sign_multisig(proposed_msig, RECIPIENT_PRIVATE_KEY)
    refund_lsig_signature = proposed_refund_lsig.lsig.msig.subsigs[1].signature

    # Recipient accepts this channel.
    async with OC_LOCK:
        OPEN_CHANNELS.add(proposed_msig.address())
    logging.info("Channel accepted.")
    await websocket.send(
        setupResponse(
            recipient=RECIPIENT_ADDR,
            lsigSignature=refund_lsig_signature,
        ).SerializeToString()
    )
    # At this point, the recipient does not own a correctly signed lsig because it's missing sender's signature.

    return setup_proposal.minRefundBlock


async def receive_payment(websocket):
    logging.info(Payment.FromString(await websocket.recv()))


async def settle():
    ...


async def recipient(websocket):
    node_algod = get_sandbox_algod()
    method = SMCMethod.FromString(await websocket.recv())
    if not method.method == SMCMethod.SETUP_CHANNEL:
        raise ValueError("Expected channel setup method.")
    min_refund_block = await setup_channel(websocket)

    # The recipient wants to keep accepting payments but also monitor the lifetime of this
    # channel to settle it before the refund condition comes online.
    while True:
        try:
            method_message = await wait_for(websocket.recv(), 2.0)
        except TimeoutError:
            # No new payments last time we waited.
            pass
        except ConnectionClosed:
            # Sender has closed websocket.
            break
        else:
            method = SMCMethod.FromString(method_message)
            if not method.method == SMCMethod.PAY:
                raise ValueError("Expected payment method.")
            await receive_payment(websocket)

        chain_status = node_algod.status()
        # We want to have at least 10 blocks before sending the highest paying transaction.
        if chain_status["last-round"] >= min_refund_block - 10:
            break

    await settle()


async def main():
    async with websockets.serve(recipient, "localhost", 55_000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
