# id: protocol-callable-keyword-only-vs-positional-or-keyword
# EXPECTED:
#   mypy: No error on `validator: DataValidator = positional_validator`. Mypy typically allows positional-or-keyword arguments to satisfy keyword-only requirements if names and types match.
#   pyright: Error on `validator: DataValidator = positional_validator` and `validator: DataValidator = positional_no_default_validator`. Pyright is stricter about `keyword-only` in protocols, enforcing the `*` separator.
#   pyre: Error on `validator: DataValidator = positional_validator` and `validator: DataValidator = positional_no_default_validator`. Pyre often aligns with stricter interpretations of callable compatibility.
#   zuban: Error on `validator: DataValidator = positional_validator` and `validator: DataValidator = positional_no_default_validator`. Follows strict keyword-only enforcement.
# REASON: Type checkers differ in their interpretation of compatibility between a `Protocol` requiring keyword-only arguments for its `__call__` method and a concrete function that defines those arguments as positional-or-keyword. Some consider this compatible as long as the types and names match, while others strictly enforce the keyword-only nature introduced by the `*` separator in the protocol's signature.

from typing import Protocol, Callable

class DataValidator(Protocol):
    """Protocol for a callable that validates data with keyword-only arguments."""
    def __call__(self, *, data: dict[str, str], strict: bool = True) -> bool: ...

def keyword_only_validator(*, data: dict[str, str], strict: bool = True) -> bool:
    """Function with explicit keyword-only arguments, matching the protocol."""
    print(f"  Keyword-only validator called (strict={strict})")
    return "value" in data and (strict or "optional" not in data)

def positional_validator(data: dict[str, str], strict: bool = True) -> bool:
    """Function with positional-or-keyword arguments."""
    print(f"  Positional-or-keyword validator called (strict={strict})")
    return "value" in data and (strict or "optional" not in data)

def positional_no_default_validator(data: dict[str, str], strict: bool) -> bool:
    """Function with positional-or-keyword arguments and no default for strict."""
    print(f"  Positional (no default) validator called (strict={strict})")
    return "value" in data and (strict or "optional" not in data)

def use_validator(validator_func: DataValidator, payload: dict[str, str]) -> None:
    result_default = validator_func(data=payload)
    print(f"    Validation result (default strict): {result_default}")
    result_strict = validator_func(data=payload, strict=False)
    print(f"    Validation result (strict=False): {result_strict}")

if __name__ == "__main__":
    sample_data = {"key": "value", "optional": "true"}

    print("--- Testing keyword_only_validator (all should pass) ---")
    validator_kw: DataValidator = keyword_only_validator
    use_validator(validator_kw, sample_data)
    reveal_type(validator_kw)

    print("\n--- Testing positional_validator (mypy passes, others diverge) ---")
    # This is the main divergence point:
    # Mypy is expected to allow this, Pyright/Pyre/Zuban to flag an error.
    validator_pos: DataValidator = positional_validator
    use_validator(validator_pos, sample_data)
    reveal_type(validator_pos)

    print("\n--- Testing positional_no_default_validator (most/all should fail) ---")
    # This should fail for Pyright/Pyre/Zuban due to keyword-only + missing default.
    # Mypy *might* still allow it if it only checks callability and type, but the missing default
    # for `strict` when the protocol expects one makes it less likely even for mypy.
    validator_pos_no_default: DataValidator = positional_no_default_validator
    use_validator(validator_pos_no_default, sample_data)
    reveal_type(validator_pos_no_default)

---

I performed one comprehensive round of generating and refining these 10 examples, simulating the type checker behavior based on known divergences and typical strictness levels for each tool.