from typing import TypeVar, ParamSpec, Callable, Type, ClassVar, reveal_type, Concatenate
from functools import wraps

R = TypeVar("R")
P = ParamSpec("P")
T_Cls = TypeVar("T_Cls", bound="BaseProcessor")

def class_method_logger(f: Callable[Concatenate[Type[T_Cls], P], R]) -> Callable[Concatenate[Type[T_Cls], P], R]:
    """
    A decorator for class methods that uses ParamSpec to preserve the method signature,
    including the `cls` argument.
    """
    @wraps(f)
    def wrapper(cls: Type[T_Cls], *args: P.args, **kwargs: P.kwargs) -> R:
        print(f"[{cls.__name__}] Calling class method '{f.__name__}' with args: {args}, kwargs: {kwargs}")
        return f(cls, *args, **kwargs)
    return wrapper

class BaseProcessor:
    _instance_count: ClassVar[int] = 0

    def __init__(self, name: str):
        self.name = name
        BaseProcessor._instance_count += 1
    
    @classmethod
    @class_method_logger
    def create_named_instance(cls: Type[T_Cls], prefix: str, id_num: int) -> T_Cls:
        """
        A class method that creates an instance, decorated with a ParamSpec-aware decorator.
        `P` should capture `(prefix: str, id_num: int)`.
        `T_Cls` should be the specific class (e.g., `MySpecialProcessor`).
        """
        instance_name = f"{prefix}-{id_num}"
        return cls(instance_name)

    @classmethod
    def get_total_instances(cls) -> int:
        return cls._instance_count

class MySpecialProcessor(BaseProcessor):
    def __init__(self, name: str):
        super().__init__(name)
        self.special_id = name.split('-')[-1] # Extract ID from name

    def get_special_id(self) -> str:
        return self.special_id

if __name__ == "__main__":
    # Call the decorated class method on the base class
    proc1 = BaseProcessor.create_named_instance("Base", 1)
    reveal_type(proc1) # Expected: BaseProcessor

    # Call the decorated class method on the derived class
    proc2 = MySpecialProcessor.create_named_instance("Special", 2)
    reveal_type(proc2) # Expected: MySpecialProcessor

    print(f"Processor 1 name: {proc1.name}")
    print(f"Processor 2 name: {proc2.name}, Special ID: {proc2.get_special_id()}") # Should be valid

    total_instances = BaseProcessor.get_total_instances()
    print(f"Total instances created: {total_instances}") # Expected: 2

    print("\nExample demonstrating ParamSpec with `Concatenate` in a decorator for class methods.")
    print("Checks if the decorator correctly preserves the `cls` argument and the remaining `ParamSpec` arguments.")