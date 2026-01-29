from typing import TypeVar, TypeAliasType, Protocol, Any

T = TypeVar('T')

class SupportsAddItem(Protocol[T]):
    """A generic protocol for containers that can add items."""
    def add_item(self, item: T, *, quantity: int = 1) -> None: ...

# Create a TypeAliasType that itself is a generic protocol.
# This tests how checkers handle TypeAliasType that wraps a generic Protocol,
# especially with default arguments in protocol methods.
ItemContainer = TypeAliasType('ItemContainer', SupportsAddItem[T], type_params=(T,))

class MyIntContainer:
    """A concrete implementation of SupportsAddItem[int] with a specific default."""
    def add_item(self, item: int, *, quantity: int = 5) -> None: # Different default
        print(f"Adding {quantity} of int {item} to MyIntContainer.")

class MyStrContainer:
    """A concrete implementation of SupportsAddItem[str] with the protocol's default."""
    def add_item(self, item: str, *, quantity: int = 1) -> None: # Same default as protocol
        print(f"Adding {quantity} of str '{item}' to MyStrContainer.")

def process_container(container: ItemContainer[Any]) -> None:
    """Function accepting the generic TypeAliasType."""
    # When calling add_item, which default for 'quantity' is applied by the type checker
    # if the concrete implementation has a different default?
    container.add_item("test", quantity=2) # Should be fine if T allows Any, but concrete container expects str
    container.add_item(100) # Should be fine, using protocol/implementation default

if __name__ == "__main__":
    int_cont: MyIntContainer = MyIntContainer()
    str_cont: MyStrContainer = MyStrContainer()

    # Assign concrete instances to the TypeAliasType.
    # This tests the original mypy #20531 pattern with a generic protocol.
    int_alias: ItemContainer[int] = int_cont # Mypy 20531 reported error for similar assignment.
    int_alias.add_item(42) # Should use MyIntContainer's default (5)
    int_alias.add_item(42, quantity=10) # Explicit quantity

    str_alias: ItemContainer[str] = str_cont
    str_alias.add_item("hello") # Should use MyStrContainer's default (1)

    print("\nProcessing with generic function:")
    process_container(int_cont) # Should be valid, TypeAliasType[Any] is broad
    process_container(str_cont)

    # Test for type mismatch:
    # bad_alias: ItemContainer[str] = int_cont # Expected: Type error
    # print(f"Bad alias: {bad_alias}")