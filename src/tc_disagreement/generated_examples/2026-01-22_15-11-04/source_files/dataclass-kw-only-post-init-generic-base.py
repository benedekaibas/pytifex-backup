from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar('T')

@dataclass
class BaseSettings(Generic[T]):
    base_id: str
    data_source: T # Generic field in base class

@dataclass(kw_only=True)
class AdvancedSettings(BaseSettings[str]):
    """
    A kw_only dataclass inheriting from a generic base.
    The base class has positional arguments, while this one enforces kw_only.
    How the constructor reconciles `base_id` and `data_source` as kw_only
    when they were positional in the base is a common point of contention.
    """
    timeout: int = 30
    log_level: str = "INFO"
    tags: List[str] = field(default_factory=list)
    processed_flag: Optional[bool] = None

    def __post_init__(self) -> None:
        # Perform validation or additional setup after __init__
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive.")
        if not self.base_id.startswith("CONF-"):
            print(f"Warning: base_id '{self.base_id}' does not start with 'CONF-'.")
        if self.data_source == "":
            self.data_source = "default_source" # Modify generic field from base

@dataclass(kw_only=True)
class ExtendedAdvancedSettings(AdvancedSettings):
    """
    Further inheritance, ensuring kw_only propagates and interacts correctly
    with inherited fields, including those from the generic base.
    """
    additional_param: float
    processed_flag: bool = False # Override default of Optional[bool] to bool, make it required via kw_only

    def __post_init__(self) -> None:
        super().__post_init__()
        print(f"ExtendedAdvancedSettings post_init called for '{self.base_id}'")
        if self.additional_param < 0:
            raise ValueError("additional_param must be non-negative.")
        # Check if processed_flag is explicitly set or still False
        if self.processed_flag is False:
            print(f"  Processed flag is still False (or explicitly set to False).")

if __name__ == "__main__":
    # Correct usage: All fields must be keyword arguments
    settings1 = AdvancedSettings(
        base_id="CONF-A1",
        data_source="api_v2",
        timeout=60,
        tags=["critical"]
    )
    print(f"Settings 1: {settings1}")
    print(f"Settings 1 data source: {settings1.data_source}")

    # Test kw_only enforcement with positional arguments (should be error)
    try:
        # This constructor call should be a type error (and runtime TypeError)
        # because AdvancedSettings is kw_only, despite BaseSettings having positional fields.
        _ = AdvancedSettings("CONF-B2", "file_storage", timeout=10) # type: ignore
    except TypeError as e:
        print(f"Caught expected TypeError for positional args: {e}")

    # Test ExtendedAdvancedSettings
    ext_settings1 = ExtendedAdvancedSettings(
        base_id="CONF-X1",
        data_source="db_connection",
        timeout=120,
        additional_param=1.5,
        processed_flag=True # Must be provided due to kw_only and override
    )
    print(f"Extended Settings 1: {ext_settings1}")

    # This should be a type error because 'processed_flag' is implicitly Required[bool]
    # in ExtendedAdvancedSettings due to `processed_flag: bool = False` combined with kw_only=True.
    ext_settings2 = ExtendedAdvancedSettings( # type: ignore
        base_id="CONF-X2",
        data_source="cache",
        additional_param=2.0
        # missing processed_flag
    )
    print(f"Extended Settings 2: {ext_settings2}")

    # Test __post_init__ validation
    try:
        _ = AdvancedSettings(base_id="CONF-C3", data_source="web", timeout=0)
    except ValueError as e:
        print(f"Caught expected ValueError from __post_init__: {e}")

    try:
        _ = ExtendedAdvancedSettings(base_id="CONF-Y1", data_source="stream", additional_param=-1.0, processed_flag=False)
    except ValueError as e:
        print(f"Caught expected ValueError from ExtendedAdvancedSettings __post_init__: {e}")