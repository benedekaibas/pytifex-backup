from typing import TypedDict, Required, NotRequired

# A base TypedDict where all fields are implicitly Required (default total=True)
class StrictConfigBase(TypedDict, total=True):
    """
    Defines configuration fields that are implicitly required.
    """
    config_id: int
    config_name: str

# Another base TypedDict where all fields are implicitly NotRequired (total=False)
class OptionalFeaturesBase(TypedDict, total=False):
    """
    Defines optional features that are implicitly not required.
    """
    feature_a_enabled: bool
    feature_b_value: float

# ComplexConfig inherits from both. According to PEP 589:
# "If any of the base classes has total=False, then the new TypedDict type has total=False."
# Thus, ComplexConfig itself is `total=False`.
# The divergence point is how fields inherited from `StrictConfigBase` (which were implicitly Required)
# are treated in `ComplexConfig` (which is `total=False`).
# PEP 655 states: "Required/NotRequired take precedence over the 'total' parameter,
# regardless of whether the field is introduced in the current TypedDict or inherited from a base class."
# This implies that `config_id` and `config_name` *should* become `NotRequired`
# because `ComplexConfig` is `total=False` and they are not explicitly marked `Required`.
# However, some type checkers (e.g., mypy) might retain the "implicitly Required" status
# for fields inherited from `total=True` bases, even when the child is `total=False`.
class ComplexConfig(StrictConfigBase, OptionalFeaturesBase):
    """
    Combines strict and optional configurations, with its own specific requirements.
    This TypedDict itself is total=False due to inheriting OptionalFeaturesBase.
    """
    # This field is explicitly Required, overriding ComplexConfig's total=False default for new fields.
    required_setting: Required[str]
    # This field is explicitly NotRequired, consistent with ComplexConfig's total=False default.
    optional_comment: NotRequired[str]

def process_complex_config(data: ComplexConfig) -> None:
    """
    Processes the complex configuration data.
    """
    print(f"Config ID: {data.get('config_id', 'N/A')}")
    print(f"Config Name: {data.get('config_name', 'N/A')}")
    print(f"Feature A Enabled: {data.get('feature_a_enabled', False)}")
    print(f"Feature B Value: {data.get('feature_b_value', 0.0)}")
    print(f"Required Setting: {data['required_setting']}")
    print(f"Optional Comment: {data.get('optional_comment', 'No comment')}\n")

if __name__ == "__main__":
    # This dictionary is missing 'config_id' and 'config_name' (originally from StrictConfigBase, total=True).
    # It is also missing 'feature_a_enabled' and 'feature_b_value' (from OptionalFeaturesBase, total=False).
    # It *must* include 'required_setting' (explicitly Required in ComplexConfig).
    #
    # The divergence occurs on the fields from `StrictConfigBase`:
    # Will `config_id` and `config_name` remain `Required` (leading to an error here),
    # or will they become `NotRequired` due to `ComplexConfig` being `total=False` (allowing this to pass)?
    test_config_data_missing_inherited_required: ComplexConfig = {
        "required_setting": "enabled",
        "optional_comment": "This is fine, it's optional",
        # 'config_id' and 'config_name' are MISSING.
        # Mypy and some others would flag this as an error.
        # Other checkers might pass, interpreting `total=False` as overriding
        # implicit requirements from parent `total=True` TypedDicts.
    }
    print("Testing config missing inherited (implicitly) required fields:")
    process_complex_config(test_config_data_missing_inherited_required)

    # This example should always pass, as all fields (including optional ones) are present.
    full_config_data: ComplexConfig = {
        "config_id": 123,
        "config_name": "MainConfig",
        "feature_a_enabled": True,
        "feature_b_value": 0.5,
        "required_setting": "global_access",
        "optional_comment": "Full configuration example"
    }
    print("Testing config with all fields present:")
    process_complex_config(full_config_data)

    # This example should always fail across all strict type checkers,
    # as it's missing an explicitly `Required` field (`required_setting`).
    # invalid_config_data_missing_explicit_required: ComplexConfig = {
    #     "config_id": 123,
    #     "config_name": "MainConfig",
    #     "feature_a_enabled": True,
    #     # missing "required_setting"
    # }
    # print("Testing config missing explicitly required field (should error):")
    # process_complex_config(invalid_config_data_missing_explicit_required)