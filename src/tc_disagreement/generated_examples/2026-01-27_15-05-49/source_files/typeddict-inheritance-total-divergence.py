from typing import TypedDict, Required, NotRequired, reveal_type

class BaseSettings(TypedDict, total=True):
    log_level: str
    timeout: int

class ExtendedSettings(BaseSettings, total=False): # All inherited fields become NotRequired
    api_key: str # Becomes NotRequired due to total=False on ExtendedSettings
    feature_flag: NotRequired[bool]

class FinalSettings(ExtendedSettings, total=True): # Inherited fields from ExtendedSettings should become Required again
    # Expected behavior for fields in FinalSettings:
    # log_level: Required[str] (inherited from BaseSettings, became NotRequired in ExtendedSettings, now Required due to FinalSettings total=True)
    # timeout: Required[int] (same as log_level)
    # api_key: Required[str] (inherited from ExtendedSettings, became NotRequired there, now Required due to FinalSettings total=True)
    # feature_flag: NotRequired[bool] (explicitly NotRequired, should remain so)
    database_url: Required[str]
    retries: NotRequired[int]

def validate_config(cfg: FinalSettings):
    reveal_type(cfg)
    
    # Accessing fields to see if Required/NotRequired is inferred correctly
    log_level = cfg['log_level']
    reveal_type(log_level) # Expected: str (Required due to FinalSettings total=True)
    
    api_key = cfg['api_key']
    # EXPECTED: str (Required due to FinalSettings total=True).
    # Divergence point: MyPy's reveal_type for 'cfg' itself shows 'api_key?'.
    # This implies MyPy considers it NotRequired, which contradicts strict TypedDict total=True semantics for inherited fields.
    reveal_type(api_key) 
    
    feature_flag = cfg.get('feature_flag')
    reveal_type(feature_flag) # Expected: Union[bool, None] (NotRequired)
    
    database_url = cfg['database_url']
    reveal_type(database_url) # Expected: str (Required)
    
    retries = cfg.get('retries')
    reveal_type(retries) # Expected: Union[int, None] (NotRequired)

def create_valid_final_config() -> FinalSettings:
    return {
        "log_level": "INFO",
        "timeout": 30,
        "api_key": "some_secret", # Required in FinalSettings
        "database_url": "postgres://db.example.com" # Required in FinalSettings
        # feature_flag and retries are NotRequired, so can be omitted
    }

def create_invalid_final_config_missing_required():
    # This dictionary is missing 'api_key'.
    # If 'api_key' is interpreted as Required (as per strict TypedDict `total=True` rules),
    # this dictionary should trigger a type error.
    # If 'api_key' is interpreted as NotRequired (as MyPy's initial 'reveal_type' output for 'cfg' implies),
    # this dictionary should NOT trigger an error for 'api_key'.
    return {
        "log_level": "DEBUG",
        "timeout": 60,
        "database_url": "sqlite:///test.db",
        "feature_flag": True
    }

if __name__ == "__main__":
    valid_cfg = create_valid_final_config()
    validate_config(valid_cfg)

    # This line exposes the divergence:
    # - Some checkers (e.g., Pyright) correctly identify 'api_key' as Required
    #   and flag this as an error for missing 'api_key'.
    # - Other checkers (e.g., MyPy based on its 'reveal_type' for 'api_key?') might
    #   either not flag an error for 'api_key', or might exhibit inconsistent behavior
    #   (e.g., MyPy sometimes reports other present required keys as missing in this scenario).
    # The disagreement on whether 'api_key' is required or not (and thus whether this is an error)
    # constitutes the real divergence.
    invalid_cfg = create_invalid_final_config_missing_required()
    validate_config(invalid_cfg) 
    
    print("\nExample demonstrating complex TypedDict inheritance with mixed `total` and `Required`/`NotRequired` fields, highlighting a divergence in `total=True` re-evaluation of inherited fields.")