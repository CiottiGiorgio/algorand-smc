# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: smc.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\tsmc.proto\"\\\n\tSMCMethod\x12%\n\x06method\x18\x01 \x01(\x0e\x32\x15.SMCMethod.MethodEnum\"(\n\nMethodEnum\x12\x11\n\rSETUP_CHANNEL\x10\x00\x12\x07\n\x03PAY\x10\x01\"^\n\rsetupProposal\x12\x0e\n\x06sender\x18\x01 \x01(\t\x12\r\n\x05nonce\x18\x02 \x01(\x04\x12\x16\n\x0eminRefundBlock\x18\x03 \x01(\x04\x12\x16\n\x0emaxRefundBlock\x18\x04 \x01(\x04\"9\n\rsetupResponse\x12\x11\n\trecipient\x18\x01 \x01(\t\x12\x15\n\rlsigSignature\x18\x02 \x01(\x0c\"\x1b\n\x0b\x66undingTxID\x12\x0c\n\x04txid\x18\x01 \x01(\t\":\n\tPaymentTx\x12\x18\n\x10\x63umulativeAmount\x18\x01 \x01(\x04\x12\x13\n\x0btxSignature\x18\x02 \x01(\x0c\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'smc_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _SMCMETHOD._serialized_start=13
  _SMCMETHOD._serialized_end=105
  _SMCMETHOD_METHODENUM._serialized_start=65
  _SMCMETHOD_METHODENUM._serialized_end=105
  _SETUPPROPOSAL._serialized_start=107
  _SETUPPROPOSAL._serialized_end=201
  _SETUPRESPONSE._serialized_start=203
  _SETUPRESPONSE._serialized_end=260
  _FUNDINGTXID._serialized_start=262
  _FUNDINGTXID._serialized_end=289
  _PAYMENTTX._serialized_start=291
  _PAYMENTTX._serialized_end=349
# @@protoc_insertion_point(module_scope)
