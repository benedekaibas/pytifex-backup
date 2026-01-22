# id: typeddict-total-mixed-required-notrequired
# EXPECTED:
#   mypy: No error. All `reveal_type`s should be `Union[Type, None]` for `.get()`. `total=False` propagates.
#   pyright: No error. All `reveal_type`s should be `Type | None` for `.get()`. `Required` overrides `total=False` for specific keys.
#   pyre: Subtle error/difference. Pyre might treat 'optional_param' as strictly missing if `total=False` isn't fully propagated for inherited keys, leading to an error on `td.get('optional_param')` or incorrect `reveal_type`. Or it might raise an error during assignment if it misinterprets the optionality.
#   zuban: No error. Aims for precise TypedDict semantics.
# REASON: The interaction between `total=False` on a base `TypedDict` and explicit `Required`/`NotRequired` in a derived one can lead to different interpretations of key optionality. This divergence is often seen in how `.get()` is typed for keys whose optionality is implicitly inherited versus explicitly defined, or in how `total=False` inheritance affects new keys.

from typing import TypedDict, Union
from typing_extensions import Required, NotRequired

class BaseOpts(TypedDict, total=False):
    """Base TypedDict where all keys are optional by default."""
    config_id: int
    log_file: str

class AdvancedOpts(BaseOpts):
    """Derived TypedDict, mixing explicit optionality and inheriting total=False."""
    # new_param is implicitly NotRequired due to inheriting total=False
    new_param: float
    
    # Required keys explicitly override total=False for themselves
    api_key: Required[str]
    
    # Explicitly NotRequired (redundant given total=False, but allowed)
    debug_mode: NotRequired[bool]

def process_options(opts: AdvancedOpts) -> None:
    # 'api_key' is Required, but .get() always returns Optional.
    api_k = opts.get('api_key')
    reveal_type(api_k) # EXPECTED: str | None (all should agree)
    if api_k:
        print(f"API Key: {api_k}")

    # 'config_id' is implicitly NotRequired from BaseOpts(total=False)
    cfg_id = opts.get('config_id')
    reveal_type(cfg_id) # EXPECTED: int | None (pyre might differ here or on the call)
    if cfg_id is not None:
        print(f"Config ID: {cfg_id}")

    # 'new_param' is implicitly NotRequired as it's a new key in a total=False derived TypedDict.
    new_p = opts.get('new_param')
    reveal_type(new_p) # EXPECTED: float | None (pyre might differ here)
    if new_p is not None:
        print(f"New Param: {new_p}")

    # 'debug_mode' is explicitly NotRequired.
    dbg_m = opts.get('debug_mode')
    reveal_type(dbg_m) # EXPECTED: bool | None (all should agree)
    if dbg_m is not None:
        print(f"Debug Mode: {dbg_m}")

if __name__ == "__main__":
    # Valid config: includes 'api_key' (Required), others are optional
    config1: AdvancedOpts = {'api_key': 'abc-123', 'config_id': 101, 'new_param': 3.14}
    print("--- Processing config1 ---")
    process_options(config1)

    # Config with only required key
    config2: AdvancedOpts = {'api_key': 'xyz-456'}
    print("\n--- Processing config2 ---")
    process_options(config2)

    # This assignment would fail for all checkers if 'api_key' is missing.
    # config3: AdvancedOpts = {'config_id': 202}

---

### Snippet 4: `ParamSpec` with Decorators on Class Methods