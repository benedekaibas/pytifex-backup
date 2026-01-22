# id: newtype-list-covariance
# EXPECTED:
#   mypy: Error (Incompatible types in assignment (expression has type "list[int]", variable has type "list[ProductId]"))
#   pyright: Error (Type "list[int]" is not assignable to type "list[ProductId]")
#   pyre: Error (Expected `List[ProductId]`, got `List[int]`)
#   zuban: Error (Strictly disallows, as NewType is nominal and List is invariant)
# REASON: `NewType` creates a distinct nominal type, even though it's a runtime alias. `List` is invariant in Python's typing. Therefore, `List[int]` should *never* be assignable to `List[ProductId]`. While all modern type checkers should strictly enforce this, older versions or checkers with less mature `NewType` support sometimes exhibited leniency. This example confirms the expected strictness across the board for `List` invariance, highlighting that any divergence would be a bug. *Self-correction: Since all major checkers consistently error here, this is not a divergence. I need to replace it.*

**Self-correction Round 2: Re-evaluating `NewType` example.**

The `NewType` and `List` invariance example correctly points out that it *should* error everywhere. So, it's not a divergence point. I need a different example for `NewType` divergence.

A common subtle divergence for `NewType` is around its interaction with structural subtyping or methods of the base type when accessed via `NewType` variable.

**New idea for `NewType` divergence:** Accessing attributes or methods of the base type on a `NewType` instance.