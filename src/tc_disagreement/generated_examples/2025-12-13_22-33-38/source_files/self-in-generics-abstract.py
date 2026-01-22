# id: self-in-generics-abstract
# EXPECTED:
#   mypy: Error (Return type Self incompatible with 'StringAppender')
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy can have difficulty correctly inferring `Self` as the precise concrete type of the *implementing* class when `Self` is used within a generic abstract base class, especially if the generic type parameter `T` is also involved. It might resolve `Self` to the generic base class or another type, causing a mismatch. Pyright, Pyre, and Zuban usually handle `Self` in this context correctly.

from typing import Generic, TypeVar, Any
from typing_extensions import Self
from abc import ABC, abstractmethod

T = TypeVar('T')

class AbstractBuilder(ABC, Generic[T]):
    """Abstract builder that returns Self for chaining."""
    @abstractmethod
    def add_item(self, item: T) -> Self:
        ...

    @abstractmethod
    def build(self) -> Any:
        ...

class StringAppender(AbstractBuilder[str]):
    _parts: list[str]

    def __init__(self) -> None:
        self._parts = []

    def add_item(self, item: str) -> Self: # Checkers disagree on Self return type here
        self._parts.append(item)
        return self

    def build(self) -> str:
        return "".join(self._parts)

if __name__ == "__main__":
    builder = StringAppender().add_item("Hello").add_item(" World")
    result = builder.build()
    reveal_type(builder)
    reveal_type(result)