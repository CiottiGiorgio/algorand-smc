"""
File that implements the template for the payment transaction
"""
from algosdk.transaction import PaymentTxn

from algorandsmc.utils import get_sandbox_algod


def smc_txn_pay(msig: str, sender: str, recipient: str, amount: int):
    node_algod = get_sandbox_algod()

    sugg_params = node_algod.suggested_params()

    return PaymentTxn(msig, sugg_params, recipient, amount, close_remainder_to=sender)
