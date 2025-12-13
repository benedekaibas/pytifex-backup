# id: typeguard-generic-narrowing


")
    use_reader(network_reader_instance)       # This should be fine for all, Protocol's default is compatible with no default in implementation.
    use_reader(network_reader_instance, 100)

# EXPECTED:
#   mypy: Error: List item 0 has incompatible type "str"; expected "object" (or similar error on `data.append` due to `data` not being fully `list[str]`)
#   pyright: No error (correctly narrows `data` to `list[str]`)
#   pyre: Error: Incompatible return type for `append` (or similar, might not fully narrow `list[object]` to `list[str]`)
#   zuban: No error (likely follows pyright's robust narrowing)
# REASON: Pyright's type narrowing with TypeGuard is very powerful and understands how to refine generic types like `list[object]` to `list[str]`. Mypy and Pyre, while supporting TypeGuard, sometimes struggle with fully refining generics within collections, leading to errors when attempting operations specific to the narrowed generic type (e.g., calling `append` with a `str` on `list[str]` which they might still perceive as `list[object]`).
from typing import TypeGuard, TypeVar, List, Union

T = TypeVar('T')

def is_list_of(val: list[object], type_: type[T]) -> TypeGuard[list[T]]:
    """Checks if all elements in a list are of a given type."""
    return all(isinstance(x, type_) for x in val)

def process(data: List[object]) -> None:
    print(f"Processing data (initial type: {type(data)}): {data}")
    if is_list_of(data, str):
        # After this line, 'data' should be narrowed to List[str]
        print(f"  Narrowed 'data' to list[str]. Appending 'new_string'.")
        data.append("new_string") # Mypy/Pyre might error here, thinking 'data' is still List[object] or List[Union[str, object]]
        print(f"  After append: {data}")
        first_item = data[0]
        # This should be safe if data is List[str], but might be a problem if it's List[object]
        if first_item:
            reveal_type(first_item) # Should be 'str'
            print(f"  First item (type: {type(first_item)}) length: {len(first_item)}")
    else:
        print("  Data is not a list of strings.")

if __name__ == "__main__":
    mixed_list: List[object] = ["hello", 123, "world"]
    str_list: List[object] = ["alpha", "beta"]

    process(str_list)
    print("\n" + "="*30 + "\n")
    process(mixed_list)

# EXPECTED:
#   mypy: Error: Key 'x' of TypedDict "Child" is optional (due to base class total=False), but accessed directly (td['x']). (Or similar: might infer td.get('x') returns int, not Optional[int])
#   pyright: No error. `reveal_type` for `td.get('x')` is `Union[int, None]`.
#   pyre: Error: Incompatible return type for `td.get('x')` (might incorrectly infer `x` is `int` or misinterpret optionality).
#   zuban: No error. `reveal_type` for `td.get('x')` is `Union[int, None]`.
# REASON: Pyright and Zuban correctly prioritize explicit `Required`/`NotRequired` over the `total` keyword from base classes, especially when `total=False` on the base. Mypy and Pyre can sometimes get confused by the interaction, potentially inheriting `total=False` in an unexpected way or not correctly inferring the optionality of fields from a `total=False` base when the child also uses explicit `Required`/`NotRequired`.
from typing import TypedDict, Required, NotRequired, Union

class Base(TypedDict, total=False):
    x: int
    base_prop: str

class Child(Base):
    y: Required[str]  # 'y' is required in Child, even though Base is total=False
    z: NotRequired[int] # 'z' is explicitly not required in Child

def test_child_typeddict(td: Child) -> None:
    # 'y' should always be present (str)
    reveal_type(td['y']) # Should be 'str'
    print(f"td['y']: {td['y']}")

    # 'z' is optional (Union[int, None])
    reveal_type(td.get('z')) # Should be 'Union[int, None]'
    print(f"td.get('z'): {td.get('z')}")

    # 'x' from Base(total=False) should still be optional (Union[int, None])
    reveal_type(td.get('x')) # This is the main point of divergence: Mypy/Pyre might misinterpret
    print(f"td.get('x'): {td.get('x')}")

    # 'base_prop' from Base(total=False) should also be optional
    reveal_type(td.get('base_prop'))
    print(f"td.get('base_prop'): {td.get('base_prop')}")

if __name__ == "__main__":
    # Valid instances of Child TypedDict
    td1: Child = {'y': 'hello', 'x': 5}
    td2: Child = {'y': 'world', 'z': 10, 'base_prop': 'base'}
    td3: Child = {'y': 'test'} # 'x', 'z', 'base_prop' are optional

    print("