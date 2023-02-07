"""
File that implements the template for the payment transaction
"""
from algosdk.transaction import PaymentTxn

from algorandsmc.utils import get_sandbox_algod


# FIXME: This function is gathering information about first/last block but there are
#  time constraints that must be respected to receive a payment.
def smc_txn_pay(msig: str, sender: str, recipient: str, cumulative_amount: int):
    """
    Returns all necessary information about the payment transaction that enables the recipient (Bob) to
     settle on Layer-1 the last received payment.

    :param msig: Algorand address of the msig
    :param sender: Algorand address of the sender
    :param recipient: Algorand address of the recipient
    :param cumulative_amount: Sum of all payments from Alice to Bob
    :return: SDK wrapper around the payment transaction
    """
    node_algod = get_sandbox_algod()

    sugg_params = node_algod.suggested_params()

    return PaymentTxn(
        msig, sugg_params, recipient, cumulative_amount, close_remainder_to=sender
    )


# FIXME: This function is gathering information about first/last block but there are
#  time constraints that must be respected to be refunded.
def smc_txn_refund(msig: str, sender: str) -> PaymentTxn:
    """
    Returns the compiled refund transaction that the sender (Alice) can use in case of an
    uncooperative recipient (Bob).

    :param msig: Algorand address of the msig
    :param sender: Algorand address of the sender
    :return: SDK wrapper around the refund transaction
    """
