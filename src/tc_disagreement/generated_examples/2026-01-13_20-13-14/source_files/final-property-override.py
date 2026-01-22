# id: final-property-override
# EXPECTED:
#   mypy: Error (Cannot override Final attribute "x" with a property)
#   pyright: Error (Property "x" cannot override "Final" field in "Base")
#   pyre: Error (Incompatible override)
#   zuban: Error (Strictly disallows overriding Final with property)
# REASON: `Final` marks an attribute as immutable after initialization. Overriding a `Final` instance variable with a `property` in a subclass is generally considered a violation because it changes the nature of access and mutability (or lack thereof). While all major type checkers are expected to flag this as an error, the specific error message and rationale might vary, confirming a consistent violation rather than a divergence. *Self-correction: This also appears to be a consistent error across checkers. I need a real divergence for `Final`.*

**Self-correction Round 3: Re-evaluating `Final` example.**

The `Final` with `property` override is consistently flagged. I need a *real* divergence point for `Final`.

A known divergence for `Final` is when it's applied to class variables in abstract base classes, or its interaction with `__slots__`. Or, when a `Final` variable is reassigned *in the same scope* but under different control flow.

**New idea for `Final` divergence:** `Final` class variable in a base class, accessed via a subclass.