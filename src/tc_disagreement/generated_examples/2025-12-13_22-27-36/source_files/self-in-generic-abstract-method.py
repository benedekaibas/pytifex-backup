# id: self-in-generic-abstract-method
# EXPECTED:
#   mypy: Error on `cloned_processor: StringProcessor = processor_instance.duplicate()`. Mypy might resolve `Self` in the generic context to `BaseProcessor[T]` instead of the specific concrete subclass (`StringProcessor`). `reveal_type(cloned_processor_var)` would show `BaseProcessor[str]`.
#   pyright: No error. Pyright generally handles `Self` correctly even within generic abstract methods, inferring the concrete class type. `reveal_type(cloned_processor_var)` -> `StringProcessor`.
#   pyre: Error. Pyre often struggles with complex `Self` and generics interactions, similar to mypy.
#   zuban: No error. Aims for precise type inference for `Self`.
# REASON: Type checkers differ in how they resolve the `Self` type when it's used as a return type in an abstract method within a generic class. Some might incorrectly resolve `Self` to the generic base class (e.g., `BaseProcessor[str]`), rather than the specific concrete subclass (`StringProcessor`), leading to type mismatches during assignment or further operations.

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type
from typing_extensions import Self

T = TypeVar('T')

class BaseProcessor(ABC, Generic[T]):
    """Abstract generic class for processing data."""
    def __init__(self, data: T) -> None:
        self._data = data

    @abstractmethod
    def process(self) -> T:
        """Processes the internal data."""
        ...

    @abstractmethod
    def duplicate(self) -> Self:
        """Returns a new instance of the concrete processor type, using Self."""
        # The critical point: Self should resolve to the implementing class.
        ...

class StringProcessor(BaseProcessor[str]):
    """Concrete processor for string data."""
    def process(self) -> str:
        return f"Processed: {self._data.upper()}"

    def duplicate(self) -> Self:
        # `Self` should resolve to `StringProcessor` here.
        # This factory call should return an instance of `StringProcessor`.
        print(f"Duplicating {type(self).__name__} with data '{self._data}'")
        return type(self)(self._data + " (copy)")

class IntProcessor(BaseProcessor[int]):
    """Concrete processor for integer data."""
    def process(self) -> int:
        return self._data * 2

    def duplicate(self) -> Self:
        print(f"Duplicating {type(self).__name__} with data '{self._data}'")
        return type(self)(self._data + 10)


def check_processor(processor: BaseProcessor[str]) -> BaseProcessor[str]:
    # This call demonstrates that `duplicate` *can* be called via the base type.
    # The return type should still be compatible with the base generic.
    return processor.duplicate()

if __name__ == "__main__":
    processor_instance = StringProcessor("hello")
    print(f"Original type: {type(processor_instance).__name__}")
    
    # This assignment is the key divergence point.
    # If Self resolves correctly, this is fine. If not, mypy/pyre will error.
    cloned_processor: StringProcessor = processor_instance.duplicate()
    
    print(f"Cloned type: {type(cloned_processor).__name__}")
    print(f"Cloned data: {cloned_processor._data}")
    reveal_type(cloned_processor) # EXPECTED: StringProcessor

    print("\n--- Testing IntProcessor ---")
    int_processor_instance = IntProcessor(10)
    cloned_int_processor: IntProcessor = int_processor_instance.duplicate()
    print(f"Cloned int processor type: {type(cloned_int_processor).__name__}")
    reveal_type(cloned_int_processor) # EXPECTED: IntProcessor

    print("\n--- Testing through base type hint ---")
    base_processor_ref: BaseProcessor[str] = StringProcessor("base_test")
    returned_base_processor = check_processor(base_processor_ref)
    reveal_type(returned_base_processor) # EXPECTED: BaseProcessor[str]

---

### Snippet 6: `NewType` and `List` Contravariance