"""
This file implements the multisignature transaction that A uses to pay B on the SMC.
"""
from algosdk.transaction import PaymentTxn, SuggestedParams


def smc_pay(
    sender: str, msig: str, recipient: str, amount: int, sp: SuggestedParams
) -> PaymentTxn:
    return PaymentTxn(msig, sp, recipient, amount, close_remainder_to=sender)
