from typing import TypeVar, TypeAliasType, Generic, Union, Optional

T = TypeVar('T')

# Recursive TypeAliasType definition.
# It refers to itself within a Union and also uses a generic class that itself is generic.
# This combines recursion, TypeAliasType, and complex generic class structures.
NestedData = TypeAliasType('NestedData', Union[T, list['NestedData[T]'], 'LinkedList[T]'], type_params=(T,))

class LinkedList(Generic[T]):
    """A generic linked list class that uses the recursive TypeAliasType."""
    def __init__(self, value: T, next_node: Optional[NestedData[T]] = None):
        self.value = value
        self.next = next_node

    def __repr__(self) -> str:
        return f"Node({self.value}, next={self.next})"

def walk_data(data: NestedData[str]) -> None:
    """Recursively walks the nested data structure."""
    if isinstance(data, list):
        print(f"List: {data}")
        for item in data:
            walk_data(item)
    elif isinstance(data, LinkedList):
        print(f"LinkedList Node: {data.value}")
        if data.next:
            walk_data(data.next)
    else:
        print(f"Leaf Value: {data}")

if __name__ == "__main__":
    # Example usage with string types
    list_tail: NestedData[str] = LinkedList("tail", None)
    list_mid: NestedData[str] = LinkedList("mid", list_tail)
    list_head: NestedData[str] = LinkedList("head", list_mid)

    complex_structure: NestedData[str] = [
        "start",
        list_head,
        ["nested_list_item", LinkedList("final_node")]
    ]

    print("Walking complex structure:")
    walk_data(complex_structure)

    # Test type safety: what if we introduce a non-str where str is expected?
    # This should be a type error, but recursive aliases can make it hard to check.
    bad_structure: NestedData[str] = ["good", LinkedList("also_good", ["bad_int", LinkedList(123)])] # Expected: Type error on 123 (int)
    print(f"\nBad structure (should have type error): {bad_structure}")