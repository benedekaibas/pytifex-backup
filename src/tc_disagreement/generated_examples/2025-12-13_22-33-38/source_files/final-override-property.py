# id: final-override-property
# EXPECTED:
#   mypy: Error (Cannot override Final attribute "API_KEY" with a property)
#   pyright: Error (Cannot override Final attribute "API_KEY" with a property)
#   pyre: No error
#   zuban: Error (Cannot override Final attribute "API_KEY" with a property)
# REASON: Pyre treats a property as a method, not a direct attribute, and might not consider it a direct override of a `Final` class variable in the same way mypy, pyright, and zuban do. The latter checkers interpret `Final` as preventing *any* redefinition of that name in subclasses, whether by another class variable or a property.

from typing import Final

class BaseSettings:
    API_KEY: Final[str] = "initial_api_key"
    TIMEOUT: Final[int] = 30

class ProdSettings(BaseSettings):
    # Checkers disagree on whether this is a valid override of a Final class variable
    @property
    def API_KEY(self) -> str:
        return "production_api_key_secure"

    # If uncommented, this would likely be flagged by all for directly overriding Final
    # TIMEOUT: Final[int] = 60

if __name__ == "__main__":
    prod_config = ProdSettings()
    print(f"Prod API Key: {prod_config.API_KEY}")
    reveal_type(prod_config.API_KEY)
    print(f"Base Timeout: {prod_config.TIMEOUT}")