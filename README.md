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
Namely, they are unidirectional, it's hard/costly to reset them, and they involve only two parties.
Nevertheless, they can still allow two parties to transact without any knowledge ahead-of-time.
Meaning that they don't need to know how many payments are going to be exchanged, and they don't
need to know when these payments will be executed.
Also, the implementation takes an interesting shape on Algorand because of the difference in the
primitives provided by its Layer-1.

Instead of `UTXO`, `Timelocks` and `Script language`, we have a rich Algorand Layer-1 feature set that we can leverage.
This implementation makes use of `native msig accounts`, `Logic Signatures (lsig)`, `firstBlock`, `lastBlock`, `closeTo` and `TEAL language`.

## Design
### Multisignature
We would also like to have as many active channels between the two parties that can be
customized in the amount of initial funding during setup, minimum and maximum lifetime of the channel.

For this reason, we use 2-out-of-3 Algorand Layer-1 msig accounts shared between A (sender), B (recipient) and C (parameter address).
C should be an address that is inert and can never possibly interfere with the coordination
between A and B. We choose a Smart Signature Account (aka contract account) programmed to
always reject upon being asked to sign any kind of transaction.
There are virtually an infinite number of msig accounts shared between A and B with this technique.
Also, the address of this contract account is essentially the hash of the program.
We inject setup parameters into the program to make it easy to detect already open channels
instead of using random bytes.

Since there are a lot of signatures involved, a msig that has not yet reached the end of
its lifetime shouldn't be accepted by the recipient. Deriving the msig address and checking
against a local database is easy to do.

### LogicSignature
Alice's payments to Bob happens through the use of a lsig. Alice signs a delegation to submit a transaction with
 Bob as the recipient, Alice as the closeout and the amount defined in the latest lsig.

Alice's refund condition also happens through the use of a lsig.
The msig account must delegate the authority executing the refund transaction to Alice alone. Following Algorand terminology, msig becomes a delegating account and Alice the
delegated account.

These lsigs are TEAL code signed by the msig account
 (in turn, both Alice and Bob since they are the participants of the msig).

### Communication protocol
Both parties should exchange as little information as possible in the Layer-2.
That's why both parties have access to a template library within this package that they can
use to derive the Layer-1 primitives starting from the agreed upon parameters of the SMC.

- Alice initiates the setup by sending Bob `(nonce: int, min_block_refund: int, max_block_refund: int)`.
- Bob must validate, according to his own knowledge of the Layer-1, that
the parameters of the setup are reasonable.
- Bob has enough information to derive `(C address, msig, lsig)`.
- Bob signs his part of the refund lsig and sends `(Bob's signature of lsig, Bob's public address)`.
- Alice now has all information to derive `(C, msig, lsig)` on her side.
She validates that Bob's signature of lsig is valid and that the setup proposal has been
accepted.

Once this setup is completed, Alice can just pay Bob by signing her part of a lsig that allows Bob, some time in the future, to submit a payment w/ closeout from msig to Bob.
Close out field is used in the payment transaction to make sure that Alice gets back
whatever is left in the channel when Bob closes it.
Bob can accept these lsigs and, at some point, sign the highest value transaction, send it to the network and close the channel.
Bob should always verify in the Layer-1 that the cumulative amount that he has received,
is at most the current balance of the msig address.

Alice can also sign a transaction with the shared lsig to unilaterally close the channel and be refunded if Bob is not cooperating.
Although it should be noted that the lsig allows _only_ Alice to be refunded, Bob does not own a fully signed lsig.
By the same token, Alice signs payments _only_ to Bob but does not own a fully signed payment transaction.
