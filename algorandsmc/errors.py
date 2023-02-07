"""
This file implements custom errors for Algorand SMC.
"""
from abc import ABC


class SMCBase(ABC, Exception):
    pass


class SMCBadSetup(SMCBase):
    pass


class SMCBadSignature(SMCBase):
    pass


class SMCBadFunding(SMCBase):
    pass


class SMCCannotBeRefunded(SMCBase):
    pass
