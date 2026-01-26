from typing import TypeVar, Union, Callable, TypeGuard, reveal_type, List, Optional

class Config:
    def __init__(self, name: str) -> None:
        self.name = name
    def validate(self) -> bool:
        return True
    def describe(self) -> str:
        return f"Config: {self.name}"

class SpecialConfig(Config):
    def describe(self) -> str:
        return f"Special Config: {self.name.upper()}"
    def perform_special_action(self) -> None:
        print(f"Performed special action for {self.name}")

def is_special_config(item: Union[Config, SpecialConfig, None]) -> TypeGuard[SpecialConfig]:
    return isinstance(item, SpecialConfig)

def process_item(item: Union[Config, SpecialConfig, None]) -> None:
    # Test narrowing within a lambda in a ternary expression
    # Original issue was about x in `foo(x)`. Here, we have `item` in `item.describe()`
    action_lambda: Callable[[], None] = (
        (lambda: item.perform_special_action()) # should narrow to SpecialConfig
        if is_special_config(item) else
        (lambda: print(f"Normal config: {item.describe()}" if item else "No config")) # should narrow to Config or None
    )
    reveal_type(action_lambda) # N: Revealed type is "def ()" or similar

    action_lambda()

    # More complex ternary with generic return and list operations
    T = TypeVar("T")
    def get_first_or_default(data: List[T], default: T) -> T:
        return data[0] if data else default

    # Here, `item` is narrowed in the TypeGuard branch
    # What if the return type of the lambda changes based on narrowing?
    get_description_lambda = (
        (lambda: item.describe() + " (Validated)") # Item is SpecialConfig
        if is_special_config(item) and item.validate() else
        (lambda: item.describe() if item else "No item available") # Item is Config or None
    )
    reveal_type(get_description_lambda) # N: Revealed type should be "def () -> str"

    print(get_description_lambda())

if __name__ == "__main__":
    c1: Union[Config, SpecialConfig, None] = Config("general")
    c2: Union[Config, SpecialConfig, None] = SpecialConfig("specific")
    c3: Union[Config, SpecialConfig, None] = None

    print("\n--- Processing c1 (Config) ---")
    process_item(c1)
    print("\n--- Processing c2 (SpecialConfig) ---")
    process_item(c2)
    print("\n--- Processing c3 (None) ---")
    process_item(c3)

    # Test a direct type guard call outside ternary
    test_config: Optional[Config] = SpecialConfig("direct")
    if is_special_config(test_config):
        test_config.perform_special_action()
    else:
        print("Not special")