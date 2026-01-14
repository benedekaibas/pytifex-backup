# id: self-in-generics-abstract-method
# EXPECTED:
#   mypy: No error
#   pyright: No error
#   pyre: Error (Incompatible return type [13]: Expected `Self`, got `ConcreteFactory`)
#   zuban: Error (Similar to Pyre, potentially stricter with Self in generic ABCs)
# REASON: The interaction of `Self` with generic abstract base classes, particularly in `abstractmethod` return types, can expose differences. Pyre and Zuban might struggle to correctly resolve `Self` within a concrete subclass that also instantiates a generic `ABC`, sometimes requiring `Self` to be the exact type of the enclosing class or failing to unify the generic parameter correctly. Mypy and Pyright generally handle this scenario well, inferring `Self` as the concrete subclass type.

from typing import Generic, TypeVar, Any
from typing_extensions import Self
from abc import ABC, abstractmethod

T = TypeVar('T')

class AbstractFactory(ABC, Generic[T]):
    """An abstract factory for producing objects related to type T."""
    @abstractmethod
    def create(self) -> Self: # Return type is Self
        """Creates an instance of the concrete factory type."""
        ...

class StringProcessor:
    def process(self, data: str) -> str:
        return data.upper()

class StringFactory(AbstractFactory[str]):
    """A concrete factory for strings."""
    def create(self) -> Self: # Implements create, returns Self
        print(f"Creating an instance of {type(self).__name__}")
        return self # 'self' is of type 'Self' here

class IntFactory(AbstractFactory[int]):
    """A concrete factory for integers."""
    def create(self) -> Self:
        print(f"Creating an instance of {type(self).__name__}")
        return self

def use_factory(factory: AbstractFactory[Any]) -> Self:
    """Consumes an abstract factory and returns a factory instance."""
    return factory.create()

if __name__ == "__main__":
    string_factory_instance = StringFactory()
    int_factory_instance = IntFactory()

    # The divergence occurs here in assigning the result of create()
    # to a variable typed as the specific concrete factory.
    result1: StringFactory = string_factory_instance.create() # Type checker should allow this
    result2: IntFactory = use_factory(int_factory_instance) # And this