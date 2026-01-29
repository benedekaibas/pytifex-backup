from typing import TypeVar, ParamSpec, Callable, Any
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def my_decorator(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Decorated function '{func.__name__}' called.")
        result = func(*args, **kwargs)
        # Here, `_` holds the result. zuban#180 flagged `_ = ...` for needing annotation.
        # If the result type R is complex or generic, checkers might disagree if `_`
        # requires an annotation or if its type is trivially inferable.
        _ = result 
        print(f"Decorated function '{func.__name__}' finished (result assigned to _).")
        return result
    return wrapper

@my_decorator
def calculate_sum(a: int, b: int) -> int:
    return a + b

@my_decorator
def get_message(name: str) -> str:
    return f"Hello, {name}!"

class MyProcessor:
    @my_decorator
    def process(self, value: Any) -> Any:
        return f"Processed: {value}"

if __name__ == "__main__":
    _ = calculate_sum(5, 3) # This assignment to `_`
    print(f"Sum calculated (dummy var _): {_}")

    _ = get_message("World")
    print(f"Message received (dummy var _): {_}")

    processor = MyProcessor()
    _ = processor.process([1, 2, 3])
    print(f"Processed value (dummy var _): {_}")