# id: paramspec-classmethod-decorator-signature
# EXPECTED:
#   mypy: Error. Mypy has historically struggled with ParamSpec on classmethod/staticmethod, often losing the `cls` argument or misinterpreting the signature, leading to an error when calling `Service.create_named_resource`.
#   pyright: No error. Pyright is generally very robust with ParamSpec, including on class methods, correctly inferring the `cls` argument's behavior.
#   pyre: Error. Similar to mypy's historical issues, Pyre might misinterpret the signature after decoration.
#   zuban: No error. Aims for high compatibility with modern Python typing features.
# REASON: Type checkers differ in their ability to correctly infer and preserve the signature of class methods when they are decorated by a `ParamSpec`-aware decorator. The implicit `cls` (or `self`) argument can be mishandled, leading to incorrect call signatures or type errors when the method is invoked, as `ParamSpec` needs to correctly capture or omit it.

from typing import TypeVar, Callable, ParamSpec, Type
from typing_extensions import Concatenate # Explicitly show usage though not strictly needed for this example

P = ParamSpec('P')
R = TypeVar('R')
ClsT = TypeVar('ClsT') # Type variable for the class type in classmethods

def log_and_return(func: Callable[P, R]) -> Callable[P, R]:
    """A simple decorator that logs and returns the result."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"LOG: Calling '{func.__name__}' with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"LOG: '{func.__name__}' returned: {result}")
        return result
    return wrapper

class Resource:
    _registry: dict[str, 'Resource'] = {}

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value
        self.__class__._registry[name] = self

    @log_and_return
    @classmethod
    def create_named_resource(cls: Type[ClsT], name: str, initial_value: int = 0) -> ClsT:
        """A class method to create or retrieve a resource."""
        if name not in cls._registry:
            print(f"  Creating new resource: {name}")
            return cls(name, initial_value)
        print(f"  Retrieving existing resource: {name}")
        return cls._registry[name] # type: ignore [return-value] # This ignore is for runtime, type checkers handle it

if __name__ == "__main__":
    print("--- Calling create_named_resource ---")
    # This call should be type-checked based on `create_named_resource`'s
    # original signature, correctly handling `cls` and `name: str, initial_value: int`.
    resource1 = Resource.create_named_resource("Alpha", 10)
    print(f"Resource 1: {resource1.name}, {resource1.value}")
    reveal_type(resource1) # EXPECTED: Resource

    resource2 = Resource.create_named_resource("Beta") # Uses default initial_value
    print(f"Resource 2: {resource2.name}, {resource2.value}")

    # The actual divergence will be seen here:
    # Mypy/Pyre might reveal a signature that doesn't include 'initial_value' or misattributes 'name'
    reveal_type(Resource.create_named_resource) # Check the inferred signature

---

### Snippet 5: `Self` in Generics with Abstract Methods