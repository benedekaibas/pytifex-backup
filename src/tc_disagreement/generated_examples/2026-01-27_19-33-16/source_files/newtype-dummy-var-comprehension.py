from typing import NewType, List, Tuple

ItemId = NewType('ItemId', int)
Price = NewType('Price', float)

def process_items_with_prices(items_prices: List[Tuple[ItemId, Price]]) -> None:
    # zuban#180 flagged `_ = ...` with 'Need type annotation for "_"'
    # This comprehension assigns a NewType value to `_` implicitly.
    # Checkers might disagree if `_` needs an explicit annotation here or if its type is clear.
    _ = [item_id * 2 for item_id, _ in items_prices] 
    print(f"Processed item IDs (doubled): {_[0]}...") # Accessing `_` here is bad practice, but illustrates the type

    # Another scenario where `_` is used for a NewType that isn't fully consumed.
    # The return type of `get_first_item_id` is ItemId.
    # If the checker requires `_` to be annotated, this could fail.
    try:
        def get_first_item_id() -> ItemId:
            if not items_prices:
                raise ValueError("No items")
            return items_prices[0][0]

        _ = get_first_item_id() # error: Need type annotation for "_" [var-annotated] is possible for zuban
        print(f"First item ID (via _): {_}")
    except ValueError as e:
        print(e)


if __name__ == "__main__":
    my_items: List[Tuple[ItemId, Price]] = [
        (ItemId(101), Price(10.50)),
        (ItemId(102), Price(22.00)),
        (ItemId(103), Price(5.75)),
    ]
    process_items_with_prices(my_items)

    empty_items: List[Tuple[ItemId, Price]] = []
    process_items_with_prices(empty_items)