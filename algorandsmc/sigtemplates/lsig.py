import base64

from algosdk.transaction import LogicSigAccount
from algosdk.v2client.algod import AlgodClient
from pyteal import compileTeal, Mode, Int, Pop, Assert, Seq, Txn, TxnType, Bytes, Global, Approve


def smc_lsig(
        sender,
        min_block_refund,
        max_block_refund
) -> LogicSigAccount:
    # Sandbox node
    node_client = AlgodClient("a" * 64, "http://localhost:4001")

    # TODO: Figure out if there are some checks left to do.
    lsig_pyteal = Seq(
        Assert(
            Txn.type_enum() == TxnType.Payment,
            Txn.amount() == Int(0),
            Txn.fee() == Global.min_txn_fee(),
            Txn.close_remainder_to() == Bytes(sender),
            Txn.first_valid() >= Int(min_block_refund),
            Txn.last_valid() <= Int(max_block_refund)
        ),
        Approve()
    )

    lsig_teal = compileTeal(lsig_pyteal, Mode.Signature, version=2)

    return LogicSigAccount(base64.b64decode(node_client.compile(lsig_teal)["result"]))
