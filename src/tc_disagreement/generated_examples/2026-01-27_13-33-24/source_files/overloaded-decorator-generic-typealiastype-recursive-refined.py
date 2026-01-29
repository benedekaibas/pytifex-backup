import functools
from typing import TypeVar, TypeAliasType, Callable, overload, Any, Union, List

T = TypeVar('T')

# A TypeAliasType that itself is recursive and generic.
# This tests TypeAliasType's interaction with recursion, generics, and overloaded functions.
# Mypy currently fails to resolve this cyclic definition (Issue #15112, #20531 related)
NestedPayload = TypeAliasType('NestedPayload', Union[T, List['NestedPayload[T]']], type_params=(T,))

# Simple decorator (not overloaded itself)
def trace_execution(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func) # Use functools.wraps to preserve metadata for better introspection
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"TRACE: Executing {func.__name__}...")
        result = func(*args, **kwargs)
        print(f"TRACE: {func.__name__} finished.")
        return result
    return wrapper

# Overloaded function definitions using the recursive TypeAliasType.
@overload
def process_payload(data: T) -> NestedPayload[T]: ...

@overload
def process_payload(data: List[T]) -> List[NestedPayload[T]]: ...

@trace_execution # Decorating the overloaded implementation
def process_payload(data: T | List[T]) -> NestedPayload[T] | List[NestedPayload[T]]:
    """
    Processes a single item or a list of items into NestedPayload structures.
    The challenge for type checkers is correctly inferring the return type
    based on the specific overload, especially with the recursive TypeAliasType.
    Crucially, TypeAliasType is a *type*, not a constructor. A value *is* a
    NestedPayload if it conforms to its definition, it's not "wrapped".
    """
    if isinstance(data, list):
        # If `data` is List[T], then each `item` is T.
        # Since T is the base case for NestedPayload[T], List[T] is already
        # compatible with List[NestedPayload[T]].
        return data
    # If `data` is T, then it's already compatible with NestedPayload[T].
    return data

def consume_int_payload(payload: NestedPayload[int]) -> None:
    if isinstance(payload, list):
        for item in payload:
            consume_int_payload(item) # Recursive call
    else:
        print(f"  Consumed int payload: {payload + 10}") # Check int operations

if __name__ == "__main__":
    # Test single item payload
    int_single_payload = process_payload(100)
    # reveal_type(int_single_payload) # Expected: NestedPayload[int]
    print(f"Single payload: {int_single_payload}")
    consume_int_payload(int_single_payload)

    # Test list of items payload
    int_list_payload = process_payload([1, 20])
    # reveal_type(int_list_payload) # Expected: List[NestedPayload[int]]
    print(f"List payload: {int_list_payload}")
    consume_int_payload(int_list_payload)

    # Test recursive assignment with TypeAliasType (inspired by mypy #20531)
    # This should be OK if the TypeAliasType and overloads are handled correctly.
    # The return type for process_payload([10, [20, 30], 40]) with T=int would be
    # List[NestedPayload[int]], which is compatible with NestedPayload[int] (due to Union).
    recursive_payload: NestedPayload[int] = process_payload([10, [20, 30], 40])
    print(f"Recursive payload: {recursive_payload}")
    consume_int_payload(recursive_payload)

    # Expected Type Error: incompatible type in payload
    # `process_payload([10, "string", 30])` implies T = Union[int, str].
    # Return type is List[NestedPayload[Union[int, str]]].
    # This cannot be assigned to NestedPayload[int] because `Union[int, str]`
    # is not assignable to `int`.
    bad_payload: NestedPayload[int] = process_payload([10, "string", 30]) # Expected: Type Error
    print(f"Bad payload (should error for type mismatch): {bad_payload}")