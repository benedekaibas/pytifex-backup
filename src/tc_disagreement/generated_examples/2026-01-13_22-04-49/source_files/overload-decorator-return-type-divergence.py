from typing import TypeVar, Callable, ParamSpec, Any, overload, reveal_type

R = TypeVar("R")
P = ParamSpec("P")

def caching_decorator(func: Callable[P, R]) -> Callable[P, tuple[R, bool]]:
    """
    A decorator that wraps a function, simulating a cache.
    It returns a tuple of (result, is_cached_hit), changing the return type.
    """
    cache: dict[Any, R] = {}
    
    # Robustly get the function's name, handling staticmethod/classmethod wrappers
    # If `func` is a staticmethod object, `getattr(func, '__func__', func)` will retrieve the actual function.
    # Then we get its __name__. If all fails, use 'unknown_function'.
    actual_func = getattr(func, '__func__', func)
    func_name = getattr(actual_func, '__name__', 'unknown_function')

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> tuple[R, bool]:
        # For simplicity, cache key is just args.
        # This tests P.args and P.kwargs for generic cache key generation.
        key = (args, tuple(sorted(kwargs.items()))) # Create a hashable key
        if key not in cache:
            print(f"Cache miss for {func_name} with {args}, {kwargs}")
            result = func(*args, **kwargs)
            cache[key] = result
            return result, False # Not cached
        else:
            print(f"Cache hit for {func_name} with {args}, {kwargs}")
            return cache[key], True # Cached
    return wrapper

class DataService:
    @overload
    @staticmethod
    def fetch(id: int) -> str: ...
    @overload
    @staticmethod
    def fetch(query: str, limit: int) -> list[str]: ...
    @overload
    @caching_decorator # Apply decorator to one of the overloads
    @staticmethod
    def fetch(category: str, include_details: bool = False, **filter_kwargs: Any) -> dict[str, Any]: ...
    @overload
    @staticmethod
    def fetch(*args: Any, **kwargs: Any) -> Any: ... # Catch-all overload

    @staticmethod
    def fetch(*args: Any, **kwargs: Any) -> Any:
        if len(args) == 1 and isinstance(args[0], int):
            return f"Item {args[0]} details"
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], int):
            return [f"Result {i} for '{args[0]}'" for i in range(args[1])]
        elif len(args) >= 1 and isinstance(args[0], str): # Matches the decorated overload
            # Fix: filter_kwargs must be extracted from kwargs as it's not a direct variable
            category_arg = args[0]
            include_details_arg = kwargs.pop('include_details', False) # Remove from kwargs
            actual_filter_kwargs = kwargs # Remaining kwargs are the filter_kwargs
            return {"category": category_arg, "details": include_details_arg, "filters": actual_filter_kwargs}
        else:
            return "Unknown fetch type"

def test_data_service():
    # Matches (id: int) -> str
    reveal_type(DataService.fetch(101))

    # Matches (query: str, limit: int) -> list[str]
    reveal_type(DataService.fetch("users", 3))

    # Matches (category: str, include_details: bool, **filter_kwargs) -> dict[str, Any]
    # This is the decorated overload. The ParamSpec handling within the decorator is key.
    # DISAGREEMENT POINT:
    # If the type checker applies the decorator's type transformation to the overload,
    # the type will be `tuple[dict[str, Any], bool]`.
    # If the type checker ignores decorators on overload signatures (common for mypy),
    # the type will remain `dict[str, Any]`.
    result_decorated_call1 = DataService.fetch("products", include_details=True, price_min=100)
    reveal_type(result_decorated_call1)

    result_decorated_call2 = DataService.fetch("products", include_details=True, price_min=100) # Second call, should be cached.
    reveal_type(result_decorated_call2) # Should be the same as result_decorated_call1.

    # This falls into the catch-all.
    reveal_type(DataService.fetch("any", "type", other_arg=1))

if __name__ == "__main__":
    test_data_service()