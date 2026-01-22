# id: newtype-list-covariance
# category: newtype-containers
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import NewType, List, Tuple

# Define NewTypes based on built-in types.
UserID = NewType('UserID', int)
OrderID = NewType('OrderID', str)

# A function expecting a list of the base type (int).
def process_int_list(data: List[int]) -> None:
    print(f"Processing integers: {data}")

# A function expecting a tuple of the base type (str).
def process_str_tuple(data: Tuple[str, ...]) -> None:
    print(f"Processing strings: {data}")

if __name__ == "__main__":
    # Create instances of generic containers using NewTypes.
    user_id_list: List[UserID] = [UserID(101), UserID(102)]
    order_id_tuple: Tuple[OrderID, ...] = (OrderID("ORD_001"), OrderID("ORD_002"))

    # DIVERGENCE POINT 1: List Covariance
    # `List` is covariant in its type parameter. Therefore, `List[UserID]` should be
    # assignable to `List[int]`, because `UserID` is a subtype of `int`.
    # Mypy correctly handles this. Other type checkers might be stricter and
    # flag an error, treating `NewType` as too distinct from its base type
    # within generic contexts.
    print("--- Testing List Covariance ---")
    process_int_list(user_id_list) # mypy: ok, others: error

    # DIVERGENCE POINT 2: Tuple Covariance
    # `Tuple` is also covariant. `Tuple[OrderID, ...]` should be assignable to
    # `Tuple[str, ...]`. Similar to List, this tests the type checker's
    # understanding of `NewType` and container variance.
    print("\n--- Testing Tuple Covariance ---")
    process_str_tuple(order_id_tuple) # mypy: ok, others: error