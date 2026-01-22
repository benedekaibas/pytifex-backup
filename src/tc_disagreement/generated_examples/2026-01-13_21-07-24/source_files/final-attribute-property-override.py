# id: final-attribute-property-override
# category: final-override
# expected: mypy: error, pyrefly: ok, zuban: ok, ty: ok

from typing import Final

class Configuration:
    """A base class with Final class attributes."""
    SETTING_A: Final[str] = "default_value_A"
    SETTING_B: Final[int] = 100

class CustomConfiguration(Configuration):
    """
    A subclass attempting to override Final attributes.
    """
    # DIVERGENCE POINT:
    # Overriding a Final class attribute (`SETTING_A`) with a property.
    # PEP 591 states: "In a class body, Final variables cannot be overridden in subclasses."
    # Mypy interprets a property as an override of the Final attribute and flags an error.
    # Other type checkers might consider a property a distinct kind of class member
    # (a descriptor, not a simple variable assignment) and allow this override,
    # or they might not implement this specific check for `Final` in this scenario.
    @property
    def SETTING_A(self) -> str:
        return "custom_value_for_A"

    # This is a direct override of a Final attribute with a different type,
    # which should typically be an error for all compliant type checkers.
    # SETTING_B: Final[str] = "200" # Uncomment to test a universally expected error.

if __name__ == "__main__":
    # Accessing the original Final attributes.
    print(f"Base SETTING_A: {Configuration.SETTING_A}")
    print(f"Base SETTING_B: {Configuration.SETTING_B}")

    # Accessing the potentially overridden attributes in CustomConfiguration.
    # If the checker permits the property override (i.e., not mypy),
    # this will print the value from the property.
    custom_config = CustomConfiguration()
    print(f"Custom SETTING_A (via property): {custom_config.SETTING_A}")
    # MyPy would have already flagged an error at the class definition of CustomConfiguration.