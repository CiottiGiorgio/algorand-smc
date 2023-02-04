"""
File that implements the Layer-1 multisignature account shared between sender and recipient.
"""
from algosdk.transaction import Multisig

from algorandsmc.utils import get_sandbox_algod


def smc_msig(
    sender_addr: str,
    recipient_addr: str,
    nonce: int,
    min_block_refund: int,
    max_block_refund: int,
) -> Multisig:
    """
    Returns all necessary info about a Simple Micropayment Channel given setup parameters.
    (A)lice is the sender and (B)ob the recipient. (C)ontract is the fictitious smart signature account that always
    returns false but generates a distinct address based on the SMC arguments.
    C is used to generate a multitude of msig accounts between A and B.

    :param sender_addr: Algorand address of Alice
    :param recipient_addr: Algorand address of Bob
    :param nonce: Parameter to generate multiple channels given fixed sender, recipient and block contraints
    :param min_block_refund: Minimum block for A's refund transaction to be valid
    :param max_block_refund: Last block for A's refund transaction to be valid
    :return: SDK wrapper around the multisignature account shared between Alice and Bob
    """
    # Sandbox node
    node_algod = get_sandbox_algod()

    # fmt: off
    # Derive C's address.
    # This code always fails because it terminates with more than one element on the stack.
    teal = "\n".join([
        f"int {nonce}",
        f"int {min_block_refund}",
        f"int {max_block_refund}",
        "int 0"
    ])
    # fmt: on
    contract_addr = node_algod.compile(teal)["hash"]

    return Multisig(1, 2, [sender_addr, recipient_addr, contract_addr])
