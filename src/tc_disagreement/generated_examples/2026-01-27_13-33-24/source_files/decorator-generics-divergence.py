from typing import overload, Callable, TypeVar, ParamSpec, Generic, Any, List, ClassVar, cast

R = TypeVar('R')
P = ParamSpec('P')
T = TypeVar('T')

# A generic decorator that tracks calls.
# It wraps functions, passing through their arguments and return types.
def call_tracker(func: Callable[P, R]) -> Callable[P, R]:
    """A decorator that tracks calls to the wrapped function."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # ty currently reports an unresolved-attribute error on func.__qualname__ here.
        print(f"Tracker: {func.__qualname__} called with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

class DataProcessor(Generic[T]):
    # ORIGINAL: _processed_items: List[T] = []
    # This declaration for a class variable within a generic class
    # was ambiguous for type checkers, as T is specific to the generic instance
    # (e.g., DataProcessor[int]) but a class variable is shared.

    # MODIFIED: Declare as ClassVar[List[Any]] to correctly represent a single, shared,
    # class-level list. This resolves the ambiguity for the class variable itself.
    # The interaction with 'cast(List[T], ...)' within the methods,
    # where a type checker might still see the underlying List[Any] type
    # despite the cast, is the target for divergence.
    _processed_items: ClassVar[List[Any]] = []

    # Overloaded classmethod definitions.
    # This tests the interaction of @overload, @classmethod, @call_tracker, and generics.
    @overload
    @classmethod
    def process(cls, item: T) -> T: ...

    @overload
    @classmethod
    def process(cls, item: List[T]) -> List[T]: ...

    @classmethod
    @call_tracker # Applying decorator to the overloaded implementation
    def process(cls, item: T | List[T]) -> T | List[T]:
        """Processes a single item or a list of items."""
        # Use cast to assert that _processed_items is treated as List[T] in this generic context.
        # This is where some type checkers (e.g., mypy) might flag an 'arg-type' error,
        # indicating they don't fully trust the cast when interacting with the original
        # List[Any] storage, even though the variable 'processed_list' is now statically List[T].
        processed_list = cast(List[T], cls._processed_items)
        if isinstance(item, list):
            processed_list.extend(item)
            return item
        else:
            processed_list.append(item)
            return item

    @classmethod
    def get_all_processed(cls) -> List[T]:
        # Same casting for retrieval.
        return cast(List[T], cls._processed_items)

if __name__ == "__main__":
    # Test with integers
    res_int = DataProcessor[int].process(10)
    # reveal_type(res_int) # Expected: int, Actual: T | List[T] | Any (potential type inference issue)
    print(f"Processed single int: {res_int}")
    print(f"All processed ints: {DataProcessor[int].get_all_processed()}")

    res_int_list = DataProcessor[int].process([20, 30])
    # reveal_type(res_int_list) # Expected: List[int], Actual: T | List[T] | Any
    print(f"Processed int list: {res_int_list}")
    print(f"All processed ints: {DataProcessor[int].get_all_processed()}")

    # Test with strings
    # Because _processed_items is now a ClassVar[List[Any]], it's a single shared list.
    # DataProcessor[str] will add to the *same* list as DataProcessor[int].
    # This demonstrates a runtime effect of the type change for the type checker.
    # The 'cast' tells the type checker to treat it as List[T] for each context.
    res_str = DataProcessor[str].process("hello")
    # reveal_type(res_str) # Expected: str
    print(f"Processed single string: {res_str}")
    print(f"All processed strings: {DataProcessor[str].get_all_processed()}") # This will also contain ints!

    res_str_list = DataProcessor[str].process(["world", "!"])
    print(f"Processed string list: {res_str_list}")
    print(f"All processed strings: {DataProcessor[str].get_all_processed()}") # Still same shared list

    # Verify that all processed items are in the same list due to ClassVar[List[Any]]
    print(f"\nAll processed items (mixed types): {DataProcessor[Any].get_all_processed()}")

    # Expected type errors:
    # 1. Passing wrong type to the generic classmethod
    # DataProcessor[int].process("bad_type") # Expected: Type Error
    # 2. Trying to call a non-existent overload
    # DataProcessor[int].process(10, 20) # Expected: Type Error (too many args)