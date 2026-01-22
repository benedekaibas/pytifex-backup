# id: final-attribute-override-property
# EXPECTED:
#   mypy: Error on `DetailedAppConfig.MODE`. Mypy flags attempts to redefine `Final` attributes, even with properties.
#   pyright: Error on `DetailedAppConfig.MODE`. Pyright is also strict about `Final` attributes and redefinition.
#   pyre: No error. Pyre has been observed to be less strict about `Final` attributes in class hierarchies, sometimes allowing a property to override a `Final` field. It might treat the property as a different "kind" of member.
#   zuban: Error. Strict `Final` enforcement, considering redefinition via a property as a violation.
# REASON: Type checkers differ in their interpretation of `Final` attributes when a derived class attempts to override them with a property (or a method) of the same name. Some checkers strictly enforce that a `Final` member cannot be redefined in any form, while others might consider a property to be a distinct kind of member that doesn't constitute a direct override in the same way a field would, thereby allowing it.

from typing import Final

class BaseAppConfig:
    """Base class with a final configuration mode."""
    MODE: Final[str] = "PRODUCTION" # This is a final class attribute

class DetailedAppConfig(BaseAppConfig):
    """Derived class attempting to override MODE with a property."""
    @property
    def MODE(self) -> str: # This property has the same name as the Final attribute in BaseAppConfig
        print("Accessing DetailedAppConfig.MODE property")
        return "DEVELOPMENT"

class AnotherAppConfig(BaseAppConfig):
    """Derived class attempting to override MODE with a regular attribute."""
    MODE: str = "STAGING" # This should be an error for all strict checkers.

def get_app_mode(config: BaseAppConfig) -> str:
    return config.MODE

if __name__ == "__main__":
    print("--- Testing DetailedAppConfig ---")
    detailed_config = DetailedAppConfig()
    # The divergence occurs during the definition of DetailedAppConfig.MODE
    # or when assigning an instance of it to a BaseAppConfig variable.
    print(f"Detailed config mode (direct): {detailed_config.MODE}")
    reveal_type(detailed_config.MODE) # Should be str

    # Assigning to a base class type hint.
    # If the property override is allowed, this might change behavior.
    base_view_config: BaseAppConfig = detailed_config
    print(f"Detailed config mode (via BaseAppConfig): {base_view_config.MODE}")
    reveal_type(base_view_config.MODE) # Still str, but definition caused the issue.

    print("\n--- Testing AnotherAppConfig (expected error for all) ---")
    # This assignment should cause a type error for all strict checkers,
    # as it's a direct redefinition of a Final class attribute.
    # another_config: BaseAppConfig = AnotherAppConfig()
    # print(f"Another config mode: {another_config.MODE}")

---

### Snippet 9: Complex Generic Bounds (TypeVar Nesting)