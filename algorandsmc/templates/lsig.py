"""
File that implements the Logic Signature with the msig as the delegating account.
"""
import base64

from algosdk.transaction import LogicSigAccount
from algosdk.v2client.algod import AlgodClient
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

from algorandsmc.utils import get_sandbox_client


def smc_lsig(
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
    node_client = get_sandbox_client()

    # TODO: Figure out if there are some checks left to do.
    lsig_pyteal = Seq(
        Assert(
            Txn.type_enum() == TxnType.Payment,
            Txn.amount() == Int(0),
            Txn.fee() == Global.min_txn_fee(),
            Txn.close_remainder_to() == Bytes(sender),
            Txn.first_valid() >= Int(min_block_refund),
            Txn.last_valid() <= Int(max_block_refund),
        ),
        Approve(),
    )

    lsig_teal = compileTeal(lsig_pyteal, Mode.Signature, version=2)

    return LogicSigAccount(base64.b64decode(node_client.compile(lsig_teal)["result"]))
