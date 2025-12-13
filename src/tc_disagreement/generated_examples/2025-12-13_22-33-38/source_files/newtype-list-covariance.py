# id: newtype-list-covariance
# EXPECTED:
#   mypy: Error (List item type incompatible)
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy strictly enforces NewType as distinct types, even when they wrap a covariant type like list. It treats `list[NewType]` as completely separate from `list[BaseType]`, even for passing arguments. Pyright, Pyre, and Zuban can sometimes allow passing a `list[BaseType]` where `list[NewType]` is expected, as long as the base type is compatible, demonstrating a less strict approach to NewType covariance/contravariance with collections.

from typing import NewType, Union

CustomerId = NewType('CustomerId', int)
ProductId = NewType('ProductId', int)

def get_customer_orders(customer_ids: list[CustomerId]) -> list[str]:
    """Simulates fetching orders for a list of customer IDs."""
    return [f"Order for customer {cid}" for cid in customer_ids]

def process_product_data(product_ids: list[ProductId]) -> None:
    print(f"Processing products: {product_ids}")

if __name__ == "__main__":
    actual_customer_ids: list[CustomerId] = [CustomerId(101), CustomerId(102)]
    orders = get_customer_orders(actual_customer_ids) # OK for all

    # The divergence point: passing a list of the *base* type where NewType is expected
    raw_customer_ids: list[int] = [201, 202, 203]
    # Mypy typically flags this as an error. Pyright/Pyre/Zuban often allow it.
    orders_raw = get_customer_orders(raw_customer_ids) # Checkers disagree here
    reveal_type(orders_raw)

    raw_product_ids: list[int] = [10, 20]
    process_product_data(raw_product_ids) # Similar divergence point