from typing import TypeGuard, Protocol, TypeVar, List, Union, runtime_checkable, Any

T = TypeVar('T')

@runtime_checkable
class HasMetadata(Protocol[T]):
    """A generic protocol with a metadata attribute and a processing method."""
    metadata: dict[str, str]
    def process_data(self, data: T, *, tags: List[str] = []) -> str: ... # Method with default

class SimpleProcessor:
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata
    def process_data(self, data: str, *, tags: List[str] = ["default_tag"]) -> str: # Different default
        return f"[{self.metadata.get('name', 'Anon')}/{','.join(tags)}] {data.upper()}"

class ComplexProcessor:
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata
    def process_data(self, data: int, *, tags: List[str] = []) -> str: # Same default
        return f"Complex {self.metadata.get('id', 'N/A')}: {data * 2}"

def is_string_processor(obj: Any) -> TypeGuard[HasMetadata[str]]:
    """Narrows an object to HasMetadata[str]."""
    # This check relies on runtime behavior (isinstance) but needs to correctly infer generic type.
    return isinstance(obj, HasMetadata) and isinstance(obj.process_data("test", tags=[]), str)

def process_item_with_guard(item: Union[SimpleProcessor, ComplexProcessor, Any]) -> None:
    """Processes an item using TypeGuard for narrowing."""
    if is_string_processor(item):
        # 'item' should now be HasMetadata[str]
        print(f"String processor found: {item.metadata.get('name')}")
        result = item.process_data("input_text") # Uses default tag from SimpleProcessor
        print(f"  Result: {result}")
    else:
        print(f"Not a string processor (or failed narrowing): {type(item)}")
        # Check if it's a ComplexProcessor
        if isinstance(item, ComplexProcessor):
            print(f"  It's a ComplexProcessor! Processing int: {item.process_data(10)}")

if __name__ == "__main__":
    sp = SimpleProcessor({'name': 'StringHandler'})
    cp = ComplexProcessor({'id': 'C1'})
    unknown_obj = 123

    process_item_with_guard(sp)
    process_item_with_guard(cp)
    process_item_with_guard(unknown_obj)

    # Test direct calls and default argument discrepancies
    # The protocol's default for `tags` is [], but `SimpleProcessor` uses `["default_tag"]`.
    # When called through the protocol, which default is used/checked?
    protocol_sp: HasMetadata[str] = sp
    print(f"\nCalling SimpleProcessor via protocol:")
    print(protocol_sp.process_data("direct call")) # Should use SimpleProcessor's default tag
    print(protocol_sp.process_data("direct call", tags=["explicit_tag"]))

    # Expected Type Error: passing wrong data type to a narrowed processor.
    # if is_string_processor(sp):
    #     sp.process_data(123) # Expected: Type error (int vs str)