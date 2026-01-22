from typing import Final

class Base:
    x: Final[int] = 1

class Derived(Base):
    @property
    def x(self) -> int:
        return 2

if __name__ == "__main__":
    print(Derived().x)

# EXPECTED means that the Agent (gemini-2.0-flash) expects the following outcomes of the type checkers
"""
# EXPECTED:
   mypy: Error - "Derived.x" overrides final attribute from base
   ty: No error
   pyrefly: Error
   zuban: Error
# REASON: Some checkers do not enforce "Final" on attributes when overridden by properties.

"""
"""
# ACTUAL OUTPUT:
#   mypy: error: Cannot override final attribute "x" (previously declared in base class "Base")
#   ty: All checks passed!
#   pyrefly: ERROR `x` is declared as final in parent class `Base` [bad-override]
#   zuban: error: Cannot override final attribute "x" (previously declared in base class "Base")

"""
