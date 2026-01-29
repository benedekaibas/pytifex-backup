from typing import TypeVar, ParamSpec, Callable, Union, reveal_type, Type

P = ParamSpec("P")
R = TypeVar("R")

def conditional_decorator(
    func: Callable[P, R]
) -> Union[Callable[P, R], Callable[P, Type[None]]]:
    """
    A decorator that *type-system-wise* implies it might return a callable with the original return type,
    or one whose return type is `Type[None]`. At runtime, it always returns the original.
    This tests ParamSpec resolution within a Union return.
    """
    class OriginalWrapper:
        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
            print(f"Calling {func.__name__} with original return type")
            return func(*args, **kwargs)

    class AltWrapper:
        def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Type[None]:
            print(f"Calling {func.__name__} with Type[None] return type (should not happen at runtime)")
            func(*args, **kwargs)
            return type(None) # Always returns the type object None

    # This branch is never taken at runtime, but affects the static type.
    if False:
        return AltWrapper()
    else:
        return OriginalWrapper()

def my_function(x: int, y: str) -> float:
    return float(x) + len(y)

decorated_func = conditional_decorator(my_function)

# Type checker should infer decorated_func as Union[Callable[[int, str], float], Callable[[int, str], Type[None]]]
reveal_type(decorated_func)

# The result of calling decorated_func should reflect the Union of return types.
result = decorated_func(10, "hello")
reveal_type(result) # Expected: Union[float, Type[None]]

if __name__ == "__main__":
    print(f"Result from calling decorated_func: {decorated_func(1, 'world')}")
    # At runtime, it will always be a float, but type checkers should respect the annotation.