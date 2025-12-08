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
#   mypy: error: Cannot override final attribute "x" (previously declared in base class "Base")
#   ty: All checks passed!
#   pyrefly: ERROR `x` is declared as final in parent class `Base` [bad-override]
#   zuban: error: Cannot override final attribute "x" (previously declared in base class "Base")

"""
