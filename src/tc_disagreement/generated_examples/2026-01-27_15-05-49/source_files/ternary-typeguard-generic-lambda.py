from typing import TypeVar, Union, Callable, reveal_type, TypeGuard, Any

T = TypeVar("T")

class BaseThing:
    def get_info(self) -> str:
        return "Base Info"

class SpecialThing(BaseThing):
    def get_special_info(self) -> str:
        return "Special Info"
    def get_info(self) -> str:
        return self.get_special_info()

def is_special(val: Union[T, BaseThing]) -> TypeGuard[SpecialThing]:
    """
    TypeGuard that narrows a generic type or BaseThing to SpecialThing.
    The generic T here might interact oddly with narrowing.
    """
    return isinstance(val, SpecialThing)

def process_special(s: SpecialThing) -> str:
    return s.get_special_info()

def get_action_lambda(x: Union[T, BaseThing, None]) -> Callable[[], Union[str, None]]:
    # The core test: ternary operator's condition uses TypeGuard, and branches return lambdas
    # that capture `x`. The narrowing of `x` must correctly apply *inside* the lambda.
    action_lambda: Callable[[], Union[str, None]] = (
        (lambda: process_special(x)) if is_special(x) else (lambda: None)
    )
    
    reveal_type(action_lambda) # Expected: Callable[[], Union[str, None]]
    
    # Test the return type of the lambda call
    lambda_result = action_lambda()
    reveal_type(lambda_result) # Expected: Union[str, None]

    return action_lambda

if __name__ == "__main__":
    special_obj = SpecialThing()
    base_obj = BaseThing()
    none_obj = None

    lambda_s = get_action_lambda(special_obj)
    print(f"Special lambda result: {lambda_s()}") # Expected: Special Info
    
    lambda_b = get_action_lambda(base_obj)
    print(f"Base lambda result: {lambda_b()}") # Expected: None
    
    lambda_n = get_action_lambda(none_obj)
    print(f"None lambda result: {lambda_n()}") # Expected: None

    print("\nExample demonstrating TypeGuard narrowing within a lambda chosen by a ternary expression.")
    print("Checks if type checkers correctly narrow the captured variable `x` for the `process_special(x)` call.")