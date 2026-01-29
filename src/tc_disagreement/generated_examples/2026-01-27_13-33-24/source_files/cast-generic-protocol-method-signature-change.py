from typing import Protocol, TypeVar, Callable, Any, cast, List

T = TypeVar('T')
U = TypeVar('U')

class DataMapper(Protocol[T, U]):
    """
    A generic protocol for mapping data.
    Tests `cast` with a generic protocol where the implementation's method
    signature (especially default arguments) differs.
    """
    def map_data(self, source: T, *, transform_mode: str = "default") -> U: ...

class StringMapper:
    def map_data(self, source: str, *, transform_mode: str = "upper") -> str: # Different default
        if transform_mode == "upper":
            return source.upper()
        elif transform_mode == "lower":
            return source.lower()
        return source

class IntToBoolMapper:
    def map_data(self, source: int, *, transform_mode: str = "is_positive") -> bool: # Different default, different return type
        if transform_mode == "is_positive":
            return source > 0
        return False

def process_with_generic_mapper(mapper: DataMapper[Any, Any], input_data: Any) -> Any:
    """
    Takes an Any-to-Any mapper and attempts to cast it to `DataMapper[str, str]`.
    This cast is unsafe if the original `mapper` isn't compatible with `DataMapper[str, str]`.
    Mypy #20500 showed a false negative for `cast(int, str)`. This aims for a similar
    false negative with a more complex, generic target.
    """
    # This cast is the core of the test.
    # It tells the type checker to assume `mapper` is `DataMapper[str, str]`.
    str_str_mapper = cast(DataMapper[str, str], mapper)
    
    # Now call the method. If input_data is not `str`, it should fail at runtime,
    # but the type checker might not flag the cast or this subsequent call.
    result = str_str_mapper.map_data(input_data, transform_mode="upper")
    return result

if __name__ == "__main__":
    string_mapper_instance = StringMapper()
    int_bool_mapper_instance = IntToBoolMapper()

    print("--- Processing with StringMapper (compatible cast) ---")
    # This scenario is safe, as StringMapper is compatible with DataMapper[str, str].
    processed_str = process_with_generic_mapper(string_mapper_instance, "hello")
    # reveal_type(processed_str) # Expected: str, Actual: Any or U?
    print(f"String processed: {processed_str}") # HELLO

    print("\n--- Processing with IntToBoolMapper (INCOMPATIBLE CAST) ---")
    # This is the unsafe scenario. IntToBoolMapper maps `int` to `bool`.
    # `process_with_generic_mapper` attempts to cast it to `DataMapper[str, str]`.
    # The type checker should ideally flag the `cast` operation here.
    try:
        # Runtime error because `IntToBoolMapper.map_data` expects `int`,
        # but `process_with_generic_mapper` passes `input_data` (which is '123' as string in this example).
        processed_int = process_with_generic_mapper(int_bool_mapper_instance, "123") # Expected: Type Error on cast, or on call if cast is allowed.
        print(f"IntToBoolMapper processed: {processed_int}")
    except TypeError as e:
        print(f"Caught runtime TypeError (expected): {e}") # Likely from 'is_positive' expecting int
    except AttributeError as e:
        print(f"Caught runtime AttributeError (expected): {e}") # E.g., if 'source' is str and > operator fails.

    # Direct call to `IntToBoolMapper` to show its actual behavior:
    print(f"Direct IntToBoolMapper(5): {int_bool_mapper_instance.map_data(5)}") # True
    print(f"Direct IntToBoolMapper(-2): {int_bool_mapper_instance.map_data(-2)}") # False (uses default 'is_positive')