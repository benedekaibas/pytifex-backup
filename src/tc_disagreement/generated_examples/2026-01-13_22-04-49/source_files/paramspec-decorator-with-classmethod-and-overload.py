from typing import TypeVar, Callable, ParamSpec, Any, ClassVar, overload, reveal_type

R = TypeVar("R")
P = ParamSpec("P")
C = TypeVar("C", bound=type) # Type variable for the class itself

def custom_classmethod_decorator(func: Callable[P, R]) -> Callable[P, R]:
    """
    A decorator that specifically wraps class methods.
    It prints class name and then calls the original method.
    """
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # P.args[0] should be the class (cls) for a classmethod.
        # This tests correct ParamSpec resolution for the first argument.
        cls_arg = args[0]
        cls_name = cls_arg.__name__ if isinstance(cls_arg, type) else "UnknownClass"
        print(f"Decorating classmethod call for '{cls_name}.{func.__name__}'")
        return func(*args, **kwargs)
    return wrapper

class ResourceManager:
    _resources_count: ClassVar[int] = 0

    @overload
    @classmethod
    def create_resource(cls: C, name: str) -> C: ...
    @overload
    @custom_classmethod_decorator # Decorator on specific overload
    @classmethod
    def create_resource(cls: type, name: str, quantity: int) -> list[Any]: ...
    @overload
    @classmethod
    def create_resource(cls: type, *args: Any, **kwargs: Any) -> Any: ... # Catch-all

    @classmethod
    def create_resource(cls: type, *args: Any, **kwargs: Any) -> Any:
        if len(args) == 1 and isinstance(args[0], str):
            ResourceManager._resources_count += 1
            print(f"Creating a single resource '{args[0]}'")
            return cls() # Returns an instance of the class C
        elif len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], int):
            ResourceManager._resources_count += args[1]
            print(f"Creating {args[1]} resources named '{args[0]}'")
            return [f"{args[0]}_{i}" for i in range(args[1])] # Returns list of str
        else:
            print(f"Unhandled resource creation: args={args}, kwargs={kwargs}")
            return None

    def __init__(self):
        self.id = ResourceManager._resources_count

class SpecificResource(ResourceManager):
    def get_specific_id(self) -> int:
        return self.id * 10

def test_resource_manager():
    # Matches (cls: C, name: str) -> C
    single_res = ResourceManager.create_resource("Logger")
    reveal_type(single_res) # Expected ResourceManager. DISAGREEMENT if Any or different.

    sub_res = SpecificResource.create_resource("Database")
    reveal_type(sub_res) # Expected SpecificResource. DISAGREEMENT if ResourceManager or Any.
    print(f"Sub-resource specific ID: {sub_res.get_specific_id()}")

    # Matches (cls: type, name: str, quantity: int) -> list[Any] (decorated overload)
    multi_res = ResourceManager.create_resource("Cache", 5)
    reveal_type(multi_res) # DISAGREEMENT POINT: Expected list[Any] or list[str], might be Any or error.
    print(f"Multi-resources created: {multi_res}")

    # Falls into catch-all overload
    unknown_res = ResourceManager.create_resource(123, "config")
    reveal_type(unknown_res) # DISAGREEMENT POINT: Expected Any, might be error.

    print(f"Total resources count: {ResourceManager._resources_count}")

if __name__ == "__main__":
    test_resource_manager()