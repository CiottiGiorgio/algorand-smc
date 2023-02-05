from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Payment(_message.Message):
    __slots__ = ["cumulativeAmount", "lsigSignature"]
    CUMULATIVEAMOUNT_FIELD_NUMBER: _ClassVar[int]
    LSIGSIGNATURE_FIELD_NUMBER: _ClassVar[int]
    cumulativeAmount: int
    lsigSignature: bytes
    def __init__(self, cumulativeAmount: _Optional[int] = ..., lsigSignature: _Optional[bytes] = ...) -> None: ...

class SMCMethod(_message.Message):
    __slots__ = ["method"]
    class MethodEnum(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    METHOD_FIELD_NUMBER: _ClassVar[int]
    PAY: SMCMethod.MethodEnum
    SETUP_CHANNEL: SMCMethod.MethodEnum
    method: SMCMethod.MethodEnum
    def __init__(self, method: _Optional[_Union[SMCMethod.MethodEnum, str]] = ...) -> None: ...

class setupProposal(_message.Message):
    __slots__ = ["maxRefundBlock", "minRefundBlock", "nonce", "sender"]
    MAXREFUNDBLOCK_FIELD_NUMBER: _ClassVar[int]
    MINREFUNDBLOCK_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    maxRefundBlock: int
    minRefundBlock: int
    nonce: int
    sender: str
    def __init__(self, sender: _Optional[str] = ..., nonce: _Optional[int] = ..., minRefundBlock: _Optional[int] = ..., maxRefundBlock: _Optional[int] = ...) -> None: ...

class setupResponse(_message.Message):
    __slots__ = ["lsigSignature", "recipient"]
    LSIGSIGNATURE_FIELD_NUMBER: _ClassVar[int]
    RECIPIENT_FIELD_NUMBER: _ClassVar[int]
    lsigSignature: bytes
    recipient: str
    def __init__(self, recipient: _Optional[str] = ..., lsigSignature: _Optional[bytes] = ...) -> None: ...
