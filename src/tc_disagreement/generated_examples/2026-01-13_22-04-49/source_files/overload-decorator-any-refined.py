from typing import overload, TypeVar, Callable, Any, reveal_type

# T is defined for the generic overload
T = TypeVar("T") 

# A simple decorator that just passes through, but could be complex
# MODIFIED: Changed decorator signature to (f: Any) -> Any.
# This weakens the decorator's type precision, which might cause some type checkers
# to infer 'Any' for decorated overloads where 'T' could otherwise be inferred.
def identity_decorator(f: Any) -> Any:
    return f

class Factory:
    _registry: dict[str, Any] = {}

    @overload
    @staticmethod
    def create(name: str) -> str: ...
    @overload
    @staticmethod
    def create(item_id: int, quantity: int) -> int: ...
    @overload
    @identity_decorator # Decorator on an overload
    @staticmethod
    def create(item_type: type[T], config: dict[str, Any]) -> T: ...
    @overload
    @staticmethod
    # MODIFIED: Replaced ParamSpec-based catch-all with standard Any-based catch-all.
    # The original ParamSpec usage was reported as "unbound" by mypy and other checkers,
    # preventing further analysis. This fixes that syntax error.
    def create(*args: Any, **kwargs: Any) -> Any: ...

    @staticmethod
    def create(*args: Any, **kwargs: Any) -> Any:
        if len(args) == 1 and isinstance(args[0], str):
            return f"Created item '{args[0]}'"
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], int):
            return args[0] * args[1]
        elif len(args) == 2 and isinstance(args[0], type) and isinstance(args[1], dict):
            # Simulate object creation
            print(f"Creating object of type {args[0].__name__} with config {args[1]}")
            return args[0]() # Simplistic instantiation
        else:
            return f"Unhandled creation request: args={args}, kwargs={kwargs}"

class Product:
    def __init__(self): self.name = "default_product"
    def get_name(self) -> str: return self.name

def test_factory():
    # Matches (name: str) -> str
    reveal_type(Factory.create("widget")) # Expected: str

    # Matches (item_id: int, quantity: int) -> int
    reveal_type(Factory.create(10, 5)) # Expected: int

    # Matches (item_type: type[T], config: dict[str, Any]) -> T
    product_instance = Factory.create(Product, {"version": 1})
    # DISAGREEMENT POINT: Some checkers might infer 'Product' (correct), 
    # others might infer 'Any' or error out due to the 'identity_decorator(f: Any) -> Any'
    # obscuring the specific overload's return type.
    reveal_type(product_instance) 
    print(f"Created product name: {product_instance.get_name()}")

    # These calls match no specific overload, falling into the Any catch-all.
    # Expected: Any for all of these.
    reveal_type(Factory.create("untyped", value=123)) 
    reveal_type(Factory.create(1.0, 2.0))
    reveal_type(Factory.create(lambda x: x + 1, data=7))

if __name__ == "__main__":
    test_factory()