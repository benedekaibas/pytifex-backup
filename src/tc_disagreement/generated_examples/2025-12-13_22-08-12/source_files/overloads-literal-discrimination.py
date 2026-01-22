# id: overloads-literal-discrimination


")
    return processor.process()

if __name__ == "__main__":
    sp = StringProcessor("hello")
    result = sp.process()
    print(f"Final StringProcessor result: {result}")

    # Test with generic function.
    # If type arguments for `super()` are lost, `use_processor` might have issues.
    generic_proc = StringProcessor("world")
    generic_result = use_processor(generic_proc)
    print(f"Generic processed result: {generic_result}")

# EXPECTED:
#   mypy: No error. `reveal_type(result1)` is `bool`. `reveal_type(result2)` is `bool`. `reveal_type(result3)` is `str`.
#   pyright: No error. `reveal_type(result1)` is `Literal[True]`. `reveal_type(result2)` is `Literal[False]`. `reveal_type(result3)` is `str`.
#   pyre: No error. `reveal_type(result1)` is `bool`. `reveal_type(result2)` is `bool`. `reveal_type(result3)` is `str`.
#   zuban: No error. `reveal_type(result1)` is `Literal[True]`. `reveal_type(result2)` is `Literal[False]`. `reveal_type(result3)` is `str`.
# REASON: Mypy and Pyre often resolve `Literal[True]` and `Literal[False]` to `bool` in overload resolution for simplicity, especially when the return type is `bool`. Pyright and Zuban are generally more precise, preserving the `Literal` type if the return type of the specific overload is a `Literal` itself, or if the `Literal` input directly maps to a `Literal` output, which can be useful for further narrowing or `TypeGuard` scenarios. This example specifically uses `bool` as the return type for Literal strings "true"/"false", hence pyright/zuban give `Literal[True/False]` as a more precise form of `bool`.
from typing import overload, Literal, Union

@overload
def parse(value: Literal["true"]) -> Literal[True]: ...
@overload
def parse(value: Literal["false"]) -> Literal[False]: ...
@overload
def parse(value: Literal["null"]) -> Literal[None]: ...
@overload
def parse(value: str) -> str: ... # General case for any other string

def parse(value: str) -> Union[Literal[True], Literal[False], Literal[None], str]:
    """Parses specific string literals to their corresponding Python types."""
    if value == "true": return True
    if value == "false": return False
    if value == "null": return None
    return value

if __name__ == "__main__":
    result1 = parse("true")
    reveal_type(result1) # Mypy/Pyre: bool, Pyright/Zuban: Literal[True]

    result2 = parse("false")
    reveal_type(result2) # Mypy/Pyre: bool, Pyright/Zuban: Literal[False]

    result3 = parse("hello")
    reveal_type(result3) # All: str

    result4 = parse("null")
    reveal_type(result4) # Mypy/Pyre: None, Pyright/Zuban: Literal[None]

    # Demonstrate usage based on inferred type
    if result1 is True:
        print("result1 is indeed True!")
    if result2 is False:
        print("result2 is indeed False!")
    if isinstance(result3, str):
        print(f"result3 is a string: {result3}")
    if result4 is None:
        print("result4 is indeed None!")

# EXPECTED:
#   mypy: Error: Cannot override Final attribute "x" with a property (in Derived)
#   pyright: No error
#   pyre: Error: Incompatible override (might not recognize Final on attribute as blocking property)
#   zuban: Error: Cannot override Final attribute "x" (likely similar to mypy)
# REASON: Mypy and Zuban treat `Final` very strictly, considering that a `Final` attribute in a base class cannot be overridden by any member (including a property) in a derived class because it would violate the immutability constraint. Pyright is more lenient, sometimes distinguishing between a `Final` *attribute* (a data descriptor) and a `property` (a non-data descriptor with `fget`/`fset`/`fdel` methods), seeing it as an override of a member name rather than a direct re-assignment of a final value.
from typing import Final

class Base:
    x: Final[int] = 1
    y: int = 10

    def __init__(self, val: int = 0) -> None:
        # mypy would warn if self.x was assigned here after class-level Final
        pass

class Derived(Base):
    # This attempts to override 'x' which is Final in Base.
    # Checkers disagree on whether a property can override a Final attribute.
    @property
    def x(self) -> int:
        print("Accessing Derived.x property")
        return 2

    @x.setter
    def x(self, value: int) -> None:
        print(f"Setting Derived.x property to {value}")
        # In a real scenario, this would update an internal state
        # For demonstration, we just print.

    # This is a normal override, no Final involved, all agree it's fine.
    y: int = 20

def demonstrate_final_override(obj: Base) -> None:
    print(f"Value of x: {obj.x}") # Accessing the property or attribute
    print(f"Value of y: {obj.y}")

if __name__ == "__main__":
    base_instance = Base()
    derived_instance = Derived()

    print("