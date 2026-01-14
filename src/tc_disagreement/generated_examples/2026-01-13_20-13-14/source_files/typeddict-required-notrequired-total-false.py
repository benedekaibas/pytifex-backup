# id: typeddict-required-notrequired-total-false
# EXPECTED:
#   mypy: No error (for reveal_type, but might show Dict[str, Any] for .get())
#   pyright: Reveal type: `int | None` (correctly infers optionality). Might error on direct access if total=False and not Required.
#   pyre: Reveal type: `Optional[int]` (similar to pyright)
#   zuban: Reveal type: `Union[int, None]` (similar to pyright/pyre)
# REASON: The interaction between `total=False` on a base `TypedDict` and `Required`/`NotRequired` in a subclass is complex. `total=False` implies all keys are `NotRequired` by default. `Required` explicitly makes a key mandatory. `NotRequired` explicitly makes it optional. The divergence lies in how checkers infer the *exact* optionality for keys implicitly optional from `total=False` (like 'x') when accessed via `td.get()`. Some might infer `Optional[int]`, others `Union[int, None]`, and some might have subtle errors on direct access or assignment depending on their strictness around `TypedDict` inheritance and `total` semantics.

from typing import TypedDict, Any
from typing_extensions import Required, NotRequired

class BaseConfig(TypedDict, total=False):
    x: int # Implied NotRequired because total=False
    common_prop: str

class DetailedConfig(BaseConfig):
    y: Required[str] # Explicitly required
    z: NotRequired[bool] # Explicitly not required
    additional: Any # Implied Required because total=True by default for subclasses

def process_config(td: DetailedConfig) -> None:
    # Accessing keys:
    # mypy: reveal_type(td.get('x')) # Expected: Union[int, None]
    # pyright: reveal_type(td.get('x')) # Expected: int | None
    # pyre: reveal_type(td.get('x')) # Expected: Optional[int]
    # zuban: reveal_type(td.get('x')) # Expected: Union[int, None]

    # The divergence is often not just in the reveal_type, but in whether direct access like td['x'] is allowed,
    # or how missing keys are treated.
    # The 'get' method's return type is the clearest point for divergence.

    val_x = td.get('x')
    val_y = td['y']
    val_z = td.get('z')

    if val_x is not None:
        print(f"x: {val_x + 1}")
    print(f"y: {val_y.upper()}")
    if val_z is not None:
        print(f"z: {not val_z}")

if __name__ == "__main__":
    config1: DetailedConfig = {'y': 'required_y', 'z': True, 'common_prop': 'base'}
    # config2: DetailedConfig = {'y': 'required_y'} # Should error for missing 'additional' and 'common_prop' implicitly
    config3: DetailedConfig = {'y': 'another', 'x': 100, 'additional': 'info', 'common_prop': 'more'}

    # Using reveal_type on the 'get' results directly in mypy/pyright/pyre via comments.
    # The divergence is subtle about `Optional[int]` vs `Union[int, None]` or even `Any` in older versions.
    # The primary divergence is in how explicitly `None` is included in the type if the key is optional.
    reveal_type(config3.get('x')) # Type checker will show its interpretation here
    reveal_type(config1.get('z'))