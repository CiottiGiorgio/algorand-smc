import asyncio

import websockets
from algosdk.encoding import is_valid_address

from algorandsmc.sigtemplates import smc_lsig, smc_msig
from algorandsmc.smc_pb2 import setupProposal, SMCMethod, setupResponse

RECIPIENT_ADDR = "QPKVS55LXLVR5AGHLE4B5T5HTXJSFP5ZBVEWVN5DGPC4FV267AVU35ZZEI"


async def setup_channel(websocket):
    setup_proposal = setupProposal.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_proposal.sender):
        raise ValueError

    proposed_msig = smc_msig(setup_proposal.sender, RECIPIENT_ADDR, setupProposal.nonce, setupProposal.minRefundBlock, setupProposal.maxRefundBlock)
    # TODO: Se proposed_msig esiste già nella memoria del recipient, non può essere riutilizzato per un nuovo setup.
    proposed_lsig = smc_lsig(setup_proposal.sender, setupProposal.minRefundBlock, setupProposal.maxRefundBlock)
    # TODO: Figure out if there are any checks necessary at this point for the recipient.

    # Recipient needs to:
    # - Compile msig (done)
    # - Compile lsig
    # - Sign lsig with RECIPIENT_ADDR private key
    # - Send back a setupResponse
    await websocket.send(setupResponse(recipient=RECIPIENT_ADDR, lsigSignature=...))

    print(setup_proposal)


async def receive_payment(websocket):
    pass


async def recipient(websocket):
    method: SMCMethod = SMCMethod.FromString(await websocket.recv())
    match method.method:
        case SMCMethod.MethodEnum.SETUP_CHANNEL:
            await setup_channel(websocket)
        case SMCMethod.MethodEnum.PAY:
            await receive_payment(websocket)


async def main():
    async with websockets.serve(recipient, "localhost", 55000):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
