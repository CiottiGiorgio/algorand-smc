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
from algosdk.transaction import LogicSigTransaction, PaymentTxn, wait_for_confirmation

from algorandsmc.errors import SMCBadSetup, SMCCannotBeRefunded

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import Payment, SMCMethod, setupProposal, setupResponse
from algorandsmc.templates import smc_lsig_pay, smc_lsig_refund, smc_msig
from algorandsmc.templates.txn import smc_txn_refund
from algorandsmc.utils import get_sandbox_algod, get_sandbox_indexer

logging.root.setLevel(logging.INFO)

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)


async def setup_channel(websocket, setup_proposal: setupProposal) -> setupResponse:
    """
    Handles the setup of the channel on the sender side.

    :param websocket:
    :param setup_proposal: Channel arguments to be sent as a proposal
    :return: Recipient's side of arguments for this channel
    """
    get_sandbox_algod()

    await websocket.send(
        SMCMethod(method=SMCMethod.MethodEnum.SETUP_CHANNEL).SerializeToString()
    )
    await websocket.send(setup_proposal.SerializeToString())

    setup_response = setupResponse.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_response.recipient):
        raise SMCBadSetup("Recipient address is not a valid Algorand address.")

    logging.info("setup_response = %s", setup_response)

    # Compiling msig template on the sender side.
    accepted_msig = smc_msig(
        SENDER_ADDR,
        setup_response.recipient,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    logging.info("accepted_msig.address() = %s", accepted_msig.address())
    # Compiling lsig template on the sender side.
    accepted_refund_lsig = smc_lsig_refund(
        SENDER_ADDR, setup_proposal.minRefundBlock, setup_proposal.maxRefundBlock
    )

    # Merging signatures for the lsig
    accepted_refund_lsig.sign_multisig(accepted_msig, SENDER_PRIVATE_KEY)
    accepted_refund_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature
    if not accepted_refund_lsig.verify():
        # Least incomprehensible sentence in this code.
        raise SMCBadSetup("Recipient multisig subsig of the refund lsig is not valid.")

    logging.info("Channel accepted.")

    return setup_response


def fund(
    setup_proposal: setupProposal, setup_response: setupResponse, amount: int
) -> None:
    """
    Funds the msig associated with the established channel by amount.
    It should be noted that in this model it is possible to fund the msig multiple times after channel setup.

    :param setup_proposal: Sender's side of arguments for this channel
    :param setup_response: Recipient's side of arguments for this channel
    :param amount: microalgos to send
    """
    node_algod = get_sandbox_algod()

    derived_msig = smc_msig(
        SENDER_ADDR,
        setup_response.recipient,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )

    sugg_params = node_algod.suggested_params()
    txid = node_algod.send_transaction(
        PaymentTxn(SENDER_ADDR, sugg_params, derived_msig.address(), amount).sign(
            SENDER_PRIVATE_KEY
        )
    )
    wait_for_confirmation(node_algod, txid)

    logging.info("Funding TxID = %s", txid)


async def pay(
    websocket,
    setup_proposal: setupProposal,
    setup_response: setupResponse,
    cumulative_amount: int,
) -> None:
    """
    Handles the protocol for sending a payment.

    :param websocket:
    :param setup_proposal: Sender's side of arguments for this channel
    :param setup_response: Recipient's side of arguments for this channel
    :param cumulative_amount: Sum of all payments from sender to recipient
    """
    await websocket.send(SMCMethod(method=SMCMethod.MethodEnum.PAY).SerializeToString())

    derived_msig = smc_msig(
        SENDER_ADDR,
        setup_response.recipient,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    payment_lsig_proposal = smc_lsig_pay(
        SENDER_ADDR,
        setup_response.recipient,
        cumulative_amount,
        setup_proposal.minRefundBlock,
    )
    payment_lsig_proposal.sign_multisig(derived_msig, SENDER_PRIVATE_KEY)
    await websocket.send(
        Payment(
            cumulativeAmount=cumulative_amount,
            lsigSignature=payment_lsig_proposal.lsig.msig.subsigs[0].signature,
        ).SerializeToString()
    )

    logging.info("Payment accepted.")


async def refund_channel(
    setup_proposal: setupProposal, setup_response: setupResponse
) -> None:
    node_algod = get_sandbox_algod()
    node_indexer = get_sandbox_indexer()

    derived_msig = smc_msig(
        SENDER_ADDR,
        setup_response.recipient,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )

    while True:
        # This time we are going to assume that the account has enough minimum balance
        #  to be recognized by the indexer.
        # On the sender's side, it only makes sense to attempt a refund if there are money in it.
        msig_balance = node_indexer.account_info(derived_msig.address())["account"][
            "amount-without-pending-rewards"
        ]

        if not msig_balance == 0:
            # Here we are going to assume that the only reason why msig balance could be zero
            #  is that it was correctly settled by the recipient.
            raise SMCCannotBeRefunded

        last_round = node_algod.status()["last-round"]
        if last_round >= setup_proposal.minRefundBlock:
            # Refund condition is online.
            break

        await sleep(5.0)

    refund_txn = smc_txn_refund(derived_msig.address(), SENDER_ADDR)

    assert refund_txn.fee <= 1_000_000

    derived_refund_lsig = smc_lsig_refund(
        SENDER_ADDR, setup_proposal.minRefundBlock, setup_proposal.maxRefundBlock
    )
    derived_refund_lsig.sign_multisig(derived_msig, SENDER_PRIVATE_KEY)
    derived_refund_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature

    refund_txn_signed = LogicSigTransaction(refund_txn, derived_refund_lsig)

    txid = node_algod.send_transaction(refund_txn_signed)
    wait_for_confirmation(node_algod, txid)

    logging.info("Refund executed")
    logging.info("TxID = %s", txid)


async def honest_sender() -> None:
    """Demo of an honest sender"""
    setup_proposal = setupProposal(
        sender=SENDER_ADDR, nonce=1024, minRefundBlock=10_000, maxRefundBlock=10_500
    )

    # pylint: disable-next=no-member
    async with websockets.connect("ws://localhost:55000") as websocket:
        setup_response = await setup_channel(websocket, setup_proposal)
        fund(setup_proposal, setup_response, 10_000_000)
        await sleep(1.0)
        await pay(websocket, setup_proposal, setup_response, 1_000_000)
        await sleep(2.0)
        await pay(websocket, setup_proposal, setup_response, 2_000_000)
        try:
            await refund_channel(setup_proposal, setup_response)
        except SMCCannotBeRefunded:
            logging.info("Channel was settled.")
            return
        else:
            logging.info("Channel was refunded.")
            return


if __name__ == "__main__":
    logging.info("sender: %s", SENDER_ADDR)

    asyncio.run(honest_sender())
