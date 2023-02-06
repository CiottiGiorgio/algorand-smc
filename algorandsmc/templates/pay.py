"""
File that implements the template for the payment transaction
"""
from algosdk.transaction import PaymentTxn

from algorandsmc.utils import get_sandbox_algod


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
