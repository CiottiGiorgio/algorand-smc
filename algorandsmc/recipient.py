"""
File that implements all things related to the recipient side of an SMC.
"""
import asyncio

import websockets
from algosdk.account import address_from_private_key
from algosdk.encoding import is_valid_address
from algosdk.mnemonic import to_private_key

from algorandsmc.templates import smc_lsig, smc_msig

# pylint: disable-next=no-name-in-module
from algorandsmc.smc_pb2 import SMCMethod, setupProposal, setupResponse, fundingTxID

RECIPIENT_PRIVATE_KEY_MNEMONIC = (
    "question middle cube wire breeze choose rival accident disorder wood "
    "park erosion uphold shine picnic industry diagram attack magnet park "
    "evoke music auto above gas"
)
RECIPIENT_PRIVATE_KEY = to_private_key(RECIPIENT_PRIVATE_KEY_MNEMONIC)
RECIPIENT_ADDR = address_from_private_key(RECIPIENT_PRIVATE_KEY)


async def setup_channel(websocket):
    setup_proposal: setupProposal = setupProposal.FromString(await websocket.recv())
    # Protobuf doesn't know what constitutes a valid Algorand address.
    if not is_valid_address(setup_proposal.sender):
        raise ValueError

    print(setup_proposal)

    # Compiling msig template on the recipient side.
    proposed_msig = smc_msig(
        setup_proposal.sender,
        RECIPIENT_ADDR,
        setup_proposal.nonce,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    # TODO: Se proposed_msig esiste già nella memoria del recipient, non può essere riutilizzato per un nuovo setup.
    # Compiling lsig template on the recipient side.
    proposed_lsig = smc_lsig(
        setup_proposal.sender,
        setup_proposal.minRefundBlock,
        setup_proposal.maxRefundBlock,
    )
    # TODO: Figure out if there are any checks necessary at this point for the recipient.
    # Signing the lsig with the msig only on the recipient side.
    # Crucially, the lsig MUST not be signed using the recipient secret key directly.
    # That would allow the sender to close out the recipient balance in the future.
    # TODO: Create a test that validates that the lsig CANNOT be used on the recipient account in the future.
    #  Also, create a test that validates that the lsig CAN be used on the msig account in the future.
    proposed_lsig.sign_multisig(proposed_msig, RECIPIENT_PRIVATE_KEY)

    # TODO: Extract the signature of the recipient from proposed_lsig in a way that does not rely on explicit index.
    #  Although, as long as both parties compile from the same template, they should find the addresses in the same
    #  index each time and on each side.

    await websocket.send(
        setupResponse(
            recipient=RECIPIENT_ADDR,
            lsigSignature=proposed_lsig.lsig.msig.subsigs[1].signature,
        ).SerializeToString()
    )
    # At this point, the recipient does not own a correctly signed lsig because it's missing sender's signature.

    # funding_txid: fundingTxID = fundingTxID.FromString(await websocket.recv())
    # TODO: Check that the funding happened in order to start accepting SMC payments.


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
