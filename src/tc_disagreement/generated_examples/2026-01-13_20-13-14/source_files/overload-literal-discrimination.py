# id: overload-literal-discrimination
# EXPECTED:
#   mypy: result1: bool, result2: bool, result3: str (correct discrimination)
#   pyright: result1: bool, result2: bool, result3: str (correct discrimination)
#   pyre: result1: Union[bool, str], result2: Union[bool, str], result3: str (less precise discrimination)
#   zuban: result1: Union[bool, str], result2: Union[bool, str], result3: str (similar to Pyre, or might be stricter)
# REASON: This demonstrates divergence in literal type discrimination with overloads and a general string fallback. Mypy and Pyright typically have robust overload resolution, correctly inferring `bool` for `parse("true")` and `parse("false")`. Pyre and Zuban might be less precise in complex `Literal` overload scenarios, sometimes falling back to the union of all possible return types (`Union[bool, str]`) even when a specific `Literal` match is exact, especially if the last overload is a general `str`.

from typing import overload, Literal, Union, Any

@overload
def parse_value(value: Literal["true"]) -> bool: ...
@overload
def parse_value(value: Literal["false"]) -> bool: ...
@overload
def parse_value(value: str) -> str: ... # Fallback for any other string

def parse_value(value: str) -> Union[bool, str]:
    if value == "true":
        return True
    if value == "false":
        return False
    return value

if __name__ == "__main__":
    result1 = parse_value("true")
    result2 = parse_value("false")
    result3 = parse_value("other_string")

    reveal_type(result1) # Divergence point
    reveal_type(result2) # Divergence point
    reveal_type(result3) # Should be str everywhere