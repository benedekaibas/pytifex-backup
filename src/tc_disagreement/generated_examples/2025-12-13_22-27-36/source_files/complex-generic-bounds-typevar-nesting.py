# id: complex-generic-bounds-typevar-nesting
# EXPECTED:
#   mypy: No error. Mypy's recent versions have improved significantly in handling complex generic bounds.
#   pyright: No error. Pyright is generally robust in generic type inference and bound checking.
#   pyre: Error on `process_data_source(db_source)` or `reveal_type(first_data)`. Pyre might struggle to correctly resolve `T_Source`'s bound (`DataSource[T_Data]`), leading to an error when an instance of a concrete generic class is passed.
#   zuban: No error. Aims for advanced generic reasoning and correctness.
# REASON: Type checkers vary in their ability to handle complex generic bounds, especially when a `TypeVar`'s bound is itself a generic type parameterized by another `TypeVar`. This can lead to difficulties in determining subtype compatibility when an instance of a concrete generic class is passed to a function expecting such a deeply-bound `TypeVar`.

from typing import TypeVar, Generic, List, Protocol

class BaseData:
    """Base for all data objects."""
    id: int = 0

class UserData(BaseData):
    """Specific user data."""
    name: str = "anon"

class ProductData(BaseData):
    """Specific product data."""
    sku: str = "N/A"

# T_Data is bound to a base data type
T_Data = TypeVar('T_Data', bound=BaseData)

# DataSource is a generic class that manages a list of T_Data
class DataSource(Generic[T_Data]):
    def __init__(self, data_items: List[T_Data]) -> None:
        self.data_items = data_items

    def get_first(self) -> T_Data:
        return self.data_items[0]

# T_Source is a TypeVar whose bound is a DataSource that manages *any* T_Data
# This is the complex part: T_Source bound to a generic type that itself uses a TypeVar
T_Source = TypeVar('T_Source', bound=DataSource[T_Data])

def process_data_source(source: T_Source) -> None:
    """Function that processes a data source bound by T_Source."""
    first_data = source.get_first()
    print(f"Processing source. First item ID: {first_data.id}")
    reveal_type(source)      # Expected: DataSource[UserData] or DataSource[ProductData]
    reveal_type(first_data)  # Expected: UserData or ProductData

if __name__ == "__main__":
    user_data_list: List[UserData] = [UserData(id=1, name="Alice"), UserData(id=2, name="Bob")]
    user_source = DataSource(user_data_list)

    print("--- Processing UserData Source ---")
    # This is the critical call for divergence:
    # Does `user_source` (DataSource[UserData]) fit the bound `T_Source` (bound=DataSource[T_Data])?
    process_data_source(user_source) # Pyre might error here.

    product_data_list: List[ProductData] = [ProductData(id=10, sku="A123"), ProductData(id=11, sku="B456")]
    product_source = DataSource(product_data_list)

    print("\n--- Processing ProductData Source ---")
    process_data_source(product_source) # Pyre might error here too.

---

### Snippet 10: Protocol for `__call__` (Callable) with Positional vs. Keyword Arguments