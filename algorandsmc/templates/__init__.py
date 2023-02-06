"""
Flatten template import structure.
"""
from .lsig import smc_lsig_pay, smc_lsig_refund
from .msig import smc_msig

__all__ = ["smc_lsig_refund", "smc_lsig_pay", "smc_msig"]
