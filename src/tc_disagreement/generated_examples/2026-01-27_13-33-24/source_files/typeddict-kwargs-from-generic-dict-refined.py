from typing_extensions import TypedDict, Required, NotRequired

class GeneralSettings(TypedDict, total=False):
    """Base settings, fields are optional by default."""
    debug: bool
    log_level: str

class EnvironmentSettings(GeneralSettings):
    """Inherits from total=False. New fields are also NotRequired."""
    env_name: str # Implicitly NotRequired

class ProductionSettings(EnvironmentSettings, total=True):
    """
    Explicitly total=True. All inherited fields become Required.
    Therefore, debug, log_level, env_name, and db_conn_str are Required.
    Only max_connections is NotRequired.
    """
    db_conn_str: Required[str]
    max_connections: NotRequired[int] # NotRequired in total=True TypedDict

def create_prod_config(data: dict) -> ProductionSettings:
    """
    Creates a ProductionSettings instance.
    This tests if type checkers can correctly identify missing Required fields
    when initializing a complex TypedDict from a dict literal, especially with inheritance
    and changing 'total' status.

    The critical point of divergence is how type checkers handle
    spreading a generic `dict` (`**data`) into a `TypedDict` constructor.
    Some might fail at the `**data` line itself (conservative), while
    others might attempt to infer the dictionary's structure from call sites
    and flag errors there (more aggressive inference).
    """
    # MODIFICATION: Changed from ProductionSettings(data) to ProductionSettings(**data)
    # This addresses the initial "bad constructor signature" error,
    # now forcing type checkers to analyze the dictionary contents when spread.
    return ProductionSettings(**data)

if __name__ == "__main__":
    # Valid configuration
    valid_data = {
        'debug': False,
        'log_level': 'ERROR',
        'env_name': 'prod',
        'db_conn_str': 'sqlite:///prod.db'
    }
    prod_config1 = create_prod_config(valid_data)
    print(f"Valid ProdConfig: {prod_config1}")

    # Configuration missing a Required field (`db_conn_str`).
    # This should be a type error.
    try:
        missing_db_data = {
            'debug': True,
            'log_level': 'INFO',
            'env_name': 'staging',
            # 'db_conn_str' is missing, but is Required by ProductionSettings
        }
        prod_config2 = create_prod_config(missing_db_data) # Expected: Type Error
        print(f"ProdConfig (missing db_conn_str): {prod_config2}")
    except TypeError as e:
        print(f"Caught runtime TypeError for missing required field (expected): {e}")

    # Configuration with wrong type for a Required field (`log_level` should be str, is int).
    # This should also be a type error.
    try:
        bad_type_data = {
            'debug': True,
            'log_level': 100, # Wrong type
            'env_name': 'dev',
            'db_conn_str': 'postgresql://dev'
        }
        prod_config3 = create_prod_config(bad_type_data) # Expected: Type Error
        print(f"ProdConfig (bad log_level type): {prod_config3}")
    except TypeError as e:
        print(f"Caught runtime TypeError for bad type field (expected): {e}")

    # Valid config with NotRequired field
    valid_with_optional = {
        'debug': False,
        'log_level': 'WARNING',
        'env_name': 'qa',
        'db_conn_str': 'mysql://qa',
        'max_connections': 50 # NotRequired, so fine
    }
    prod_config4 = create_prod_config(valid_with_optional)
    print(f"ProdConfig (with NotRequired): {prod_config4}")