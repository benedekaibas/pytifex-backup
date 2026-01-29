from typing import NewType, List, reveal_type, Protocol

# 1. Introduce a Protocol for types that have a 'value' attribute
class HasValue(Protocol):
    value: float

class PriceItem:
    def __init__(self, value: float):
        self.value = value
    # __gt__ expects 'PriceItem' for the 'other' argument
    def __gt__(self, other: 'PriceItem') -> bool:
        return self.value > other.value
    def __eq__(self, other: object) -> bool:
        return isinstance(other, PriceItem) and self.value == other.value

Money = NewType("Money", PriceItem)

# 2. Define a function that expects the Protocol type
def get_item_value(item: HasValue) -> float:
    """Extracts the value from an item conforming to HasValue protocol."""
    return item.value

def compare_money_in_list(items: List[Money]) -> bool:
    if len(items) < 2:
        return True
    m1 = items[0]
    m2 = items[1]
    
    reveal_type(m1) # Expected: Money
    reveal_type(m2) # Expected: Money

    # 3. This is the point of divergence:
    # Mypy's strict interpretation of NewType states that 'Money' is distinct from 'PriceItem'
    # at the type-checking level.
    # Therefore, when 'm1 > m2' is evaluated, it resolves to 'm1.__gt__(m2)'.
    # The __gt__ method of PriceItem expects 'other: PriceItem'.
    # Passing 'm2' (which is 'Money') as 'other' should be a type error according to mypy's strictness.
    # Other type checkers might be more lenient and allow NewType to implicitly behave like its base type
    # for such operations.

    # This line has been changed from the original code (v1 > v2)
    reveal_type(m1 > m2) # Expected: bool. Mypy reveals bool but also reports an error.
    return m1 > m2

if __name__ == "__main__":
    p1 = PriceItem(10.0)
    p2 = PriceItem(20.0)
    m1_val = Money(p1)
    m2_val = Money(p2)
    
    print(f"Comparison in list: {compare_money_in_list([m1_val, m2_val])}")
    # This direct call to get_item_value (which expects a Protocol) should still pass
    # because NewType instances *are* treated as conforming to Protocols that their base type implements.
    print(f"Direct comparison using value via function: {get_item_value(m1_val) > get_item_value(m2_val)}")