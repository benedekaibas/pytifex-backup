from typing import Protocol, TypeVar, Self, override, reveal_type

T = TypeVar("T")

class BaseCloneable[T](Protocol):
    """
    Protocol with a default method returning Self, and a generic parameter T.
    """
    def __copy__(self, /) -> T:
        # Default implementation, not necessarily returning Self, but T.
        # This is fine for the protocol definition.
        ...
    
    def clone(self) -> Self: # Default method returning Self
        """Default clone implementation that simply calls __copy__."""
        return self.__copy__() # DISAGREEMENT POINT: Does T resolve to Self here?

class ConcreteCloneable(BaseCloneable[str]):
    """
    Concrete class implementing `BaseCloneable` for `str`.
    Overrides `__copy__` but uses the default `clone` method.
    """
    def __init__(self, value: str):
        self._value = value

    @override
    def __copy__(self, /) -> str:
        return self._value + "_copy"

class SubConcreteCloneable(ConcreteCloneable):
    """
    Subclass that inherits from ConcreteCloneable, thus from BaseCloneable[str].
    """
    def get_original_value(self) -> str:
        return self._value

def test_cloneable(obj: BaseCloneable[str]):
    """
    Tests the `clone` method, which is implemented by default in the protocol.
    """
    cloned_obj = obj.clone()
    reveal_type(cloned_obj) # DISAGREEMENT POINT: Expected Self (ConcreteCloneable or SubConcreteCloneable), might be BaseCloneable[str] or str.

    if isinstance(cloned_obj, ConcreteCloneable):
        # Accessing `_value` which is specific to `ConcreteCloneable`
        print(f"Cloned object value: {cloned_obj._value}")
    
    # This specific method only exists on SubConcreteCloneable
    if isinstance(cloned_obj, SubConcreteCloneable):
        print(f"Cloned object original value: {cloned_obj.get_original_value()}") # DISAGREEMENT POINT: This branch might not be correctly recognized as reachable/valid.

if __name__ == "__main__":
    c_obj = ConcreteCloneable("original")
    test_cloneable(c_obj)

    sc_obj = SubConcreteCloneable("sub_original")
    test_cloneable(sc_obj)