from typing import Literal, Union, reveal_type

def get_db_port(env_mode: Literal["dev", "test", "prod"]) -> Union[Literal[5432], Literal[1234]]:
    """Returns a database port based on environment mode."""
    port = 5432 if env_mode == "dev" or env_mode == "test" else 1234
    reveal_type(port) # Expected: Literal[5432] if "dev"|"test", else Literal[1234], overall Union[Literal[5432], Literal[1234]]
    return port

def connect_to_db(address: str, port: Union[Literal[5432], Literal[1234]]):
    reveal_type(port) # Expected: Union[Literal[5432], Literal[1234]]
    if port == 5432:
        print(f"Connecting to production/dev DB at {address}:{port}")
    else:
        print(f"Connecting to test/staging DB at {address}:{port}")

def configure_system(runtime_env_str: str):
    """
    This function takes a runtime string which cannot be narrowed by type checkers.
    The ternary condition `runtime_env_str == "production"` is dynamic.
    """
    db_connection_port = (
        get_db_port("prod") if runtime_env_str == "production" else get_db_port("test")
    )
    reveal_type(db_connection_port) # Expected: Union[Literal[1234], Literal[5432]] (the full union)

    # The type checker must correctly maintain the Union type for `db_connection_port`
    # because `runtime_env_str == "production"` cannot be resolved statically.
    connect_to_db("db.example.com", db_connection_port) # This should always pass.

    # Another subtle case: ternary affecting literal assigned to a class attribute
    class AppConfig:
        def __init__(self, debug_mode: Literal[True, False]):
            self.debug_mode = debug_mode

    app_debug_setting: Literal[True, False] = (
        True if runtime_env_str.startswith("dev") else False
    )
    reveal_type(app_debug_setting) # Expected: Union[Literal[True], Literal[False]]
    
    app = AppConfig(app_debug_setting) # This should be fine
    reveal_type(app.debug_mode) # Expected: Union[Literal[True], Literal[False]]

if __name__ == "__main__":
    print(f"Dev port: {get_db_port('dev')}")
    print(f"Prod port: {get_db_port('prod')}")

    print("\n--- Testing configure_system ---")
    configure_system("production")
    configure_system("development")
    configure_system("staging")

    print("\nExample demonstrating type inference with Literal in ternary expressions.")
    print("Checks if type checkers correctly handle ternary conditions based on runtime-only string values,")
    print("maintaining Union types where static narrowing is not possible.")