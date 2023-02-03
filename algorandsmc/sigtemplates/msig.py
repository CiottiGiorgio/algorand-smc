from algosdk.transaction import Multisig
from algosdk.v2client.algod import AlgodClient


def smc_msig(sender_addr, recipient_addr, nonce, min_block_refund, max_block_refund) -> Multisig:
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
    :return: address of the multisignature account shared between Alice and Bob with the shared arguments
    """
    # Sandbox node
    node_client = AlgodClient("a" * 64, "http://localhost:4001")

    # Derive C's address.
    # This code always fails because it terminates with more than one element on the stack.
    teal = "\n".join([
        f"int {nonce}",
        f"int {min_block_refund}",
        f"int {max_block_refund}",
        f"int 0"
    ])
    contract_addr = node_client.compile(teal)["hash"]

    return Multisig(1, 2, [sender_addr, recipient_addr, contract_addr])
