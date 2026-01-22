# id: final-class-var-subclass-access
# EXPECTED:
#   mypy: No error (mypy is generally lenient with Final class vars in inheritance for access)
#   pyright: No error (pyright typically allows this access)
#   pyre: Error (Cannot access final attribute `CONFIG_KEY` via `DerivedClass`)
#   zuban: Error (Treats Final class vars as more strictly bound to the declaring class)
# REASON: This divergence occurs when a `Final` class variable in a base class is accessed through a derived class. Mypy and Pyright typically allow this, as `Final` mainly concerns reassignment, not access patterns through inheritance. Pyre and Zuban might interpret `Final` as implying a stricter binding to the declaring class for type safety, disallowing access via the subclass's name (e.g., `DerivedClass.CONFIG_KEY`), considering it an indirect or potentially ambiguous access, even though Python's MRO allows it at runtime.

from typing import Final

class BaseConfig:
    CONFIG_KEY: Final[str] = "default_key"
    OTHER_SETTING: int = 10

class DerivedConfig(BaseConfig):
    # No override, just accessing parent's Final class variable
    pass

def print_config_key(cls: type[BaseConfig]) -> None:
    print(f"Config Key from {cls.__name__}: {cls.CONFIG_KEY}")

if __name__ == "__main__":
    print(BaseConfig.CONFIG_KEY) # Should be fine everywhere
    print(DerivedConfig.CONFIG_KEY) # Divergence point: access via subclass

    # Another subtle test: can a subclass redefine it if it's Final in the base?
    # This should be an error everywhere.
    # class AnotherDerived(BaseConfig):
    #     CONFIG_KEY: Final[str] = "new_key" # Should error