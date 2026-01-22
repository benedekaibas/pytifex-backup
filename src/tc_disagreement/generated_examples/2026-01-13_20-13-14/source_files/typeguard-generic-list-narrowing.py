# id: typeguard-generic-list-narrowing
# EXPECTED:
#   mypy: Error (Incompatible types in append: 'str'; expected 'object')
#   pyright: No error
#   pyre: Error (Cannot call `append` with an argument of type `str` when `data` is `List[object]`)
#   zuban: Error (Similar to mypy/pyre, conservative narrowing)
# REASON: Pyright's control flow analysis is typically more advanced for `TypeGuard` with generics, correctly narrowing `data` from `list[object]` to `list[T]` (where `T` is `str` in this context), allowing `append("new")`. Mypy, Pyre, and Zuban might be more conservative, retaining `list[object]` or an insufficient type for the `append` operation, preventing type `str` from being appended.

from typing import TypeGuard, TypeVar, List, Any

T = TypeVar('T')

def is_list_of(val: List[Any], type_: type[T]) -> TypeGuard[List[T]]:
    """TypeGuard to check if all elements in a list are of a specific type."""
    return all(isinstance(x, type_) for x in val)

def process(data: List[object]) -> None:
    print(f"Initial data: {data}")
    if is_list_of(data, str):
        # After this line, 'data' should be narrowed to List[str]
        data.append("new_string") # Divergence point
        print(f"Narrowed data (str): {data}")
    else:
        print(f"Data is not a list of strings: {data}")

if __name__ == "__main__":
    mixed_data: List[object] = ["hello", "world", 123]
    process(mixed_data) # Should not append due to integer

    string_data: List[object] = ["alpha", "beta"]
    process(string_data) # Should append "new_string"