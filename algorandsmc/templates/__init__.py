"""
Flatten template import structure.
"""
from .lsig import smc_lsig_refund, smc_lsig_settlement
from .msig import smc_msig
from .txn import smc_txn_refund, smc_txn_settlement

__all__ = [
    "smc_lsig_settlement",
    "smc_lsig_refund",
    "smc_msig",
    "smc_txn_settlement",
    "smc_txn_refund",
]
