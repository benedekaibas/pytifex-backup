from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Self, List, reveal_type

T = TypeVar("T")

class BaseConfigurator(Generic[T], ABC):
    """
    Abstract generic base class with a class variable typed with `Self` within a list.
    """
    _registered_instances: List[Self] = [] # DISAGREEMENT POINT: Self in a class variable type annotation

    def __init__(self, value: T):
        self.value = value
        type(self)._registered_instances.append(self) # Add self to the class-level list

    @abstractmethod
    def configure(self) -> T:
        pass

class IntConfigurator(BaseConfigurator[int]):
    """
    Concrete subclass implementing BaseConfigurator[int].
    The `_registered_instances` list should hold `IntConfigurator` objects.
    """
    def configure(self) -> int:
        return self.value * 2

    def get_specific_int_value(self) -> int:
        return self.value

class StrConfigurator(BaseConfigurator[str]):
    """
    Another concrete subclass implementing BaseConfigurator[str].
    `_registered_instances` here should hold `StrConfigurator` objects.
    """
    def configure(self) -> str:
        return self.value.upper()

    def get_specific_str_value(self) -> str:
        return self.value

def process_configurators():
    """
    Function to demonstrate interaction with the registered instances.
    """
    i1 = IntConfigurator(10)
    i2 = IntConfigurator(20)
    s1 = StrConfigurator("hello")

    # Accessing the class variable `_registered_instances`
    # Checkers might disagree on the precise type of elements in this list.
    # For IntConfigurator._registered_instances, elements should be IntConfigurator.
    # For StrConfigurator._registered_instances, elements should be StrConfigurator.
    reveal_type(IntConfigurator._registered_instances) # DISAGREEMENT POINT: Is it List[IntConfigurator] or List[BaseConfigurator[int]]?
    reveal_type(StrConfigurator._registered_instances) # DISAGREEMENT POINT: Is it List[StrConfigurator] or List[BaseConfigurator[str]]?

    if IntConfigurator._registered_instances:
        first_int_config = IntConfigurator._registered_instances[0]
        # This access should be allowed if the type of elements is correctly narrowed to IntConfigurator.
        print(f"First int config specific value: {first_int_config.get_specific_int_value()}") # DISAGREEMENT POINT
    
    # This should ideally be a type error because s1 is a StrConfigurator, not an IntConfigurator.
    # However, if `_registered_instances` is too loosely typed (e.g., List[BaseConfigurator]),
    # some checkers might not catch this.
    # IntConfigurator._registered_instances.append(s1) # Expected error

if __name__ == "__main__":
    process_configurators()