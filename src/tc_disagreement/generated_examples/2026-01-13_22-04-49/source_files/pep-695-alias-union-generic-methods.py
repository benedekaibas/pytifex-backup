from typing import TypeVar, Generic, Union, List, reveal_type

T = TypeVar("T")

class GenericReader(Generic[T]):
    def __init__(self, data: List[T]):
        self._data = data
    def read_one(self) -> T:
        return self._data[0]
    def get_data_length(self) -> int:
        return len(self._data)

class StringProcessor:
    def __init__(self, prefix: str):
        self._prefix = prefix
    def process_string(self, text: str) -> str:
        return self._prefix + text.upper()
    def get_prefix_length(self) -> int:
        return len(self._prefix)

# PEP-695 style alias for a union involving a generic class
type MixedService = GenericReader[int] | StringProcessor

def operate_on_service(service: MixedService):
    """
    Operations on the `MixedService` union.
    Checkers might struggle with attribute access and method calls.
    """
    # Both classes have `get_data_length` / `get_prefix_length` but with different names.
    # What about a method that exists on one but not the other?
    # `read_one` is only on GenericReader[int].
    if isinstance(service, GenericReader):
        reveal_type(service.read_one()) # Expected int. DISAGREEMENT POINT if type is lost or error.
        reveal_type(service.get_data_length()) # Expected int
    elif isinstance(service, StringProcessor):
        reveal_type(service.process_string("abc")) # Expected str
        reveal_type(service.get_prefix_length()) # Expected int

    # What if we try to call a method that exists on one part of the union,
    # but the checker doesn't narrow effectively for the PEP-695 alias?
    # Trying to call `read_one` directly on the union.
    # This should be an error if `service` could be `StringProcessor`.
    # Some checkers might not flag this effectively for PEP-695 aliases.
    # reveal_type(service.read_one()) # DISAGREEMENT POINT: Should be error or Union[int, Any]

if __name__ == "__main__":
    reader = GenericReader([1, 2, 3])
    processor = StringProcessor("MSG: ")

    print("--- Operating on GenericReader ---")
    operate_on_service(reader)

    print("\n--- Operating on StringProcessor ---")
    operate_on_service(processor)

    print("\n--- Operating on an actual union instance ---")
    mixed_instance: MixedService = reader if True else processor
    # This direct call will fail at runtime if `mixed_instance` is `StringProcessor`.
    # Type checkers should detect this potential AttributeError.
    try:
        if isinstance(mixed_instance, GenericReader): # Explicit narrowing is fine
            reveal_type(mixed_instance.read_one())
            print(f"Read one: {mixed_instance.read_one()}")
        else:
            print("Mixed instance is StringProcessor")
    except AttributeError as e:
        print(f"AttributeError for read_one: {e}")