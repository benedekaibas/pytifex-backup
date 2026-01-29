from typing import TypeVar, Generic, Type, Self

T = TypeVar('T')

class MyResource(Generic[T]):
    def __init__(self, value: T):
        self.value = value
        self.is_active = True

    def deactivate(self) -> Self:
        self.is_active = False
        return self

    def get_value(self) -> T:
        return self.value

    @classmethod
    def create_active(cls: Type[Self], value: T) -> Self:
        return cls(value)

def process_resource(resource: MyResource[str]) -> None:
    if resource.is_active:
        print(f"Processing active resource with value: {resource.get_value()}")
        # Checkers might disagree on the precise type of `resource` here.
        # `ty#2460` showed `type(x) == bool` narrowing issues.
        # Here, `if resource.is_active` acts as a narrowing for the *state*
        # but not necessarily the *type* of resource, but a checker might infer too much.
    else:
        print(f"Resource with value: {resource.get_value()} is inactive.")

if __name__ == "__main__":
    active_res = MyResource.create_active("initial_data")
    process_resource(active_res)

    inactive_res = active_res.deactivate()
    process_resource(inactive_res)

    # Testing another instance and narrowing based on an attribute
    another_res = MyResource[int](123)
    if isinstance(another_res.value, int):
        # This check is trivial, but imagine `value` was `Union[int, str]`
        # and `isinstance(another_res.value, int)` was used for narrowing.
        # If `Self` and generics are involved, type checkers may have differing
        # opinions on what is narrowed and how.
        print(f"Value is an integer: {another_res.value * 2}")
    
    # Reveal type here to see how checkers handle `Self` combined with narrowing conditions
    reveal_type(active_res)
    if active_res.is_active:
        reveal_type(active_res) # Should still be MyResource[str] but potentially some refined state?