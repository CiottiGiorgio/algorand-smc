"""
File that implements all things related to the recipient side of an SMC.
"""
import asyncio
import logging
from asyncio import Lock
from asyncio import TimeoutError as AsyncTimeoutError
from asyncio import wait_for
from typing import Optional

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.error import IndexerHTTPError
from algosdk.mnemonic import to_private_key
from algosdk.transaction import LogicSigTransaction, wait_for_confirmation
from websockets.exceptions import ConnectionClosed

from algorandsmc.errors import SMCBadFunding, SMCBadSetup, SMCBadSignature

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import Payment, SMCMethod, setupProposal, setupResponse
from algorandsmc.templates import smc_lsig_pay, smc_lsig_refund, smc_msig, smc_txn_pay
from algorandsmc.utils import get_sandbox_algod, get_sandbox_indexer

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


async def setup_channel(websocket) -> setupProposal:
    """
    Handles the setup of the channel on the recipient side.
    This should include all reasonable checks that the recipient would want to do even if
     commented out.

    :param websocket:
    :return: Sender's side of arguments for this channel
    """
    node_algod = get_sandbox_algod()

    setup_proposal: setupProposal = setupProposal.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_proposal.sender):
        raise SMCBadSetup("Sender address is not a valid Algorand address.")
    # Refund condition should be sound.
    if not setup_proposal.minRefundBlock <= setup_proposal.maxRefundBlock:
        raise SMCBadSetup("Refund condition can never happen.")

    chain_status = node_algod.status()
    # Should be at the very most 5 seconds per block. More than that and we can say that we are out of sync.
    # if not chain_status["time-since-last-round"] < 6 * 10**9:
    #     raise Exception("Recipient knowledge of the chain is not synchronized.")
    # Channel lifetime should be enough.
    if (
        not setup_proposal.minRefundBlock
        >= chain_status["last-round"] + MIN_ACCEPTED_LIFETIME
    ):
        raise SMCBadSetup("Channel lifetime is not reasonable.")

    logging.info("setup_proposal = %s", setup_proposal)

    # Compiling msig template on the recipient side.
    proposed_msig = smc_msig(
        setup_proposal.sender,
        RECIPIENT_ADDR,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    logging.info("proposed_msig.address() = %s", proposed_msig.address())
    async with OC_LOCK:
        if proposed_msig.address() in OPEN_CHANNELS:
            raise SMCBadSetup("This channel is already open.")

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

    return setup_proposal


async def receive_payment(websocket, accepted_setup: setupProposal) -> Payment:
    """
    Handles the protocol for receiving a payment.

    :param websocket:
    :param accepted_setup: Sender's side of arguments for this channel
    :return: lsig that allows recipient to settle a payment signed from both parties.
    """
    node_indexer = get_sandbox_indexer()

    payment_proposal = Payment.FromString(await websocket.recv())

    logging.info("payment_proposal = %s", payment_proposal)

    derived_msig = smc_msig(
        accepted_setup.sender,
        RECIPIENT_ADDR,
        accepted_setup.nonce,
        accepted_setup.minRefundBlock,
        accepted_setup.maxRefundBlock,
    )
    payment_lsig = smc_lsig_pay(
        accepted_setup.sender,
        RECIPIENT_ADDR,
        payment_proposal.cumulativeAmount,
        accepted_setup.minRefundBlock,
    )
    # FIXME: This should only verify that the sender's signature is valid. Not both together.
    #  Recipient can always correctly sign any lsig.
    payment_lsig.sign_multisig(derived_msig, RECIPIENT_PRIVATE_KEY)
    payment_lsig.lsig.msig.subsigs[0].signature = payment_proposal.lsigSignature
    if not payment_lsig.verify():
        raise SMCBadSignature(
            "Sender multisig subsig of the payment lsig is not valid."
        )

    try:
        msig_balance = node_indexer.account_info(derived_msig.address())["account"][
            "amount-without-pending-rewards"
        ]
    except IndexerHTTPError as err:
        raise SMCBadFunding(
            "Could not find msig account. Must be below minimum balance."
        ) from err
    # We are ignoring fees for the moment.
    if msig_balance < payment_proposal.cumulativeAmount:
        raise SMCBadFunding("Balance of msig cannot cover this payment.")

    return payment_proposal


async def settle(accepted_setup: setupProposal, last_payment: Payment) -> None:
    """
    Compiles and submits payment transaction to the Layer-1

    :param accepted_setup: Sender's side of arguments for this channel
    :param last_payment: Last accepted Payment
    """
    node_algod = get_sandbox_algod()

    derived_msig = smc_msig(
        accepted_setup.sender,
        RECIPIENT_ADDR,
        accepted_setup.nonce,
        accepted_setup.minRefundBlock,
        accepted_setup.maxRefundBlock,
    )
    derived_pay_lsig = smc_lsig_pay(
        accepted_setup.sender,
        RECIPIENT_ADDR,
        last_payment.cumulativeAmount,
        accepted_setup.minRefundBlock,
    )
    derived_pay_lsig.sign_multisig(derived_msig, RECIPIENT_PRIVATE_KEY)
    derived_pay_lsig.lsig.msig.subsigs[0].signature = last_payment.lsigSignature
    # FIXME: This template could compile a transaction that is outside of the range accepted by the pay lsig.
    pay_txn = smc_txn_pay(
        derived_msig.address(),
        accepted_setup.sender,
        RECIPIENT_ADDR,
        last_payment.cumulativeAmount,
    )

    assert pay_txn.fee <= 1_000_000

    pay_txn_signed = LogicSigTransaction(pay_txn, derived_pay_lsig)

    txid = node_algod.send_transaction(pay_txn_signed)
    wait_for_confirmation(node_algod, txid)

    logging.info("Settlement executed\nTxID = %s", txid)


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
        # We want to have at least 10 blocks before sending the highest paying transaction.
        if chain_status["last-round"] >= accepted_setup.minRefundBlock - 10:
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
