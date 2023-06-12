"""
File that implements all things related to the sender side of an SMC.
"""
import logging
from asyncio import sleep

from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.error import IndexerHTTPError, AlgodHTTPError
from algosdk.mnemonic import to_private_key
from algosdk.transaction import LogicSigTransaction, PaymentTxn, wait_for_confirmation

from algorandsmc.errors import SMCBadSetup, SMCCannotBeRefunded

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import Payment, SMCMethod, setupProposal, setupResponse
from algorandsmc.templates import (
    smc_lsig_refund,
    smc_lsig_settlement,
    smc_msig,
    smc_txn_refund,
)
from algorandsmc.utils import get_sandbox_algod, get_sandbox_indexer

logging.root.setLevel(logging.INFO)

SENDER_PRIVATE_KEY_MNEMONIC = (
    "people disagree couch mind bean tortoise project gorilla suffer "
    "become table issue used cage satisfy umbrella live wealth square "
    "offer spy derive labor ability margin"
)
SENDER_PRIVATE_KEY = to_private_key(SENDER_PRIVATE_KEY_MNEMONIC)
SENDER_ADDR = address_from_private_key(SENDER_PRIVATE_KEY)

# Sender signs payment lsigs with closeout to itself. This way, it's impossible to replay a settlement multiple
#  times because the shared msig will not hold any funds.
# However, sender should never fund a channel that was already settled.
# If the channel is re-financed after a settlement, payments could be replayed.
# It is always safe to re-finance a channel before the first settlement also because of the closeout.
# As a proxy for remembering past signed payment lsigs, we will use all known channels.
# It could indeed be the case that for a specific channel, no payment was signed, and therefore it is safe to re-open.
# In this implementation, we will be conservative and just never re-open a known channel.
KNOWN_CHANNELS = set()

# Margin note: It is easy to decide if we know a channel because exactly all the arguments that uniquely determine
#  an SMC, are also embedded in the address of the shared msig (more details in the docstring of smc_msig).
#  It is therefore sufficient to remember all addresses of the msigs to check if we know a channel.


async def setup_channel(websocket, setup_proposal: setupProposal) -> setupResponse:
    """
    Handles the setup of the channel on the sender side.

    :param websocket:
    :param setup_proposal: Channel arguments to be sent as a proposal
    :return: Recipient's side of arguments for this channel
    """
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
    proposed_msig = smc_msig(
        SENDER_ADDR,
        setup_response.recipient,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    if proposed_msig.address() in KNOWN_CHANNELS:
        raise SMCBadSetup("This channel is known.")

    KNOWN_CHANNELS.add(proposed_msig.address())
    logging.info("accepted_msig.address() = %s", proposed_msig.address())

    # Compiling lsig template on the sender side.
    accepted_refund_lsig = smc_lsig_refund(
        SENDER_ADDR, setup_proposal.minRefundBlock, setup_proposal.maxRefundBlock
    )

    # Merging signatures for the lsig
    accepted_refund_lsig.sign_multisig(proposed_msig, SENDER_PRIVATE_KEY)
    accepted_refund_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature
    if not accepted_refund_lsig.verify():
        # Least incomprehensible sentence in this code.
        raise SMCBadSetup("Recipient multisig subsig of the refund lsig is not valid.")

    logging.info("Channel accepted.")

    return setup_response


async def fund(
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
    node_indexer = get_sandbox_indexer()

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

    # BUGFIX: The information about the msig balance is not updated immediately after
    #  the transaction is confirmed when using the sandbox. This is some indexer shenanigan.
    #  Query the state of the msig until it shows a positive balance and only then send L2 payments.
    # FIXME: Ideally this polling would have at the very least a timeout.
    while True:
        try:
            # Assuming that any positive balance will not throw an error.
            # This still doesn't ensure that the balance is exactly what was expected by the fund transaction but
            #  close enough.
            node_indexer.account_info(derived_msig.address())["account"][
                "amount-without-pending-rewards"
            ]
        except IndexerHTTPError:
            pass
        else:
            break
        await sleep(1.0)

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
    payment_lsig_proposal = smc_lsig_settlement(
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
    """
    Handles the end of a channel lifetime. It submits refund transaction OR detect channel settlement
     from the recipient side.

    :param setup_proposal: Sender's side of arguments for this channel
    :param setup_response: Recipient's side of arguments for this channel
    """
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
        # ALGO balance of 0 could make the indexer not recognize the address as valid.
        # Assuming that the sender would only call this function if they know they funded msig,
        #  the only reason this account could have 0 ALGO balance, is if the recipient
        #  settled the channel.
        # FIXME: There has been many instances where the recipient settled the channel but the honest sender didn't
        #  follow this path. It tried to execute the refund and (correctly) failed for overspending.
        #  This is because in sandbox mode transaction confirmation is not enough to guarantee that the indexer knows
        #  about the new balances.
        try:
            msig_balance = node_indexer.account_info(derived_msig.address())["account"][
                "amount-without-pending-rewards"
            ]
        except IndexerHTTPError as err:
            raise SMCCannotBeRefunded from err

        # Kind of redundant condition. Indexer does not seem to find accounts for which ALGO balance is 0.
        #  It can't even be the case that the account has 0 ALGO but positive ASA balance because
        #  ASAs require minimum ALGO balance.
        # We keep this condition here anyway to not rely on the behaviour of the indexer to not find
        #  accounts with 0 ALGO balance.
        if msig_balance == 0:
            raise SMCCannotBeRefunded

        last_round = node_algod.status()["last-round"]
        if last_round >= setup_proposal.minRefundBlock:
            # Refund condition is online.
            break

        await sleep(2.0)

    refund_txn = smc_txn_refund(
        derived_msig.address(),
        SENDER_ADDR,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )

    assert refund_txn.fee <= 1_000_000

    derived_refund_lsig = smc_lsig_refund(
        SENDER_ADDR, setup_proposal.minRefundBlock, setup_proposal.maxRefundBlock
    )
    derived_refund_lsig.sign_multisig(derived_msig, SENDER_PRIVATE_KEY)
    derived_refund_lsig.lsig.msig.subsigs[1].signature = setup_response.lsigSignature

    refund_txn_signed = LogicSigTransaction(refund_txn, derived_refund_lsig)

    try:
        txid = node_algod.send_transaction(refund_txn_signed)
    except AlgodHTTPError as err:
        logging.error("Could not execute refund condition. This is probably because we had old indexer data and we"
                      "thought that recipient didn't settle.")
        raise err
    wait_for_confirmation(node_algod, txid)

    logging.info("Refund executed. TxID = %s", txid)
