# id: double-bound-typevar-resolution
# EXPECTED:
#   mypy: Error (Value of type variable "U" of "process_container" cannot be "DogContainer[Dog]" (or "Container[Dog]"))
#   pyright: No error (Correctly resolves the nested bounds)
#   pyre: Error (Expected type `Container[Animal]`, got `DogContainer[Dog]`)
#   zuban: Error (Similar to mypy/pyre, conservative with complex generic bounds)
# REASON: This tests the type checker's ability to resolve complex, nested `TypeVar` bounds. `U` is bound to `Container[Animal]`, meaning any type assigned to `U` must be a subclass of `Container` whose generic parameter is a subclass of `Animal`. Passing `DogContainer[Dog]` (where `Dog` is a subclass of `Animal`) *should* be valid. Pyright's type solver is typically advanced enough to correctly unify this. Mypy, Pyre, and Zuban might struggle with the double-bound resolution, failing to see `DogContainer[Dog]` as compatible with `U` due to the inner `Animal` bound on `Container`.

from typing import TypeVar, Generic, Type, Any

class Animal:
    def make_sound(self) -> str: return "..."
class Dog(Animal):
    def make_sound(self) -> str: return "Woof"
class Cat(Animal):
    def make_sound(self) -> str: return "Meow"

# T_item is bound to Animal
T_item = TypeVar('T_item', bound=Animal)

class Container(Generic[T_item]):
    def __init__(self, item: T_item):
        self.item = item
    def get_item(self) -> T_item:
        return self.item

class DogContainer(Container[Dog]):
    def __init__(self, dog: Dog):
        super().__init__(dog)
    def bark(self) -> str:
        return self.item.make_sound() # item is guaranteed to be Dog

# U is a TypeVar that is bound to a Container whose item type is at least an Animal
U = TypeVar('U', bound=Container[Animal])

def process_container(cont: U) -> None:
    """Processes a container whose inner item is an Animal."""
    print(f"Processing container with item: {cont.get_item().make_sound()}")
    # Attempt to use specific methods if the container is known
    # This part should not cause divergence, as 'cont' is 'Container[Animal]'
    # but the initial assignment to 'cont' is the divergence point.

if __name__ == "__main__":
    dog_obj = Dog()
    dog_box = DogContainer(dog_obj)

    # The divergence occurs here. Is DogContainer[Dog] assignable to U (bound=Container[Animal])?
    process_container(dog_box) # Expecting this to be type-safe
    
    cat_obj = Cat()
    cat_box = Container(cat_obj) # Container[Cat]
    process_container(cat_box) # Should also be fine