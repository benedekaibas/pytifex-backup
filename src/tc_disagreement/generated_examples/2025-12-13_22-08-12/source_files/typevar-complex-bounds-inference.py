# id: typevar-complex-bounds-inference


")
    # mypy/pyre/zuban will flag the definition of Derived.x as an error.
    # Pyright will allow it.
    demonstrate_final_override(derived_instance)
    derived_instance.x = 99 # This uses the setter on the property in Derived.
    demonstrate_final_override(derived_instance)

# EXPECTED:
#   mypy: Error: Incompatible type "ConcreteContainer"; expected "U" (or similar error on `cont.get_value()` if U's generic parameter is lost)
#   pyright: No error
#   pyre: Error: Incompatible parameter type [6]: Expected `U` (bound to `Container[Animal]`) but got `ConcreteContainer` (or similar)
#   zuban: No error (likely handles complex bounds and inference well)
# REASON: Mypy and Pyre can sometimes struggle with complex `TypeVar` bounds, especially when nested generics are involved or when a `TypeVar` is bounded by another generic type that itself has specific type arguments. This can lead to issues inferring the precise type of `cont` within `process_container`, potentially losing the specific generic type argument (e.g., `Dog` or `Cat`) and defaulting to the bound (`Animal`), which can then cause errors when attempting to access specific methods or attributes. Pyright and Zuban are generally more robust in preserving and inferring specific generic type arguments through complex `TypeVar` bounds.
from typing import TypeVar, Generic, Any

class Animal:
    def speak(self) -> str: return "..."
class Dog(Animal):
    def speak(self) -> str: return "Woof!"
    def fetch(self) -> str: return "Ball!"
class Cat(Animal):
    def speak(self) -> str: return "Meow."
    def purr(self) -> str: return "Purrrr"

T_Animal = TypeVar('T_Animal', bound=Animal)

class Container(Generic[T_Animal]):
    def __init__(self, value: T_Animal) -> None:
        self.value = value
    def get_value(self) -> T_Animal:
        return self.value

class DogContainer(Container[Dog]):
    def __init__(self, dog: Dog) -> None:
        super().__init__(dog)
    def bark(self) -> str:
        return self.value.speak() # Accessing Dog's specific method implicitly

# U is a TypeVar bound to a generic Container whose T_Animal parameter is Animal.
# This means U can be Container[Animal], DogContainer, CatContainer, etc.
U = TypeVar('U', bound=Container[Animal])

def process_container(cont: U) -> None:
    """Processes a container whose value is an Animal or a subclass."""
    print(f"\n