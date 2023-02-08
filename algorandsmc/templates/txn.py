"""
File that implements the template for the SMC Layer-1 transactions.
"""
from algosdk.transaction import PaymentTxn

from algorandsmc.utils import get_sandbox_algod


def smc_txn_settlement(
    msig: str,
    sender: str,
    recipient: str,
    cumulative_amount: int,
    min_refund_block: int,
):
    """
    Returns all necessary information about the payment transaction that enables the recipient (Bob) to
     settle on Layer-1 the last received payment.

    :param msig: Algorand address of the msig
    :param sender: Algorand address of the sender
    :param recipient: Algorand address of the recipient
    :param cumulative_amount: Sum of all payments from Alice to Bob
    :param min_refund_block: First valid block for the refund condition to be executable
    :return: SDK wrapper around the payment transaction
    """
    node_algod = get_sandbox_algod()

    sugg_params = node_algod.suggested_params()

    # We need at least one block before the refund condition to submit a settlement.
    if sugg_params.first >= min_refund_block:
        raise ValueError(
            "Suggested parameters for settlement transaction are not compatible with min_refund_block."
        )

    # There's enough time to submit a settlement transaction but lastBlock could be > min_refund_block.
    # In this case, we want the transaction to have a block range that will be accepted by settlement lsig.
    sugg_params.last = min(sugg_params.last, min_refund_block - 1)

    return PaymentTxn(
        msig, sugg_params, recipient, cumulative_amount, close_remainder_to=sender
    )


def smc_txn_refund(
    msig: str, sender: str, min_refund_block: int, max_refund_block: int
) -> PaymentTxn:
    """
    Returns the compiled refund transaction that the sender (Alice) can use in case of an
    uncooperative recipient (Bob).

    :param msig: Algorand address of the msig
    :param sender: Algorand address of the sender
    :param min_refund_block: First valid block for the refund condition to be executable
    :param max_refund_block: Last valid block for the refund condition to be executable
    :return: SDK wrapper around the refund transaction
    """
    node_algod = get_sandbox_algod()

    sugg_params = node_algod.suggested_params()

    if sugg_params.last < min_refund_block:
        raise ValueError(
            "Suggested parameters for refund transaction are not compatible with min_refund_block"
        )

    if sugg_params.first > max_refund_block:
        raise ValueError(
            "Suggested parameters for refund transaction are not compatible with max_refund_block"
        )

    # Assuming that min_refund_block and max_refund_block are in the obvious order,
    #  we want to set new first/last block to the largest intersection between
    #  old first/last block and min_refund_block/max_refund_block.
    sugg_params.first = max(sugg_params.first, min_refund_block)
    sugg_params.last = min(sugg_params.last, max_refund_block)

    return PaymentTxn(msig, sugg_params, sender, 0, close_remainder_to=sender)
