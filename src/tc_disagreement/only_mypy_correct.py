from typing import overload, Literal, Union

@overload
def parse(value: Literal["true"]) -> bool: ...
@overload
def parse(value: Literal["false"]) -> bool: ...
@overload
def parse(value: str) -> str: ...

def parse(value: str) -> Union[bool, str]:
    if value == "true": return True
    if value == "false": return False
    return value

if __name__ == "__main__":
    result1 = parse("true")
    result2 = parse("false")
    result3 = parse("auto")
    print(result1, result2, result3)

# EXPECTED means that the Agent (gemini-2.5-flash) expects the following outcomes of the type checkers
"""
# EXPECTED:
   mypy: result1 type is bool, result2 is bool, result3 is str
   pyright: result1/result2 type is Union[bool, str]
   pyre: result1/result2 type is bool
   zuban: result1/result2 type is str|bool (may warn on overlap)
# REASON: Literal overload discrimination is implemented inconsistently for strings.
"""
"""
# ACTUAL OUTPUT:
#   mypy: error: Overloaded function signatures 1 and 3 overlap with incompatible return types  [overload-overlap]
          error: Overloaded function signatures 2 and 3 overlap with incompatible return types  [overload-overlap]
#   ty: All checks passed!
#   pyrefly:  INFO 0 errors
#   zuban: Success: no issues found in 1 source file
"""
