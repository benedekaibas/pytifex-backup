from typing import TypeVar, Generic, List, reveal_type

# A TypeVar bound by a generic type
T_IntList = TypeVar("T_IntList", bound=List[int])

class Box(Generic[T_IntList]):
    """
    A generic class that holds an item of type T_IntList, which is bound to List[int].
    """
    def __init__(self, item: T_IntList) -> None:
        self.item = item

    def get_first_element(self) -> int:
        # This operation is valid if self.item is treated as List[int]
        # but problematic if it's strictly considered T_IntList without proper inference.
        return self.item[0]

# Problematic specialization: trying to use the TypeVar itself as the concrete type argument.
# Some checkers might treat `Box[T_IntList]` as a valid "unspecialized" form
# while others might flag `T_IntList` as not satisfying its own bound `List[int]`
# when used as a direct type argument this way.
ConfusingBoxType = Box[T_IntList]

def check_box(box_instance: ConfusingBoxType[T_IntList]) -> int:
    """
    Function using the `ConfusingBoxType` alias.
    Type checkers might disagree on the inferred type of `box_instance.item`.
    """
    # Is box_instance.item correctly understood as List[int] or still T_IntList?
    # Expected: T_IntList, which implicitly allows list operations due to its bound.
    reveal_type(box_instance.item) # DISAGREEMENT POINT
    return box_instance.get_first_element()

if __name__ == "__main__":
    my_data: List[int] = [10, 20]
    concrete_box: Box[List[int]] = Box(my_data)

    # Calling `check_box` with a concrete `Box[List[int]]`.
    # Does `Box[List[int]]` correctly satisfy `ConfusingBoxType[T_IntList]`?
    # This is where type checkers might diverge.
    result = check_box(concrete_box)
    print(f"Result from check_box: {result}")

    # Attempting to instantiate directly with the TypeVar (expected error)
    # This is generally not allowed, but some checkers might process the alias differently.
    # class_level_box: Box[T_IntList] = Box(my_data) # Most checkers would correctly error here.