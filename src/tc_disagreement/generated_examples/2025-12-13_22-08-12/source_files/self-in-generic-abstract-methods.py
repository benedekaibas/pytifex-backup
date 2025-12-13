# id: self-in-generic-abstract-methods


")
    return creator(Service, "Consumer-Created")

if __name__ == "__main__":
    s1 = Service.create("MyService")
    print(f"Created service instance: {s1.name}\n")

    s2_result = s1.process("input data")
    print(f"Result of processing: {s2_result}\n")

    # This call tests if the signature of Service.create is correctly preserved
    # by the decorator for downstream use as a Callable.
    # mypy/pyre might raise errors here if `Service.create`'s signature after decoration
    # is deemed incompatible with `Callable[[type[Service], str], Service]`.
    s3 = consumer(Service.create)
    print(f"Service from consumer: {s3.name}")

    reveal_type(Service.create) # This should reveal Callable[[Type[Service], str], Service]

# EXPECTED:
#   mypy: Error: Return type of "create" incompatible with supertype "AbstractFactory" (or similar error related to Self being confused with T or the generic base type)
#   pyright: No error (`create` returns `ConcreteFactory`)
#   pyre: Error: Incompatible return type for `create` (might infer `AbstractFactory[str]` or `Any` incorrectly)
#   zuban: No error (`create` returns `ConcreteFactory`)
# REASON: Mypy and Pyre can struggle to correctly resolve `Self` within a generic abstract class context, especially when the generic parameter `T` is not directly involved in the return type but the class itself is generic. Pyright and Zuban are more adept at understanding that `Self` refers to the *concrete instance type* of the class (e.g., `ConcreteFactory`), even when the base class is generic.
from typing import Generic, TypeVar, Any
from typing_extensions import Self # Python 3.11+, Self is in typing, but for broader compatibility often used from typing_extensions
from abc import ABC, abstractmethod

T = TypeVar('T')

class AbstractFactory(ABC, Generic[T]):
    @abstractmethod
    def create(self) -> Self:  # Self should refer to the concrete subclass type
        """Creates an instance of the concrete factory."""
        ...

    @abstractmethod
    def process(self, value: T) -> T:
        """Processes a value of type T."""
        ...

class ConcreteFactory(AbstractFactory[str]):
    def create(self) -> Self:
        print(f"  Creating instance of {type(self).__name__}.")
        # At runtime, Self is not a type, but type(self) is.
        # For type checking, Self here means an instance of ConcreteFactory.
        return ConcreteFactory()

    def process(self, value: str) -> str:
        return f"Processed string: {value.upper()}"

class IntFactory(AbstractFactory[int]):
    def create(self) -> Self:
        print(f"  Creating instance of {type(self).__name__}.")
        return IntFactory()

    def process(self, value: int) -> int:
        return value * 2


def make_and_use[F: AbstractFactory[Any]](factory: F, item: Any) -> tuple[F, Any]:
    """A generic function to create a factory instance and use it."""
    print(f"\n