from typing import TypeVar, Generic, Protocol, Self, reveal_type
from abc import ABC, abstractmethod

# T is bound by a Protocol that requires a 'value' attribute
T_Valued = TypeVar("T_Valued", bound="ValueContainerProtocol")

class ValueContainerProtocol(Protocol):
    value: int
    def get_value(self) -> int:
        return self.value # Default implementation

    def update_value(self, new_val: int) -> Self: # Returns Self
        self.value = new_val
        return self

class GenericProcessor[T_Valued](ABC):
    """
    Abstract generic class that operates on `T_Valued`.
    T_Valued is bound by `ValueContainerProtocol`.
    """
    def __init__(self, item: T_Valued):
        self._item = item

    def inspect_value(self) -> int:
        return self._item.get_value()

    @abstractmethod
    def process_item(self) -> T_Valued:
        pass

class ConcreteProcessor(GenericProcessor["MyValueClass"]): # Specializes with a concrete class
    def __init__(self, item: "MyValueClass"):
        super().__init__(item)
        self.processor_name = "Concrete"

    def process_item(self) -> "MyValueClass":
        # Uses the update_value method from the protocol bound.
        # This checks if the return type `Self` is correctly resolved to `MyValueClass`.
        self._item.update_value(self._item.value + 1)
        return self._item

class MyValueClass(ValueContainerProtocol): # Implements the protocol
    def __init__(self, start_value: int):
        self.value = start_value

    def get_info(self) -> str:
        return f"Current value: {self.value}"

def operate_processor(proc: GenericProcessor[T_Valued]):
    """
    Function to operate on a `GenericProcessor`.
    """
    reveal_type(proc._item) # Expected T_Valued
    inspected = proc.inspect_value()
    reveal_type(inspected) # Expected int

    processed_item = proc.process_item()
    reveal_type(processed_item) # DISAGREEMENT POINT: Expected T_Valued, might be broader like ValueContainerProtocol.

    # If `processed_item` is correctly narrowed, this specific method should be accessible.
    # Otherwise, it's an error.
    if isinstance(processed_item, MyValueClass):
        print(f"Processed item info: {processed_item.get_info()}") # DISAGREEMENT POINT

if __name__ == "__main__":
    mvc = MyValueClass(10)
    cp = ConcreteProcessor(mvc)

    print("--- Operating on ConcreteProcessor ---")
    operate_processor(cp)

    # What if we create a class that only *partially* satisfies the protocol or has a different Self behavior?
    class AnotherValueClass: # Doesn't implement ValueContainerProtocol directly
        value: int = 50
        def get_value(self) -> int: return self.value
        # Missing update_value, or update_value doesn't return Self
        # This should cause an error if used where ValueContainerProtocol is expected.
        # another_proc = GenericProcessor(AnotherValueClass(50)) # Expected error here.