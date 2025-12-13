# id: paramspec-classmethod-staticmethod
# EXPECTED:
#   mypy: Error (Signature mismatch/Argument 1 to "create_instance" has incompatible type "Type[MyUtility]"; expected "Type[MyUtility]" / "generate_uuid" has incompatible type)
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy has historically struggled with preserving the correct signature (including the implicit `cls` or `self` argument) when applying a `ParamSpec`-based decorator to `classmethod` or `staticmethod`. It might lose the `cls` argument's type, leading to a signature mismatch. Pyright, Pyre, and Zuban are generally better at handling this.

from typing import TypeVar, Callable
from typing_extensions import ParamSpec

P = ParamSpec('P')
R = TypeVar('R')

def log_args_decorator(func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)
    return wrapper

class MyUtility:
    @log_args_decorator
    @classmethod
    def create_instance(cls, name: str, id: int) -> "MyUtility":
        print(f"Creating MyUtility instance: {name} (ID: {id})")
        return cls()

    @log_args_decorator
    @staticmethod
    def generate_uuid(prefix: str = "") -> str:
        import uuid
        return f"{prefix}-{uuid.uuid4()}"

if __name__ == "__main__":
    instance = MyUtility.create_instance("test_item", 123) # Mypy often flags 'cls' parameter issue
    reveal_type(MyUtility.create_instance)

    uuid_val = MyUtility.generate_uuid("prefix")
    reveal_type(MyUtility.generate_uuid)