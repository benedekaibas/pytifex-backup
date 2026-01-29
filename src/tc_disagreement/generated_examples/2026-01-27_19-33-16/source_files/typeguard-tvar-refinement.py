from typing import TypeGuard, List, Union, TypeVar, Any

# T is now constrained to be a numeric type.
# The TypeGuard's return `TypeGuard[List[T]]` means that `data` should be a List of this constrained T.
# However, the TypeGuard's *implementation* only checks for `int`.
# This creates a potential ambiguity:
# - When `are_all_ints_in_union_list_constrained` returns True, `data` contains only ints.
# - So, `T` *should* be narrowed to `int` for maximum precision.
# - But `T` is defined as `bound=Union[int, float]`. Will type checkers infer `T=int` (refinement)
#   or `T=Union[int, float]` (sticking to the bound)?
# - If `T` is inferred as `Union[int, float]`, then the return TypeGuard is `TypeGuard[List[Union[int, float]]]`,
#   which is less specific than `List[int]` and might lead to subtle errors later.
# - Some checkers might correctly refine `T` to `int` based on the body of the guard.
# - Others might stick to the TypeVar's bound or have difficulty unifying the generic types,
#   leading to different inferred types or even errors at the call site.
T = TypeVar('T', bound=Union[int, float])  # T is bound to numeric types
U = TypeVar('U')  # U is for other types in the union

class MyObj:
    def __init__(self, value: Any):
        self.value = value

    def __repr__(self) -> str:
        return f"MyObj({self.value})"

# A TypeGuard that checks if all elements in a list of Unions are of a specific type (int).
# The TypeGuard is defined generically with `T` (constrained) and `U`.
def are_all_ints_in_union_list_constrained(data: List[Union[T, U]]) -> TypeGuard[List[T]]:
    # This function checks if all elements are strictly `int`.
    # If it returns True, it implies that the 'T' in `List[T]` should logically be `int`.
    # The divergence lies in whether type checkers perform this logical refinement of `T`.
    return all(isinstance(x, int) for x in data)

# MODIFICATION:
# The original `process_items` function's argument type `List[Union[int, str, MyObj]]`
# caused all type checkers to fail immediately. This happened because `T` (bound to `Union[int, float]`)
# could not be inferred to include `str` or `MyObj` without violating its bound,
# even though these types could theoretically be assigned to `U`. Type checkers often
# struggle to infer the correct split of a union into `Union[T, U]` when `T` has a bound
# and `U` is unconstrained.
#
# By changing the argument type to `List[Union[int, float, Any]]`, we resolve the
# initial type error. This allows `T` to be inferred as `Union[int, float]` (satisfying its bound)
# and `U` to be inferred as `Any`.
#
# This modification unblocks the type checkers to reach the intended point of divergence:
# whether `T` will be refined to `int` (matching the `isinstance` check) or remain `Union[int, float]`
# (sticking to its original bound) after the TypeGuard returns True.
def process_items(items: List[Union[int, float, Any]]) -> None:
    if are_all_ints_in_union_list_constrained(items):
        # After narrowing, 'items' should ideally be List[int].
        # If 'T' is refined to 'int', this multiplication is safe.
        # If 'T' is 'Union[int, float]', this is also safe but less precise.
        print("All items are integers:", [x * 2 for x in items])
        reveal_type(items) # Crucial reveal_type to observe the narrowed type
    else:
        print("Not all items are integers:", items)

if __name__ == "__main__":
    list1: List[Union[int, float, Any]] = [1, 2, 3, "four"]
    process_items(list1)

    list2: List[Union[int, float, Any]] = [10, 20, 30]
    process_items(list2)

    list3: List[Union[int, float, Any]] = [100, MyObj("test")]
    process_items(list3)

    # This is the key divergence point:
    # A list declared with int|float, but at runtime contains only ints.
    all_ints_numeric_list: List[Union[int, float]] = [1, 2, 3]
    reveal_type(all_ints_numeric_list) # Expect List[Union[int, float]]

    if are_all_ints_in_union_list_constrained(all_ints_numeric_list): # This will return True
        # Divergence Expected:
        # - Some checkers might narrow `all_ints_numeric_list` to `List[int]` (correct refinement).
        # - Others might narrow it to `List[Union[int, float]]` (sticking to T's bound).
        reveal_type(all_ints_numeric_list) # THIS is the critical reveal_type for divergence
        print("All items in numeric list are integers:", [x * 2 for x in all_ints_numeric_list])
    else:
        # This branch should not be taken for `all_ints_numeric_list`
        print("Error: This branch should not be taken.")

    # Another list with int|float, but containing a float.
    mixed_numeric_list: List[Union[int, float]] = [1, 2, 3.0]
    reveal_type(mixed_numeric_list) # Expect List[Union[int, float]]
    if are_all_ints_in_union_list_constrained(mixed_numeric_list): # This will return False
        reveal_type(mixed_numeric_list) # Should not narrow here
        print("Error: This branch should not be taken for mixed_numeric_list")
    else:
        print("Not all numeric items are integers (contains float):", mixed_numeric_list)

    # Test for the scenario where the original input type (now `List[Union[int, float, Any]]`)
    # actually contains only integers.
    original_items_all_ints: List[Union[int, float, Any]] = [1, 2, 3]
    reveal_type(original_items_all_ints) # Expect List[Union[int, float, Any]]
    if are_all_ints_in_union_list_constrained(original_items_all_ints):
        # Similar divergence expected here as with `all_ints_numeric_list`.
        reveal_type(original_items_all_ints) # Expect List[int] or List[Union[int, float]] or List[Union[int, float, Any]]
        print("Original items type, all integers:", [x * 2 for x in original_items_all_ints])
    else:
        print("Error: This branch should not be taken for original_items_all_ints")