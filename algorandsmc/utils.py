"""
File with DRY utilities.
"""
from algosdk.v2client.algod import AlgodClient


def get_sandbox_client() -> AlgodClient:
    return AlgodClient("a" * 64, "http://localhost:4001")
