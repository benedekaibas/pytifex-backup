# id: overload-literal-discrimination
# EXPECTED for `debug_val` and `retries_val`:
#   mypy: Union[bool, int, str] (less precise discrimination, often falls back to the broadest common type)
#   pyright: bool (for "debug_mode"), int (for "max_retries")
#   pyre: bool (for "debug_mode"), int (for "max_retries")
#   zuban: bool (for "debug_mode"), int (for "max_retries")
# REASON: Mypy is sometimes less aggressive at discriminating `Literal` types within overloads. When a literal string is passed, it might default to the more general `str` overload or combine the results, leading to a wider `Union` type, whereas Pyright, Pyre, and Zuban are often more precise in selecting the specific literal overload and returning its exact type.

from typing import overload, Literal, Union

@overload
def get_config_value(key: Literal["debug_mode"]) -> bool: ...
@overload
def get_config_value(key: Literal["max_retries"]) -> int: ...
@overload
def get_config_value(key: str) -> str: ... # Catch-all for other strings

def get_config_value(key: str) -> Union[bool, int, str]:
    if key == "debug_mode":
        return True
    if key == "max_retries":
        return 5
    return "default_string_value"

if __name__ == "__main__":
    debug_val = get_config_value("debug_mode") # Checkers disagree on inferred type
    reveal_type(debug_val)

    retries_val = get_config_value("max_retries") # Checkers disagree on inferred type
    reveal_type(retries_val)

    other_val = get_config_value("feature_x_enabled") # Should be str for all
    reveal_type(other_val)