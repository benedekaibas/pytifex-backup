from typing import NewType, Dict, List, Tuple, Union

ItemId = NewType('ItemId', int)
Tag = NewType('Tag', str)
Weight = NewType('Weight', float)

# Complex nested structure using NewTypes
InventoryRecord = Dict[ItemId, Tuple[List[Tag], Weight]]

def parse_inventory(data_string: str) -> InventoryRecord:
    # This simulates parsing, creating a complex nested NewType structure.
    # The multi-line assignment with a `type: ignore` on an intermediate line
    # can cause `mypy#20471` inconsistencies.
    inventory: InventoryRecord = {
        ItemId(101): (
            [Tag("Electronics"), Tag("Gadget")], # type: ignore[misc]
            # This 'type: ignore' on a partial line of the tuple element
            # is meant to suppress a potential error if a checker believes
            # Tag is incompatible with str or vice-versa in this context.
            # It should ideally apply only to the list of Tags.
            Weight(0.5)
        ),
        ItemId(102): (
            [Tag("Books")],
            Weight(1.2)
        ),
    }
    return inventory

if __name__ == "__main__":
    my_inventory = parse_inventory("dummy data")
    print(f"Inventory: {my_inventory}")

    # Another multi-line operation with `type: ignore` for a complex NewType.
    # The `type: ignore` on the second line here could be problematic if
    # it applies to the whole expression or is mis-scoped.
    total_weight: Union[float, int] = sum(
        item_data[1] for item_id, item_data in my_inventory.items() # type: ignore[attr-defined]
        # This ignore is for `item_data[1]` possibly not being iterable or having `__float__`
        # if the checker is over-strict on NewType conversion.
    )
    print(f"Total weight: {total_weight}")