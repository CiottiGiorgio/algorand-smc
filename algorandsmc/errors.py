"""
This file implements custom errors for Algorand SMC.
"""
from abc import ABC


class SMCBase(ABC, Exception):
    """Abstract Base Class for all exceptions related to Algorand SMC"""


class SMCBadSetup(SMCBase):
    """Exception raised if setup fails"""


class SMCBadSignature(SMCBase):
    """Exceptions raised if a signature cannot be apposed to the related Layer-1 primitive"""


class SMCBadFunding(SMCBase):
    """Exception raised if the msig cannot uphold the payment assumption"""


class SMCCannotBeRefunded(SMCBase):
    """
    Exception raised if the msig was correctly settled before the refund condition
     became online.
    """
