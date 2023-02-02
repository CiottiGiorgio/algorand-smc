from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class fundingTxID(_message.Message):
    __slots__ = ["txid"]
    TXID_FIELD_NUMBER: _ClassVar[int]
    txid: str
    def __init__(self, txid: _Optional[str] = ...) -> None: ...

class setupProposal(_message.Message):
    __slots__ = ["maxRefundBlock", "minRefundBlock", "nonce"]
    MAXREFUNDBLOCK_FIELD_NUMBER: _ClassVar[int]
    MINREFUNDBLOCK_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    maxRefundBlock: int
    minRefundBlock: int
    nonce: int
    def __init__(self, nonce: _Optional[int] = ..., minRefundBlock: _Optional[int] = ..., maxRefundBlock: _Optional[int] = ...) -> None: ...

class signature(_message.Message):
    __slots__ = ["sig"]
    SIG_FIELD_NUMBER: _ClassVar[int]
    sig: bytes
    def __init__(self, sig: _Optional[bytes] = ...) -> None: ...
