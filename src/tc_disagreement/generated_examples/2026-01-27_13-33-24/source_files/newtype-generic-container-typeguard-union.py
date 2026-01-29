from typing import NewType, TypeGuard, Any, TypeVar, List, Union

OrderID = NewType('OrderID', int)
SKU = NewType('SKU', str)

T = TypeVar('T')

# A generic list that can hold either OrderIDs or SKUs.
# This tests NewType with generic containers and TypeGuards across a Union type.
MixedIDList = List[Union[OrderID, SKU]]

def is_list_of_order_ids(items: List[Any]) -> TypeGuard[List[OrderID]]:
    """TypeGuard for a list of OrderIDs."""
    # At runtime, OrderID is just int. Type checkers need to distinguish.
    return all(isinstance(x, int) for x in items)

def is_list_of_skus(items: List[Any]) -> TypeGuard[List[SKU]]:
    """TypeGuard for a list of SKUs."""
    # At runtime, SKU is just str. Type checkers need to distinguish.
    return all(isinstance(x, str) for x in items)

def process_mixed_ids(ids: MixedIDList) -> None:
    print(f"Processing: {ids}")
    # This branch tests narrowing from MixedIDList to List[OrderID]
    if is_list_of_order_ids(ids):
        # 'ids' should now be List[OrderID]
        first_id: OrderID = ids[0] # Expected: fine
        print(f"  First OrderID: {first_id + 100}") # OrderID supports int operations
    # This branch tests narrowing from MixedIDList to List[SKU]
    elif is_list_of_skus(ids):
        # 'ids' should now be List[SKU]
        first_sku: SKU = ids[0] # Expected: fine
        print(f"  First SKU: {first_sku.upper()}") # SKU supports str operations
    else:
        print("  Could not narrow the list to a specific ID type.")

if __name__ == "__main__":
    order_list: MixedIDList = [OrderID(1), OrderID(200)]
    process_mixed_ids(order_list)

    sku_list: MixedIDList = [SKU("ITEM1"), SKU("ITEM2")]
    process_mixed_ids(sku_list)

    mixed_list_actual: MixedIDList = [OrderID(10), SKU("PRODUCTA")]
    process_mixed_ids(mixed_list_actual) # Should hit 'else' branch

    # Crucial test: plain list of ints/strs.
    # At runtime, `is_list_of_order_ids` will return True for `plain_ints`.
    # How do checkers handle `plain_ints` being narrowed to `List[OrderID]`?
    plain_ints: List[int] = [300, 400]
    if is_list_of_order_ids(plain_ints):
        # reveal_type(plain_ints) # Expected: List[OrderID]
        x: OrderID = plain_ints[0] # Should be valid if correctly narrowed
        print(f"Plain ints narrowed to OrderID: {x}")
        # x.upper() # Expected: Type error, as OrderID is int.