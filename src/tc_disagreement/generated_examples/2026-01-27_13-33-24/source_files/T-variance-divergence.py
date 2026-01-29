from typing import TypeVar, Protocol, Self, runtime_checkable, Callable, Any # Only change: added Any
from abc import abstractmethod

T = TypeVar('T') # Mypy typically suggests `TypeVar('T', contravariant=True)` here.

@runtime_checkable
class ConfigurableBuilder(Protocol[T]):
    """
    A generic protocol for builders that can be configured.
    Tests Self type in a generic protocol with abstract methods and default arguments,
    where a parameter's type is a Callable.
    """
    @abstractmethod
    def configure(self, settings_loader: Callable[[], dict[str, Any]], *, apply_now: bool = True) -> Self:
        """Configures the builder and returns Self."""
        ...

    @abstractmethod
    def build(self, item_data: T) -> Any: # Type `Any` used in return
        """Builds an item of type T."""
        ...

class BasicBuilder(ConfigurableBuilder[str]):
    def __init__(self, name: str = "basic"):
        self.name = name
        self.config: dict[str, Any] = {}

    def configure(self, settings_loader: Callable[[], dict[str, Any]], *, apply_now: bool = False) -> Self: # Different default for apply_now
        print(f"Configuring {self.name} builder (apply_now={apply_now})...")
        new_settings = settings_loader()
        if apply_now:
            self.config.update(new_settings)
        return self

    def build(self, item_data: str) -> str:
        final_config = self.config.get("prefix", "") + item_data
        print(f"Building '{final_config}' with config: {self.config}")
        return final_config

class AdvancedBuilder(ConfigurableBuilder[int]):
    def __init__(self, id_val: int = 0):
        self.id_val = id_val
        self.config: dict[str, Any] = {"version": 1}

    def configure(self, settings_loader: Callable[[], dict[str, Any]], *, apply_now: bool = True) -> Self:
        print(f"Configuring Advanced builder {self.id_val} (apply_now={apply_now})...")
        new_settings = settings_loader()
        self.config.update(new_settings)
        return self

    def build(self, item_data: int) -> dict[str, Any]:
        result = {"id": self.id_val, "data": item_data, "config": self.config}
        print(f"Building {result}")
        return result

def get_settings_a() -> dict[str, Any]:
    return {"prefix": "ABC-", "timeout": 10}

def get_settings_b() -> dict[str, Any]:
    return {"version": 2, "cache_size": 512}

if __name__ == "__main__":
    basic_b = BasicBuilder()
    # Test 'configure' method's return type (Self) and default argument
    configured_basic_b = basic_b.configure(get_settings_a) # Should use BasicBuilder's default for apply_now (False)
    # reveal_type(configured_basic_b) # Expected: BasicBuilder, Actual: Self or ConfigurableBuilder[str]?
    print(f"BasicBuilder config after first configure: {configured_basic_b.config}")
    configured_basic_b.build("document")

    # Call `configure` explicitly overriding default.
    configured_basic_b.configure(get_settings_a, apply_now=True)
    print(f"BasicBuilder config after second configure: {configured_basic_b.config}")
    configured_basic_b.build("report")

    adv_b = AdvancedBuilder(1)
    # The Protocol defines apply_now=True, AdvancedBuilder also uses apply_now=True.
    configured_adv_b = adv_b.configure(get_settings_b)
    # reveal_type(configured_adv_b) # Expected: AdvancedBuilder
    print(f"AdvancedBuilder config: {configured_adv_b.config}")
    configured_adv_b.build(99)

    # What if a checker sees `configured_basic_b` as `ConfigurableBuilder[str]`?
    # Then `configured_basic_b.name` would be an error.
    print(f"Name of basic builder: {configured_basic_b.name}")