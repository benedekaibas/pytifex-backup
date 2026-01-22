# id: newtype-list-contravariance
# EXPECTED:
#   mypy: Error on `return get_raw_ids()`. Mypy correctly identifies that `List[int]` cannot be assigned to `List[TransactionId]` due to NewType's strictness and list invariance (for assignment), even though `int` is the base type of `TransactionId`.
#   pyright: Error on `return get_raw_ids()`. Pyright also correctly enforces NewType and list type compatibility.
#   pyre: No error. Pyre has historically been observed to be less strict about `NewType` in collection contexts, potentially allowing `List[int]` to be compatible with `List[TransactionId]` in return positions.
#   zuban: Error. Aims for strict type safety with NewType.
# REASON: Type checkers differ in their strictness when a `NewType` (which is a nominal subtype) is involved in generic collections. While `NewType` is a subtype of its base type (`int`), a collection of the base type (`List[int]`) is not type-compatible with a collection of the `NewType` (`List[TransactionId]`). This is a subtle contravariance/invariance rule that some checkers might relax.

from typing import NewType, List, Callable, TypeVar, Any

TransactionId = NewType('TransactionId', int)
ItemId = NewType('ItemId', int)

def get_raw_ids() -> List[int]:
    """Simulates fetching raw integer IDs from a database."""
    print("Fetching raw integer IDs.")
    return [101, 102, 103, 104]

def fetch_transaction_ids() -> List[TransactionId]:
    """Function expected to return a list of TransactionId NewType."""
    # This line is the potential divergence point.
    # It attempts to return List[int] where List[TransactionId] is expected.
    # Mypy, Pyright, Zuban should flag this as an error. Pyre might not.
    return get_raw_ids()

def process_ids(ids: List[TransactionId]) -> None:
    """Processes a list of TransactionIds."""
    print(f"Processing IDs of type {type(ids[0]) if ids else 'empty'}: {ids}")
    # ids.append(200) # This should be a type error in all, as 200 is int, not TransactionId
    # ids.append(TransactionId(200)) # This is fine

if __name__ == "__main__":
    print("--- Demonstrating correct usage ---")
    strict_transactions: List[TransactionId] = [TransactionId(1), TransactionId(2)]
    process_ids(strict_transactions)

    print("\n--- Demonstrating divergence ---")
    # Calling the problematic function. The type checker divergence occurs here
    # during the return statement's assignment check.
    try_transactions = fetch_transaction_ids()
    reveal_type(try_transactions) # If no error, this reveals List[TransactionId]
    process_ids(try_transactions)

---

### Snippet 7: Overload with `Literal` Discrimination