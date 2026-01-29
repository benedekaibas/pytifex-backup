from typing import TypeGuard, Dict, Union, Any, Literal, TypedDict # Added TypedDict

SettingsStatus = Literal['enabled', 'disabled']

class ConfigEntry(TypedDict, total=False):
    value: Any
    status: SettingsStatus

# Define a TypedDict that represents the *expected* narrowed type after the guard.
# By default, TypedDicts are total=True, meaning all keys are Required.
class ConfigEntryEnabled(TypedDict):
    value: Any # This key is implicitly Required
    status: Literal['enabled'] # This key is implicitly Required

# The TypeGuard now claims to narrow `ConfigEntry` (where keys are NotRequired)
# to `ConfigEntryEnabled` (where keys are Required).
# However, the implementation of has_enabled_status only checks for the 'status' key
# and its value. It does NOT check for the presence of the 'value' key,
# which is required by ConfigEntryEnabled.
# This creates a potential unsoundness in the TypeGuard.
def has_enabled_status(entry: ConfigEntry) -> TypeGuard[ConfigEntryEnabled]:
    # This guard checks if 'status' is present and 'enabled'.
    # It does NOT check if 'value' is present.
    # If `entry` is `{"status": "enabled"}`, this guard returns True,
    # but `{"status": "enabled"}` is NOT a `ConfigEntryEnabled` (it lacks 'value').
    # Type checkers might disagree on whether this TypeGuard definition is sound,
    # or where the error should be reported (at the TypeGuard definition vs. at usage).
    return 'status' in entry and entry['status'] == 'enabled'

def process_config(config: Dict[str, ConfigEntry]) -> None:
    for key, entry in config.items():
        if has_enabled_status(entry):
            # After narrowing, `entry` is claimed to be `ConfigEntryEnabled`.
            # This means `status` and `value` are both present and have specific types.
            # If the TypeGuard is unsound, accessing `entry['value']` might be an error
            # if the original `entry` did not have a 'value' key.
            print(f"Config '{key}' is enabled: Value = {entry['value']}")
        else:
            print(f"Config '{key}' is not enabled (status: {entry.get('status', 'N/A')}): Value = {entry.get('value', 'N/A')}")

if __name__ == "__main__":
    my_config: Dict[str, ConfigEntry] = {
        "feature_a": {"value": True, "status": "enabled"},
        "feature_b": {"value": 123, "status": "disabled"},
        "feature_c": {"value": "text", "status": "enabled"},
        "feature_d": {"value": None}, # 'status' key missing
        "feature_e_problem": {"status": "enabled"}, # This is a valid ConfigEntry, but problematic for the TypeGuard
    }

    process_config(my_config)

    # --- Test cases for TypeGuard soundness ---

    # Case 1: Entry that satisfies ConfigEntryEnabled fully.
    entry_fully_compliant: ConfigEntry = {"value": "test", "status": "enabled"}
    if has_enabled_status(entry_fully_compliant):
        reveal_type(entry_fully_compliant) # Expect ConfigEntryEnabled
        reveal_type(entry_fully_compliant['status']) # Expect Literal['enabled']
        print(f"Fully compliant: Value = {entry_fully_compliant['value']}")

    # Case 2: Entry that is ConfigEntry but *not* ConfigEntryEnabled (missing 'value').
    # This is the primary divergence point. The guard will return True,
    # but the runtime object does not match the TypeGuard's claim.
    entry_missing_value: ConfigEntry = {"status": "enabled"}
    if has_enabled_status(entry_missing_value):
        # Here, has_enabled_status(entry_missing_value) returns True.
        # According to the TypeGuard, entry_missing_value should now be ConfigEntryEnabled.
        # But at runtime, it's `{"status": "enabled"}`, which does not have a 'value' key.
        reveal_type(entry_missing_value) # Expect ConfigEntryEnabled, but this is a lie
        # Accessing 'value' here is unsound.
        print(f"Missing value (supposedly enabled): Value = {entry_missing_value['value']}")
    else:
        # This branch should not be taken, but if a checker detects unsoundness at the guard,
        # it might not allow this 'else' branch if the guard is considered impossible for this input.
        print("Missing value entry was not enabled (unexpected).")

    # Case 3: Entry that does not satisfy the guard.
    entry_not_enabled: ConfigEntry = {"value": "test", "status": "disabled"}
    if has_enabled_status(entry_not_enabled):
        print(f"Not enabled entry passed the guard (unexpected): Value = {entry_not_enabled['value']}")
    else:
        reveal_type(entry_not_enabled) # Expect ConfigEntry (original type)
        print("Not enabled entry correctly failed the guard.")

    entry_missing_status: ConfigEntry = {"value": "test"}
    if has_enabled_status(entry_missing_status):
        print(f"Missing status entry passed the guard (unexpected): Value = {entry_missing_status['value']}")
    else:
        reveal_type(entry_missing_status) # Expect ConfigEntry (original type)
        print("Missing status entry correctly failed the guard.")