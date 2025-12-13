# id: typeguard-generic-narrowing
# EXPECTED:
#   mypy: Error (List item type not compatible)
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy is more conservative with TypeGuard narrowing, especially when the narrowed type is itself generic. It might not fully infer the generic parameter `T` within the list, leading to an error when modifying the list with a specific type. Pyright, Pyre, and Zuban generally handle this specific generic narrowing more robustly.

from typing import TypeGuard, TypeVar, Any

T = TypeVar('T')

def is_list_of(val: list[Any], type_: type[T]) -> TypeGuard[list[T]]:
    """Narrows a list of Any to a list of T if all elements are of type_."""
    return all(isinstance(x, type_) for x in val)

def process_data(items: list[Any]) -> None:
    if is_list_of(items, int):
        # After narrowing, 'items' should be list[int]
        items.append(123)  # Mypy might complain here
        reveal_type(items)
    else:
        items.append("fallback")

if __name__ == "__main__":
    mixed_list: list[Any] = [1, "hello", 3.0]
    process_data(mixed_list)

    int_list: list[Any] = [1, 2, 3]
    process_data(int_list)