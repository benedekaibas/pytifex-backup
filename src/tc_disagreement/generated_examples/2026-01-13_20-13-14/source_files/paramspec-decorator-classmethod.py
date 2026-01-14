# id: paramspec-decorator-classmethod
# EXPECTED:
#   mypy: No error (Correctly infers signature including 'cls')
#   pyright: No error (Correctly infers signature including 'cls')
#   pyre: Error (Could not find parameter `cls` in call to `create` if it mis-infers)
#   zuban: Error (Signature mismatch, might not correctly pass 'cls' through ParamSpec)
# REASON: When `ParamSpec` is used to decorate a `classmethod`, some type checkers (like Pyre or Zuban in some versions/strictness levels) may struggle to correctly preserve the `cls` argument. They might infer the decorated function's signature as if it were a regular function, thus losing the `cls` parameter and causing a mismatch when the decorated method is called via the class. Mypy and Pyright typically handle this specific interaction well.

from typing import TypeVar, Callable, Any
from typing_extensions import ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

def log_calls(func: Callable[P, T]) -> Callable[P, T]:
    """A simple decorator that logs calls, preserving the original signature."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        print(f"Calling {func.__qualname__} with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

class Service:
    _instance_count = 0

    def __init__(self, name: str):
        self.name = name
        Service._instance_count += 1
        print(f"Service '{self.name}' created.")

    @log_calls
    @classmethod
    def create(cls, name: str) -> "Service": # Class method decorated
        print(f"  Inside create for class: {cls.__name__}")
        return cls(name)

    @log_calls
    def describe(self) -> str:
        return f"Service {self.name} (Instance ID: {id(self)})"

if __name__ == "__main__":
    # The divergence occurs here: does `create`'s signature, including `cls`,
    # correctly pass through the decorator?
    s1 = Service.create("AuthService")
    s2 = Service.create(name="UserService")
    print(s1.describe())