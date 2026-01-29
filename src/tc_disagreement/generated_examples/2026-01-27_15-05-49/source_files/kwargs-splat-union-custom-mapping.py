from typing import Union, Mapping, KeysView, Any, reveal_type, Iterator

class FlexibleConfigSource:
    """
    A class that provides mapping-like access but does not formally inherit from Mapping
    and critically, does not implement `items()` needed for `**` operator at runtime.
    """
    def __init__(self, config_data: dict[str, Any]):
        self._config = config_data
    
    def keys(self) -> KeysView[str]:
        return self._config.keys()
    
    def __getitem__(self, key: str) -> Any:
        return self._config[key]
    
    # Missing .items() method. This is where runtime `**` operator will fail.

def apply_settings(**settings: str) -> dict[str, str]: # Expects all values to be str
    reveal_type(settings) # Expected: dict[str, str]
    print(f"Applied settings: {settings}")
    return settings

def test_flexible_splat(
    source_union: Union[dict[str, str], FlexibleConfigSource],
    direct_dict: dict[str, str],
    direct_flex: FlexibleConfigSource
):
    # Testing direct splat into a dict literal
    reveal_type({**source_union}) # Does it correctly infer dict[str, str] or dict[Unknown, Unknown]?
    reveal_type({**direct_dict})  # Expected: dict[str, str]
    reveal_type({**direct_flex})  # Expected: dict[Unknown, Unknown] or error due to missing items()

    # Testing splat into a function call with type-hinted kwargs
    apply_settings(**source_union) # Will checker allow this if `source_union` could be `FlexibleConfigSource`?
    apply_settings(**direct_dict) # Should be fine
    apply_settings(**direct_flex) # Should cause runtime TypeError, checker might miss.

if __name__ == "__main__":
    my_dict = {"host": "localhost", "port": "8080"}
    my_flex_source = FlexibleConfigSource({"user": "admin", "theme": "dark"})
    
    print("Testing kwargs splat with a Union involving a custom mapping-like class (missing items()).")
    print("This should cause a runtime TypeError for `FlexibleConfigSource` via `**` operator.")

    # Uncommenting the lines below will cause a runtime TypeError for FlexibleConfigSource.
    # test_flexible_splat(my_dict, my_dict, my_flex_source) # Call with dict as Union
    # test_flexible_splat(my_flex_source, my_dict, my_flex_source) # Call with FlexibleConfigSource as Union
    
    # For type checking only, without runtime crash:
    reveal_type({**my_dict})
    reveal_type({**my_flex_source})
    
    # The `apply_settings` calls are the key:
    print("\nRunning `reveal_type` and demonstrating `apply_settings` calls for type checking:")
    apply_settings(**my_dict)
    # The following line is expected to be flagged by a strict type checker
    # because FlexibleConfigSource cannot be splatted into kwargs at runtime due to missing items().
    # apply_settings(**my_flex_source)