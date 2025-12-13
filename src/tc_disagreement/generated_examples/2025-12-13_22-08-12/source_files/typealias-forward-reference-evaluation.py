# id: typealias-forward-reference-evaluation


")
    print(simple_func("David", 45))
    print(simple_func(name="Eve", age=50))

# EXPECTED:
#   mypy: No error. `reveal_type(x)` in `add_one` is `int`.
#   pyright: No error. `reveal_type(x)` in `add_one` is `int`.
#   pyre: Error: Undefined name `Numeric` (or similar, due to strict evaluation of TypeAlias).
#   zuban: No error. `reveal_type(x)` in `add_one` is `int`.
# REASON: Pyre historically has a stricter and sometimes problematic interpretation of `TypeAlias` when used with forward references (stringified types), particularly when the alias itself is defined *after* its initial definition site but before its full resolution in the code. Mypy, Pyright, and Zuban are generally more lenient and able to resolve these forward references correctly, especially with `TypeAlias` introduced in Python 3.10. The `TypeAlias` decorator implies a full deferred evaluation, which Pyre sometimes struggles to apply consistently.
from typing import TypeAlias, Union, TYPE_CHECKING

if TYPE_CHECKING:
    # Numeric is defined as a string literal, creating a forward reference.
    # This setup (TypeAlias using string for a type declared later) is key.
    Numeric: TypeAlias = "int | float"

def add_one(x: "Numeric") -> "Numeric": # Using string literal for the alias type
    """Adds one to a numeric value."""
    print(f"Adding one to {x} (type: {type(x).__name__})")
    reveal_type(x) # Should be Union[int, float]
    return x + 1

if __name__ == "__main__":
    # Now define Numeric. Pyre might complain `Numeric` was not defined before its use in `add_one`.
    Numeric: TypeAlias = Union[int, float]

    val_int: int = 5
    val_float: float = 3.14

    result_int = add_one(val_int)
    print(f"Result int: {result_int}")
    reveal_type(result_int) # Should be Union[int, float]

    result_float = add_one(val_float)
    print(f"Result float: {result_float}")
    reveal_type(result_float) # Should be Union[int, float]

    # This assignment would also be checked
    another_val: Numeric = 10.5
    print(f"Another val: {another_val}")
    reveal_type(another_val)