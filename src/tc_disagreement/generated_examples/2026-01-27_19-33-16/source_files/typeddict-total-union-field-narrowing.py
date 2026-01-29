from typing import TypedDict, Union, Literal, List, Any

class ItemDetails(TypedDict, total=False):
    name: str
    price: Union[int, float]
    tags: List[str]
    status: Literal['available', 'out_of_stock']

def process_item(item: ItemDetails) -> None:
    # ty#2460 showed `type(x) == bool` narrowing issues.
    # Here, we're narrowing a `Union` field within a `TypedDict`
    # using `type()`. Checkers might disagree on the soundness,
    # especially since `price` is also `total=False`.
    if 'price' in item:
        if type(item['price']) == int:
            print(f"Item '{item['name']}' has integer price: {item['price'] * 2}")
        elif type(item['price']) == float:
            print(f"Item '{item['name']}' has float price: {item['price'] * 1.5}")
        else:
            print(f"Item '{item['name']}' has an unexpected price type.")
    else:
        print(f"Item '{item['name']}' has no price specified.")

    if 'status' in item and item['status'] == 'available':
        print(f"  --> '{item['name']}' is available.")
    else:
        print(f"  --> '{item['name']}' is out of stock or status unknown.")


if __name__ == "__main__":
    item1: ItemDetails = {
        'name': 'Laptop',
        'price': 1200,
        'tags': ['electronics', 'tech'],
        'status': 'available'
    }
    process_item(item1)

    item2: ItemDetails = {
        'name': 'Mouse',
        'price': 25.99,
        'status': 'out_of_stock'
    }
    process_item(item2)

    item3: ItemDetails = {
        'name': 'Keyboard',
        'tags': ['peripherals'],
    }
    process_item(item3)

    # Reveal type for a narrowed field
    if 'price' in item1 and type(item1['price']) == int:
        reveal_type(item1['price']) # Expect int, but might be Union[int, float] or Any