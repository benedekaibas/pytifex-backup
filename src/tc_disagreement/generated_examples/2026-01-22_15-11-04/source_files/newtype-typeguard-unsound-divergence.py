from typing import NewType, TypeGuard, Union, reveal_type, List

# Define a NewType
UserID = NewType('UserID', int)

# An unsound TypeGuard for NewType.
# This is unsound because `UserID` is a runtime alias for `int`.
# Therefore, `isinstance(val, int)` will return `True` for both plain `int` values
# and `UserID` values.
# However, the TypeGuard asserts that `val` is specifically a `UserID`.
#
# If `val` is a plain `int`, this TypeGuard will return True, but then
# incorrectly assert `val` is `UserID`.
#
# This scenario exposes divergence in how type checkers:
# 1. Detect the inherent unsoundness of the `TypeGuard`'s implementation.
# 2. Refine the type of `val` in the `if` and `else` branches.
#    - Some might trust the TypeGuard, even if unsound, and refine to `UserID`.
#    - Others might detect the unsoundness and refuse to refine, or keep `Union[int, UserID]`.
#    - If `is_userid_unsound` always effectively returns `True` for the union,
#      the `else` branch should be unreachable (`NoReturn`).
def is_userid_unsound(val: Union[int, UserID]) -> TypeGuard[UserID]:
    return isinstance(val, int)

def process_mixed_id(id_val: Union[int, UserID]) -> None:
    print(f"Processing: {id_val} (runtime type: {type(id_val)})")
    if is_userid_unsound(id_val):
        # Divergence point 1: What is the revealed type of `id_val` here?
        # - Some checkers might refine to `UserID`.
        # - Others might detect unsoundness and keep `Union[int, UserID]`, or report an error.
        reveal_type(id_val)
        print(f"  Refined to UserID: {id_val}")
    else:
        # Divergence point 2: What is the revealed type of `id_val` here?
        # Given `isinstance(val, int)` is always True for Union[int, UserID],
        # this `else` branch should theoretically be unreachable (NoReturn).
        # - Some checkers might infer `NoReturn`.
        # - Others might infer `int` (if they don't fully track the TypeGuard's runtime behavior).
        reveal_type(id_val)
        print(f"  Remains as int (should be unreachable): {id_val}")

if __name__ == "__main__":
    print("--- Test 1: Plain int ---")
    my_int = 10
    process_mixed_id(my_int)

    print("\n--- Test 2: UserID ---")
    my_userid = UserID(20)
    process_mixed_id(my_userid)

    # Further test: using it in a list context to see refinement propagation
    mixed_list: List[Union[int, UserID]] = [1, UserID(2), 3, UserID(4)]
    print("\n--- Test 3: Mixed list elements ---")
    for item in mixed_list:
        if is_userid_unsound(item):
            # Divergence point 3: Type of `item` within the loop
            reveal_type(item)
            print(f"  List item refined to UserID: {item}")
        else:
            reveal_type(item)
            print(f"  List item remains as int (should be unreachable): {item}")

    # Some checkers might also emit a warning/error directly on the definition of `is_userid_unsound`
    # due to its inherent unsoundness, which would be another form of divergence.