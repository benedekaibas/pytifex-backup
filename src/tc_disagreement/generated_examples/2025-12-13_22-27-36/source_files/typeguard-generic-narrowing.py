# id: typeguard-generic-narrowing
# EXPECTED:
#   mypy: No error. Mypy successfully narrows `data` to `list[int]` within the `if` block. `reveal_type(data)` -> `list[int]`.
#   pyright: No error. Pyright is very strong with TypeGuard and generic narrowing. `reveal_type(data)` -> `list[int]`.
#   pyre: Error on `data.append("string")`. Pyre might not fully narrow `data` to `list[int]`, potentially leaving it as `list[Union[int, str]]` or a less specific type, thus allowing a `str` to be appended even after the guard. Or it might be conservative about the narrowing itself.
#   zuban: No error. Aims for precise TypeGuard application.
# REASON: Type checkers differ in their ability to perform precise generic narrowing, especially when a TypeGuard makes assertions about the elements of a generic container. Some might not fully propagate the narrowing to the container's type parameter, leading to issues with subsequent operations that should be restricted by the narrowed type.

from typing import TypeGuard, TypeVar, List, Union

T = TypeVar('T')

def is_all_type(val: List[object], target_type: type[T]) -> TypeGuard[List[T]]:
    """TypeGuard that checks if all elements in the list are of a specific type."""
    return all(isinstance(x, target_type) for x in val)

def process_items(data: List[Union[int, str, bool]]) -> None:
    print(f"Initial data: {data}")

    if is_all_type(data, int):
        print("  Inside 'is_all_type(int)' block.")
        # Inside this block, 'data' should be narrowed to 'list[int]'
        data.append(100) # This should be allowed by all
        reveal_type(data) # Expected: list[int]

        # Pyre might flag this if it didn't fully narrow, incorrectly thinking 'str' is still possible.
        # Or, conversely, if it fails to narrow, it might *not* flag data.append("string") below.
        # The divergence is often in what *is* allowed/disallowed due to narrowing.
        print(f"  Data after appending int: {data}")

    print("  Outside 'is_all_type(int)' block.")
    # Outside the if block, data is still List[Union[int, str, bool]]
    # This should be allowed by all.
    data.append("new string")
    print(f"  Data after appending str: {data}")

    # This should always be an error, but if Pyre *fails* to narrow,
    # it might allow appending `str` inside the `if` block, which would be a divergence.
    # The snippet demonstrates a valid operation (append int) when narrowed,
    # expecting Pyre to potentially fail on the type assertion itself,
    # or fail to narrow so that a later invalid append is not caught.
    # Let's add an *explicitly wrong* append for narrowed type.
    if is_all_type(data, str):
        data.append(123) # This should be an error for all, but TypeGuard itself is the focus.

if __name__ == "__main__":
    my_mixed_list: List[Union[int, str, bool]] = [1, 2, "three", True, 4]
    process_items(my_mixed_list)

    print("\n--- Processing all integers list ---")
    my_int_list: List[Union[int, str, bool]] = [10, 20, 30]
    process_items(my_int_list)

---

### Snippet 3: TypedDict with `Required`/`NotRequired` and `total=False` mixed semantics