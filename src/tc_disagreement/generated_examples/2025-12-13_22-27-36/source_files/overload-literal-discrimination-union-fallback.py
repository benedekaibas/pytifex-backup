# id: overload-literal-discrimination-union-fallback
# EXPECTED:
#   mypy: `result1` -> `bool`, `result2` -> `int`, `result3` -> `float`, `result4` -> `str`. Correct discrimination.
#   pyright: `result1` -> `bool`, `result2` -> `int`, `result3` -> `float`, `result4` -> `str`. Correct discrimination.
#   pyre: `result1` -> `Union[bool, int, float, str]`, `result2` -> `Union[bool, int, float, str]`, etc. Pyre might fail to discriminate fully, especially with multiple Literal overloads and a catch-all fallback, leading to a wider union type.
#   zuban: `result1` -> `bool`, `result2` -> `int`, `result3` -> `float`, `result4` -> `str`. Correct discrimination.
# REASON: Type checkers differ in their ability to perform precise overload resolution, particularly when `Literal` types are used for discrimination alongside a general "catch-all" overload. Some checkers correctly identify the most specific matching overload for a given literal argument, while others might fall back to a wider union of all possible return types from all overloads, even for arguments that clearly match a specific `Literal`.

from typing import overload, Literal, Union

@overload
def parse_config_value(value: Literal["true", "false"]) -> bool: ...
@overload
def parse_config_value(value: Literal["0", "1", "2"]) -> int: ...
@overload
def parse_config_value(value: Literal["3.14", "2.71"]) -> float: ...
@overload
def parse_config_value(value: str) -> str: ... # Catch-all for any other string

def parse_config_value(value: str) -> Union[bool, int, float, str]:
    """Parses a configuration string into a more specific type."""
    if value in ("true", "false"):
        return value == "true"
    if value in ("0", "1", "2"):
        return int(value)
    if value in ("3.14", "2.71"):
        return float(value)
    return value

if __name__ == "__main__":
    # Test literal string arguments
    result1 = parse_config_value("true")
    reveal_type(result1) # EXPECTED: bool (pyre might show Union[bool, int, float, str])

    result2 = parse_config_value("1")
    reveal_type(result2) # EXPECTED: int (pyre might show Union[bool, int, float, str])

    result3 = parse_config_value("3.14")
    reveal_type(result3) # EXPECTED: float (pyre might show Union[bool, int, float, str])

    result4 = parse_config_value("any_other_string")
    reveal_type(result4) # EXPECTED: str (all should agree, as it hits the fallback)

    # Test with a variable of type str (should always resolve to the widest union)
    my_str_var: str = "dynamic_value"
    result_var = parse_config_value(my_str_var)
    reveal_type(result_var) # EXPECTED: Union[bool, int, float, str] (all should agree here)

---

### Snippet 8: `Final` Attribute Override with Property