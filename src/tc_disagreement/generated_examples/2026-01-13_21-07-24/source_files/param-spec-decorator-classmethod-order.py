# id: param-spec-decorator-classmethod-order
# category: param-spec-decorator
# expected: mypy: error, pyrefly: ok, zuban: ok, ty: ok

from typing import Callable, ParamSpec, TypeVar
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def logging_decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """A simple generic decorator that logs function calls."""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Log: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

class MyProcessor:
    # DIVERGENCE POINT:
    # Applying `logging_decorator` *before* `@classmethod`.
    # `logging_decorator` returns a callable `wrapper`. `@classmethod` then
    # tries to wrap this `wrapper`. Mypy correctly identifies this as an error
    # because `classmethod` expects to wrap a plain function, not an already-decorated callable
    # (which is a descriptor in itself).
    # Other type checkers might be more lenient, allowing this order.
    @logging_decorator
    @classmethod
    def inner_method(cls, value: int) -> str:
        return f"Class method (decorated first) processing {value} for {cls.__name__}"

    # This is the generally accepted and correct order for applying decorators
    # with `classmethod` or `staticmethod`.
    # `@classmethod` is applied first, then `logging_decorator` wraps the
    # resulting method (which is now effectively a class method descriptor).
    @classmethod
    @logging_decorator
    def outer_method(cls, value: int) -> str:
        return f"Class method (classmethod first) processing {value} for {cls.__name__}"

if __name__ == "__main__":
    # MyPy will flag an error at the definition of `inner_method` itself:
    # `error: "classmethod" used with a method that is already a descriptor [misc]`
    # This signifies a fundamental disagreement in how this decorator order is handled.
    # If the error is ignored, this call would execute at runtime.
    print(MyProcessor.inner_method(123))

    # This order is correctly handled by all type checkers.
    print(MyProcessor.outer_method(456))