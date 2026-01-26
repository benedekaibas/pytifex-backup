import functools
from typing import TypeVar, ParamSpec, Callable, Any, Self, Type, Concatenate

R = TypeVar("R")
P = ParamSpec("P")
T = TypeVar("T")
Cls = TypeVar("Cls") # Defined TypeVar 'Cls'

def log_classmethod_calls(func: Callable[Concatenate[Type[Cls], P], R]) -> Callable[Concatenate[Type[Cls], P], R]:
    # FIX: Use functools.wraps to propagate metadata like __name__ from the original function
    # This helps type checkers understand that 'func' will have __name__ at runtime.
    @functools.wraps(func)
    def wrapper(cls: Type[Cls], *args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling class method '{func.__name__}' on class '{cls.__name__}' with args {args}, kwargs {kwargs}")
        return func(cls, *args, **kwargs)
    return wrapper

class BaseProcessor(object):
    # FIX: Added a generic __init__ method to BaseProcessor.
    # This prevents the initial error of calling `object.__init__` with arguments
    # (as `BaseProcessor` previously had no __init__), and shifts the focus
    # to subclass constructor compatibility, which is the intended divergence point.
    def __init__(self, data: Any) -> None:
        print(f"BaseProcessor __init__ called with data: {data}")
        pass # Base processor's init doesn't do much concrete work

    @classmethod
    @log_classmethod_calls
    def create_instance(cls: type[Self], name: str) -> Self:
        print(f"BaseProcessor.create_instance called with name: {name}")
        # DIVERGENCE POINT:
        # This line calls the constructor of `cls` (which is `Self`) with `name` (a `str`).
        # - For `StringProcessor`, `StringProcessor.__init__(data: str)` is compatible.
        # - For `IntProcessor`, `IntProcessor.__init__(value: int)` is NOT compatible with `name: str`.
        #
        # Type checkers will diverge on whether they correctly infer the specific
        # constructor signature of `Self` (the concrete subclass like `IntProcessor`)
        # and flag the `str` to `int` mismatch at this call site. Some might,
        # others might allow it because `BaseProcessor.__init__` accepts `Any`.
        return cls(name)

    def process(self) -> str:
        raise NotImplementedError

class StringProcessor(BaseProcessor):
    def __init__(self, data: str) -> None:
        super().__init__(data) # Call base init to keep the MRO chain, passing the string
        self._data = data.upper()

    def process(self) -> str:
        return f"Processed: {self._data}"

class IntProcessor(BaseProcessor):
    def __init__(self, value: int) -> None:
        super().__init__(value) # Call base init, passing the (potentially incorrect) value
        # Ensures that a TypeError will occur at runtime if a string is passed
        if not isinstance(value, int):
            raise TypeError(f"Expected int for value, got {type(value).__name__}")
        self._data = value * 2

    def process(self) -> str:
        return f"Processed: {self._data}"

if __name__ == "__main__":
    # This call should pass type checking for all checkers.
    str_proc = StringProcessor.create_instance(name="hello_world")
    print(str_proc.process())

    # This call is the intended divergence point for type checkers.
    # `IntProcessor.create_instance(name="123")` will internally call `IntProcessor("123")`.
    # `IntProcessor.__init__` expects an `int` for 'value', but `name` is a `str`.
    # Some type checkers are expected to flag this `str` to `int` mismatch
    # at the `return cls(name)` line, while others might not.
    try:
        int_proc = IntProcessor.create_instance(name="123") # Expecting a type error from some checkers
        print(int_proc.process())
    except TypeError as e:
        print(f"Caught expected runtime TypeError for IntProcessor creation: {e}")
    except Exception as e:
        print(f"Caught unexpected error during IntProcessor creation: {e}")

    # Test argument type correctness for create_instance method itself
    # This checks the type of the `name` argument to `create_instance`, not `cls`'s constructor.
    # This should still be caught by all type checkers at the call site.
    try:
        _ = StringProcessor.create_instance(123) # type: ignore # Ignoring to allow runtime test of specific parameter
    except TypeError:
        print("Caught expected TypeError for invalid arg to create_instance (runtime)")
    except Exception as e:
        print(f"Caught unexpected error for invalid arg to create_instance: {e}")

    assert isinstance(str_proc, StringProcessor)