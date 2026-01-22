# id: newtype-base-type-attribute-access
# EXPECTED:
#   mypy: No error (Mypy allows accessing base type members on NewType instance)
#   pyright: Error (Member "real" is not defined on type "Coordinate" [reportAttributeAccessIssue])
#   pyre: Error (Undefined attribute `real` for `Coordinate`)
#   zuban: Error (Treats NewType more nominally, disallowing direct base class attribute access)
# REASON: `NewType` creates a distinct nominal type. While it behaves like its base type at runtime, type checkers can differ on whether attributes/methods of the *base type* are directly accessible on an instance typed as the `NewType`. Mypy often allows this, treating `NewType` more structurally in this specific context (e.g., `Coordinate(10.5).real`). Pyright, Pyre, and Zuban are typically stricter, requiring a cast to the base type (`float`) before accessing such attributes, treating `Coordinate` more nominally.

from typing import NewType

# Coordinate is a NewType based on float
Coordinate = NewType('Coordinate', float)

def process_coordinate(coord: Coordinate) -> float:
    # Attempt to access an attribute/method specific to 'float' on 'Coordinate'
    # without casting it back to float.
    print(f"Original coordinate: {coord}")
    # The 'real' attribute is specific to numeric types like float
    real_part = coord.real # Divergence point
    print(f"Real part: {real_part}")
    return real_part

if __name__ == "__main__":
    my_coord: Coordinate = Coordinate(123.456)
    result = process_coordinate(my_coord)
    print(f"Result: {result}")

    # Another example: calling a method
    precision = my_coord.as_integer_ratio() # This is also a float method
    reveal_type(my_coord.as_integer_ratio) # This will show disagreement