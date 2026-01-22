# id: super-in-generic-classes


")
    if_instance: IntFactory = int_factory.create()
    print(f"  Created type: {type(if_instance)}")
    processed_int = if_instance.process(10)
    print(f"  Processed int: {processed_int}")

    # This tests the generic function behavior.
    # Mypy/Pyre might complain if `f_instance` isn't correctly inferred as `ConcreteFactory`
    # or `IntFactory` after `factory.create()`.
    made_str_factory, original_item = make_and_use(str_factory, "test_item")
    reveal_type(made_str_factory) # Should be ConcreteFactory
    print(f"  From make_and_use, factory type: {type(made_str_factory)}, processed item: {original_item}")
    # Following operation would fail if `made_str_factory` isn't `ConcreteFactory`
    # e.g., if it was `AbstractFactory[str]`, `.process` might be fine, but other methods might not.

# EXPECTED:
#   mypy: Error: Incompatible types (expression has type "BaseProcessor[str]", base class "BaseProcessor" has type "BaseProcessor[T]") (on `super().__init__`) or similar generic argument mismatch. Also, `reveal_type(base_result)` might be `Any` or `T`.
#   pyright: No error. `reveal_type(base_result)` is `str`.
#   pyre: Error: Incompatible super call (or similar, might lose generic parameter `T` for `super()` call or return type).
#   zuban: No error. `reveal_type(base_result)` is `str`.
# REASON: Mypy and Pyre can sometimes struggle with correctly inferring and propagating generic arguments when calling `super().__init__` or other methods in a subclass of a generic class, especially if the subclass fixes a type parameter. This can lead to type errors on the `super()` call itself or incorrect inference of return types from `super()` calls in overridden methods. Pyright and Zuban are generally more robust in preserving generic type information across `super()` calls.
from typing import Generic, TypeVar, Any

T = TypeVar('T')

class BaseProcessor(Generic[T]):
    def __init__(self, data: T) -> None:
        self.data = data
        print(f"BaseProcessor: Initialized with {type(data).__name__}: {data}")

    def process(self) -> T:
        print(f"BaseProcessor: Processing '{self.data}'")
        return self.data

class StringProcessor(BaseProcessor[str]):
    def __init__(self, text: str) -> None:
        # Mypy/Pyre might flag an error here, struggling with `super()`'s generic `T`
        # when `StringProcessor` fixes `T` to `str`.
        print(f"StringProcessor: Initializing with '{text}'...")
        super().__init__(text)
        self.upper_text = text.upper()

    def process(self) -> str:
        # Pyright/Zuban infer `super().process()` returns `str` here.
        # Mypy/Pyre might infer `Any` or `T` from `BaseProcessor`, leading to potential errors
        # if `upper()` is called directly on `super().process()` without a cast.
        base_result = super().process()
        reveal_type(base_result) # This is key for divergence: should be 'str'
        print(f"StringProcessor: Appending upper text to '{base_result}'")
        return base_result + self.upper_text

def use_processor[P: BaseProcessor[Any]](processor: P) -> Any:
    """A generic function to use any BaseProcessor."""
    print(f"\n