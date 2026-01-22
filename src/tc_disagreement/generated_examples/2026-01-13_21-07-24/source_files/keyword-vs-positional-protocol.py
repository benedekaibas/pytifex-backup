# id: keyword-vs-positional-protocol
# category: keyword-vs-positional
# expected: mypy: error, pyrefly: ok, zuban: ok, ty: ok

from typing import Protocol, runtime_checkable

@runtime_checkable
class HasProcessor(Protocol):
    """
    Protocol method with a positional-or-keyword argument ('value')
    and a keyword-only argument ('factor').
    """
    def process(self, value: int, *, factor: float = 1.0) -> float: ...

class StrictProcessor:
    """
    Implements the protocol by making 'value' keyword-only.
    This changes 'value' from positional-or-keyword to keyword-only.
    """
    def process(self, *, value: int, factor: float = 1.0) -> float:
        return value * factor

class LooseProcessor:
    """
    Implements the protocol by making 'factor' positional-or-keyword.
    This makes the method *more flexible*, which is generally allowed by PEP 544.
    """
    def process(self, value: int, factor: float = 1.0) -> float:
        return value * factor

def operate(obj: HasProcessor) -> None:
    """
    Function that calls the `process` method, adhering to the protocol's signature.
    """
    print(f"Processing object: {type(obj).__name__}")
    # These calls are valid for the `HasProcessor` protocol.
    # They should only be statically allowed if `obj` truly implements `HasProcessor`.
    print(f"  Result (pos-arg, kw-arg): {obj.process(10, factor=2.0)}")
    print(f"  Result (kw-arg, kw-arg): {obj.process(value=20, factor=3.0)}")
    print(f"  Result (pos-arg, default): {obj.process(30)}")

if __name__ == "__main__":
    lp = LooseProcessor()
    print("--- Testing LooseProcessor (should be OK for all) ---")
    operate(lp) # This should pass for all checkers and at runtime.

    sp = StrictProcessor()
    print("\n--- Testing StrictProcessor (Divergence) ---")
    # DIVERGENCE POINT:
    # Mypy considers `StrictProcessor` NOT to implement `HasProcessor` because
    # the parameter `value` changed from `positional-or-keyword` in the protocol
    # to `keyword-only` in the implementation. This makes the implementation
    # *less flexible* than the protocol, which PEP 544 disallows.
    # Other type checkers might allow this, or be more lenient on parameter kinds.
    operate(sp) # mypy: error (at the `operate(sp)` call site), others: ok.