# Algorand Simple Micropayment Channels

## Disclaimer
This code is not designed to be used in any kind of production environment.
It is only a proof of concept done in the context of a CS thesis on Layer-2 solutions.

## What's an SMC?
Simple Micropayment Channels (as illustrated in [this](https://doi.org/10.1007/978-3-319-21741-3_1) article) can allow
two parties to transact in the Layer-2 with each other in a trustless manner with minimal setup and settlement
cost in the Layer-1.

In an SMC, one party is the sender and the other the recipient.
The sender locks some amount of tokens in a multi signature account on the condition that, in case of an
uncooperative recipient, they will be able to be refunded in the future.
In contrast, the recipient can observe the locked funds and the logic of the smart contract to be convinced
that he can keep accepting payments (in the form of signed transactions) until the refund condition is met.

## Why on Algorand?
Although Algorand can boast extremely cheap transaction fees, incredible speed and finality, even a small cost
multiplied by a considerable number of transaction can have an impact.
SMC, as designed in this project, suffer from the same problems that they have on Bitcoin.
Namely, it's hard/costly to reset them, and they involve only two parties.
Nevertheless, the implementation takes an interesting shape on Algorand because of the difference in the
primitives provided by its Layer-1.

Instead of `UTXO`, `Timelocks` and `Script language`, we have a rich Algorand Layer-1 feature set that we can leverage.
This implementation makes use of `native msig accounts`, `Logic Signatures (lsig)`, `firstBlock`, `lastBlock` and `TEAL language`.
