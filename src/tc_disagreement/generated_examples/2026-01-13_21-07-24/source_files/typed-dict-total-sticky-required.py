# id: typed-dict-total-sticky-required
# category: typed-dict-total
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import TypedDict, NotRequired

# Base TypedDict with total=False. 'x' is implicitly NotRequired.
class BaseConfig(TypedDict, total=False):
    x: int

# Intermediate TypedDict with total=True, inheriting from BaseConfig.
# MyPy's behavior: 'x' becomes implicitly Required in RequiredXConfig.
class RequiredXConfig(BaseConfig, total=True):
    y: str

# Final TypedDict with total=False, inheriting from RequiredXConfig.
# DIVERGENCE POINT:
# Does 'x' (which was Required in RequiredXConfig) revert to NotRequired
# due to FlexibleConfig's total=False, or does its "Required" status stick?
# PEP 655 states: "it is a static error if the resulting type would have a field
# whose final requiredness is different from all its declarations."
# 'x' is declared only once in BaseConfig (implicitly NotRequired). Its status
# *changes* implicitly through the inheritance chain. MyPy allows this implicit
# change to be overridden by subsequent `total` declarations.
# Other checkers might interpret "Required is sticky" more strictly, especially
# when a field was implicitly made Required by an intermediate `total=True`.
class FlexibleConfig(RequiredXConfig, total=False):
    z: NotRequired[bool]

if __name__ == "__main__":
    # This instance omits 'x' and 'y'.
    # MyPy considers this valid because in FlexibleConfig, 'x', 'y', and 'z'
    # are all considered NotRequired due to `total=False`.
    # Other type checkers might flag an error for missing 'x' and 'y',
    # adhering to a stricter "sticky Required" interpretation, where once
    # a field becomes implicitly Required by an intermediate `total=True`,
    # it cannot become NotRequired again through a subsequent `total=False`.
    config_instance: FlexibleConfig = {"z": False}
    print(f"FlexibleConfig instance: {config_instance}")

    # This should be valid for all checkers.
    required_x_instance: RequiredXConfig = {"x": 10, "y": "value"}
    print(f"RequiredXConfig instance: {required_x_instance}")

    # This should be an error for all checkers, as 'x' and 'y' are Required.
    # invalid_required_x_instance: RequiredXConfig = {"z": False} # Uncomment to test