# id: typeguard-generic-list-narrowing
# category: typeguard-narrowing
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import TypeGuard, TypeVar, Any, Sequence

T = TypeVar('T')

def is_sequence_of_type[T](items: Sequence[Any], type_param: type[T]) -> TypeGuard[Sequence[T]]:
    """
    A TypeGuard that attempts to narrow a Sequence[Any] to Sequence[T]
    if all its elements are of the given type T.
    """
    if not items: # Empty sequence technically fits any type.
        return True
    return all(isinstance(x, type_param) for x in items)

def process_sequence(seq: Sequence[Any]) -> None:
    if is_sequence_of_type(seq, int):
        # DIVERGENCE POINT:
        # MyPy correctly narrows 'seq' to Sequence[int] inside this block.
        # Other type checkers might fail to perform this generic type narrowing,
        # especially when 'T' is inferred from `type_param`.
        # This would lead to a type error when assigning `seq[0]` to an `int`.
        first_element: int = seq[0] # This line is the divergence test.
        print(f"Sequence narrowed to int: {seq}, first element: {first_element}")
    else:
        print(f"Sequence is not exclusively of integers or is empty: {seq}")

if __name__ == "__main__":
    ints_seq: Sequence[Any] = [1, 2, 3]
    strs_seq: Sequence[Any] = ["a", "b", "c"]
    mixed_seq: Sequence[Any] = [1, "b", 3]
    empty_seq: Sequence[Any] = []

    print("--- Processing ints_seq (expected OK) ---")
    process_sequence(ints_seq)

    print("\n--- Processing strs_seq (expected to fall into else) ---")
    process_sequence(strs_seq)

    print("\n--- Processing mixed_seq (expected to fall into else) ---")
    process_sequence(mixed_seq)

    print("\n--- Processing empty_seq (expected OK) ---")
    process_sequence(empty_seq)