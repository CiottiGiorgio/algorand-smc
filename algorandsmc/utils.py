"""
File with DRY utilities.
"""
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient


def get_sandbox_algod() -> AlgodClient:
    return AlgodClient("a" * 64, "http://localhost:4001")


def get_sandbox_indexer() -> IndexerClient:
    return IndexerClient("a" * 64, "http://localhost:8980")
