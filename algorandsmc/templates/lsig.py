"""
File that implements the Logic Signature with the msig as the delegating account.
"""
import base64

from algosdk.encoding import decode_address
from algosdk.transaction import LogicSigAccount
from pyteal import (
    Approve,
    Assert,
    Bytes,
    Global,
    Int,
    Mode,
    Seq,
    Txn,
    TxnType,
    compileTeal,
)

from algorandsmc.utils import get_sandbox_algod


def smc_lsig_settlement(
    sender: str, recipient: str, cumulative_amount: int, min_block_refund: int
) -> LogicSigAccount:
    """
    Returns all necessary information about the logic signature that enables the sender (Alice) to pay Bob
     using the SMC.

    :param sender: Algorand address of Alice
    :param recipient: Algorand address of Bob
    :param cumulative_amount: Sum of all payments from Alice to Bob
    :param min_block_refund: Last block (not included) for which it is safe to settle a payment.
    :return: SDK wrapper around the bytecode of the logic signature
    """
    # Sandbox node
    node_algod = get_sandbox_algod()

    # As per Algorand guidelines. All lsigs should contain an end block.
    # It's dangerous to sign lsigs that last for eternity.
    lsig_pyteal = Seq(
        Assert(
            Txn.type_enum() == TxnType.Payment,
            Txn.amount() == Int(cumulative_amount),
            Txn.fee() == Global.min_txn_fee(),
            Txn.receiver() == Bytes(decode_address(recipient)),
            Txn.close_remainder_to() == Bytes(decode_address(sender)),
            Txn.rekey_to() == Global.zero_address(),
            Txn.last_valid() < Int(min_block_refund),
        ),
        Approve(),
    )

    lsig_teal = compileTeal(lsig_pyteal, Mode.Signature, version=2)

    return LogicSigAccount(base64.b64decode(node_algod.compile(lsig_teal)["result"]))


def smc_lsig_refund(
    sender: str, min_block_refund: int, max_block_refund: int
) -> LogicSigAccount:
    """
    Returns all necessary information about the logic signature that enables the sender (Alice) to be refunded according
     to usual constraints of an SMC.

    :param sender: Algorand address of Alice
    :param min_block_refund: Minimum block for Alice's refund transaction to be valid
    :param max_block_refund: Last block for Alice's refund transaction to be valid
    :return: SDK wrapper around the bytecode of the logic signature
    """
    # Sandbox node
    node_algod = get_sandbox_algod()

    # As per Algorand guidelines. All lsigs should contain an end block.
    # It's dangerous to sign lsigs that last for eternity.
    lsig_pyteal = Seq(
        Assert(
            Txn.type_enum() == TxnType.Payment,
            Txn.amount() == Int(0),
            Txn.fee() == Global.min_txn_fee(),
            Txn.close_remainder_to() == Bytes(decode_address(sender)),
            Txn.rekey_to() == Global.zero_address(),
            Txn.first_valid() >= Int(min_block_refund),
            Txn.last_valid() <= Int(max_block_refund),
        ),
        Approve(),
    )

    lsig_teal = compileTeal(lsig_pyteal, Mode.Signature, version=2)

    return LogicSigAccount(base64.b64decode(node_algod.compile(lsig_teal)["result"]))
