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

    # Derive C's address.
    # We could technically just parameterize this contract with nonce alone. However, both participants in the channel
    #  would then have to associate each msig address with the channel arguments.
    # If we parameterize C with all channel arguments, its address will always be deterministically
    #  associated with the channel arguments.
    # Starting from channel arguments, deriving the address of the shared msig is basically taking
    #  the hash of the tuple (the template is constant).
    # This basically means that we can receive proposed channel arguments,
    #  derive msig address and evaluate if we already opened the channel in the past.
    # The TEAL code for C contract account always fails because it terminates with more than one element on the stack.
    # fmt: off
    teal = "\n".join([
        f"int {nonce}",
        f"int {min_block_refund}",
        f"int {max_block_refund}"
    ])
    # fmt: on
    contract_addr = node_algod.compile(teal)["hash"]

    return Multisig(1, 2, [sender_addr, recipient_addr, contract_addr])
