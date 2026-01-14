# id: bounded-typevar-nested-protocol
# category: bounded-typevars
# expected: mypy: error, pyrefly: ok, zuban: ok, ty: ok

from typing import TypeVar, Generic, Iterable, Protocol, runtime_checkable

# Define a protocol for types that must have a 'get_name' method returning a string.
@runtime_checkable
class NamedThing(Protocol):
    def get_name(self) -> str: ...

# A TypeVar whose bound is `Iterable[NamedThing]`.
# This means any type substituted for `T_NamedIterable` must be an iterable
# where *each element* satisfies the `NamedThing` protocol.
T_NamedIterable = TypeVar('T_NamedIterable', bound=Iterable[NamedThing])

# A generic function that takes an iterable of `NamedThing`s and prints their names.
def print_names[I: T_NamedIterable](data: I) -> None:
    for item in data:
        print(f"Name: {item.get_name()}")

# A class that explicitly implements the NamedThing protocol.
class MyObject:
    def __init__(self, name: str):
        self._name = name
    def get_name(self) -> str:
        return self._name

# A class that does NOT implement the NamedThing protocol (it lacks `get_name`).
class MyOtherObject:
    def __init__(self, value: int):
        self._value = value

if __name__ == "__main__":
    # Case 1: List of objects that implement NamedThing. This should pass for all.
    named_objects: list[MyObject] = [MyObject("Alpha"), MyObject("Beta")]
    print("\n--- Printing names of MyObject instances ---")
    print_names(named_objects)

    # DIVERGENCE POINT:
    # Passing a list of objects that do NOT implement `NamedThing`.
    # `MyOtherObject` does not have a `get_name` method.
    # Therefore, `list[MyOtherObject]` should NOT be compatible with
    # `Iterable[NamedThing]` according to the `T_NamedIterable` TypeVar bound.
    # Mypy correctly identifies this as a type error because `MyOtherObject` does not
    # satisfy the `NamedThing` protocol.
    # Other type checkers might be more lenient, or simply fail to perform this complex
    # nested generic bound check, allowing the code to pass statically but leading
    # to a runtime `AttributeError`.
    other_objects: list[MyOtherObject] = [MyOtherObject(1), MyOtherObject(2)]
    print("\n--- Printing names of MyOtherObject instances (EXPECTED ERROR) ---")
    print_names(other_objects) # mypy: error, others: ok.

    # An empty list satisfies the bound for any `Iterable[T]`.
    empty_list: list[NamedThing] = []
    print("\n--- Printing names of empty list ---")
    print_names(empty_list)