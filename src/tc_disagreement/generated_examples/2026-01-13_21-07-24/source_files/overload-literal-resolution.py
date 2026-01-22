# id: overload-literal-resolution
# category: overload-literals
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import overload, Literal, Union

# Overload 1: Most specific for "apple"
@overload
def get_fruit_info(fruit: Literal["apple"]) -> dict[str, str]: ...
# Overload 2: Less specific, includes "apple" and "orange". This overlaps with Overload 1.
@overload
def get_fruit_info(fruit: Literal["apple", "orange"]) -> dict[str, int]: ...
# Overload 3: General string, least specific.
@overload
def get_fruit_info(fruit: str) -> dict[str, bool]: ...

def get_fruit_info(fruit: str) -> Union[dict[str, str], dict[str, int], dict[str, bool]]:
    """Implementation for get_fruit_info."""
    if fruit == "apple":
        return {"color": "red"}
    elif fruit == "orange":
        return {"segments": 10}
    else:
        return {"available": False}

if __name__ == "__main__":
    # DIVERGENCE POINT: Calling with "apple"
    # Overload resolution order is critical here. Mypy's rule is to pick the
    # *first* matching overload in the source order.
    # Therefore, `get_fruit_info("apple")` should resolve to Overload 1,
    # resulting in `apple_info` being `dict[str, str]`.
    # Other type checkers might use different heuristics (e.g., longest literal list wins),
    # leading to `apple_info` being `dict[str, int]` (from Overload 2), or a `Union`.
    apple_info = get_fruit_info("apple")
    
    # If `apple_info` is inferred as `dict[str, int]`, then accessing "color"
    # or assigning its value to `str` will be an error, as `dict[str, int]`
    # does not guarantee a "color" key with a string value.
    apple_color: str = apple_info["color"] # This assignment is the divergence test.
    print(f"Apple info color: {apple_color}")

    # This should unambiguously resolve to Overload 2 for all checkers.
    orange_info = get_fruit_info("orange")
    orange_segments: int = orange_info["segments"]
    print(f"Orange info segments: {orange_segments}")

    # This should unambiguously resolve to Overload 3 for all checkers.
    banana_info = get_fruit_info("banana")
    banana_available: bool = banana_info["available"]
    print(f"Banana info available: {banana_available}")