from typing import TypedDict, Optional, Required, NotRequired

class BaseConfig(TypedDict, total=True):
    version: int
    debug_mode: bool

class AdvancedConfig(BaseConfig, total=False):
    log_level: NotRequired[str]
    timeout_seconds: Optional[int] # Optional implies NotRequired

class FinalConfig(AdvancedConfig, total=True):
    api_key: Required[str]

def load_config() -> FinalConfig:
    # This multi-line instantiation with an `type: ignore` on an intermediate line
    # might cause mypy#20471 type issues if `api_key` is accidentally omitted
    # and the ignore is not correctly applied.
    config: FinalConfig = {
        'version': 1,
        'debug_mode': True,
        'log_level': 'INFO', # type: ignore[typeddict-item] 
        # This ignore is for 'log_level' being NotRequired in AdvancedConfig
        # but the assignment is happening for FinalConfig.
        # It's intended to suppress a potential error about assigning to an implicitly NotRequired key.
        # If 'api_key' was omitted below, and this ignore wasn't correctly applied,
        # it could mask an error about 'api_key'.
        'timeout_seconds': None,
        'api_key': 'super_secret_key_123'
    }
    return config

if __name__ == "__main__":
    conf = load_config()
    print(f"Loaded config: {conf}")

    # Example of a missing required field that should ideally be caught,
    # but could be masked by `type: ignore` placement if not handled carefully.
    broken_config: FinalConfig = {
        'version': 2,
        'debug_mode': False,
        'log_level': 'DEBUG',
        'timeout_seconds': 60,
        # 'api_key' is intentionally missing to see if checkers would report it
    } # type: ignore[typeddict-item] # This ignore covers the whole statement, potentially masking `api_key` error
    print(f"Broken config (might be missing api_key): {broken_config}")