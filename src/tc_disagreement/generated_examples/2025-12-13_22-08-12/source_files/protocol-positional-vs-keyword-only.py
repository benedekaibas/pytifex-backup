# id: protocol-positional-vs-keyword-only


")
    item = cont.get_value()
    reveal_type(item) # This is key for divergence: should be the specific animal type (e.g., Dog)

    print(f"  Container holds a {type(item).__name__} that says: {item.speak()}")

    # Checkers might disagree on the actual type of `item` here.
    # If `item` is `Dog`, `fetch()` is valid. If it's just `Animal`, it's not.
    if isinstance(item, Dog):
        reveal_type(item) # Should be 'Dog'
        print(f"  It's a Dog! It can fetch: {item.fetch()}")
    elif isinstance(item, Cat):
        reveal_type(item) # Should be 'Cat'
        print(f"  It's a Cat! It can purr: {item.purr()}")
    else:
        print("  It's an unknown animal.")

if __name__ == "__main__":
    dog = Dog()
    cat = Cat()

    dog_container = DogContainer(dog)
    cat_container = Container(cat) # Using base Container for cat

    # All agree these are valid assignments.
    reveal_type(dog_container) # DogContainer
    reveal_type(cat_container) # Container[Cat]

    # This is where divergence occurs.
    # Mypy/Pyre might infer 'item' in `process_container` as `Animal` or `Any`,
    # thus flagging errors on `item.fetch()` or `item.purr()`.
    # Pyright/Zuban should correctly infer `Dog` and `Cat` respectively.
    process_container(dog_container)
    process_container(cat_container)

# EXPECTED:
#   mypy: Error: Signature of "simple_func" incompatible with supertype "KwargProtocol" (parameter 'name' does not allow positional arguments)
#   pyright: No error
#   pyre: Error: Signature of "simple_func" incompatible with supertype "KwargProtocol" (or similar error on argument kinds)
#   zuban: Error: Signature of "simple_func" incompatible with supertype "KwargProtocol" (likely similar to mypy)
# REASON: Mypy and Zuban are very strict on the compatibility of positional-only (`/`), positional-or-keyword, and keyword-only (`*`) argument kinds in protocol implementations. A function that allows arguments to be passed positionally (`name: str, age: int`) is considered incompatible with a protocol requiring them to be keyword-only (`*, name: str, age: int`). Pyright is more lenient, allowing this if the argument names and types match, because the function *can* be called with keyword arguments matching the protocol.
from typing import Protocol, Callable

class KwargProtocol(Protocol):
    """A protocol for callables that require keyword-only arguments."""
    def __call__(self, *, name: str, age: int) -> str: ...

def simple_func(name: str, age: int) -> str:
    """A function that takes positional-or-keyword arguments."""
    return f"Name: {name}, Age: {age}"

def another_func(*, first_name: str, user_age: int) -> str:
    """A function that takes keyword-only arguments with different names."""
    return f"First Name: {first_name}, User Age: {user_age}"

if __name__ == "__main__":
    print("