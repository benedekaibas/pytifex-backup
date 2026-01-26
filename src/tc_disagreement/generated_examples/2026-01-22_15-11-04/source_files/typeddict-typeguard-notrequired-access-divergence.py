from typing import TypedDict, Literal, NotRequired, Required, Union, TypeGuard

class BaseConfig(TypedDict):
    id: int
    status: Literal["pending", "active", "completed"]

class DetailedConfig(BaseConfig, total=False):
    description: NotRequired[str]
    deadline: NotRequired[int]

class ActiveConfig(DetailedConfig, total=True):
    # 'description' is NotRequired in the parent (DetailedConfig).
    # Per PEP 655, a field explicitly marked as NotRequired in a base class
    # cannot be overridden as Required in a subclass.
    # Therefore, 'description' remains NotRequired[str] in ActiveConfig,
    # even though 'total=True' is specified.
    startDate: Required[str] # This field is explicitly Required.

class CompletedConfig(DetailedConfig, total=False):
    # 'description' remains NotRequired, 'endDate' is optional.
    endDate: NotRequired[str]

def is_active_config(config: Union[BaseConfig, DetailedConfig]) -> TypeGuard[ActiveConfig]:
    # Check 1: status must be "active"
    if config.get("status") != "active":
        return False

    # Check 2: 'startDate' must be present and a string.
    # 'startDate' is not defined in BaseConfig or DetailedConfig, but is Required for ActiveConfig.
    if not ("startDate" in config and isinstance(config.get("startDate"), str)):
        return False

    # Check 3: 'description' must be present and a string.
    # This guard is stricter than ActiveConfig allows for 'description'.
    # ActiveConfig allows 'description' to be NotRequired, but this guard requires it.
    # The TypeGuard narrows to a strict subset of ActiveConfig where 'description' is present.
    if not ("description" in config and isinstance(config.get("description"), str)):
        return False
    
    # Check 4: If 'deadline' is present, it must be an int.
    # This check does NOT make 'deadline' required. It only checks its type if it exists.
    # This is a key part of the divergence strategy for 'deadline' access later.
    if "deadline" in config and not isinstance(config.get("deadline"), int):
        return False
    
    # If all checks pass, we assert it's an ActiveConfig.
    return True

def process_config(config: Union[BaseConfig, DetailedConfig]) -> None:
    if is_active_config(config):
        # If this branch is entered, config is narrowed to ActiveConfig.
        # Given the TypeGuard, 'description' and 'startDate' are guaranteed
        # to be present and of type str within this block.
        print(f"Processing Active Config (ID: {config['id']}):")
        print(f"  Description: {config['description']}") # Safe due to TypeGuard.
        print(f"  Start Date: {config['startDate']}")   # Safe due to TypeGuard.

        # Divergence point: Accessing 'deadline' directly without prior presence check.
        # In ActiveConfig, 'deadline' is NotRequired[int].
        # The TypeGuard ensures that *if* 'deadline' is present, its value is an int.
        # It does NOT guarantee that 'deadline' is present in the dictionary.
        #
        # Therefore, 'config["deadline"]' here *should* be a type error,
        # as 'deadline' might be missing, leading to a KeyError at runtime
        # (e.g., for cfg4).
        # Type checkers often disagree on how strictly to enforce direct access
        # to `NotRequired` TypedDict keys within a TypeGuard-narrowed context.
        try:
            # This 'try-except' block is for runtime safety and demonstration.
            # The static analysis error is expected on the line below it.
            print(f"  Deadline: {config['deadline']}")
        except KeyError:
            print(f"  Deadline: Not specified (runtime KeyError handled)")
            
        # This line is specifically designed to trigger static analysis divergence.
        # It attempts to access a NotRequired key directly without a preceding
        # 'in config' check.
        # Some type checkers might correctly report a potential KeyError.
        # Others might incorrectly allow it, possibly due to over-eager narrowing
        # or lenient handling of NotRequired fields after some checks.
        _ = config['deadline'] 

    else:
        print(f"Processing other config (ID: {config['id']})")
        # Use .get() for safe access as 'description' is not in BaseConfig.
        description = config.get("description") 
        if description is not None:
            print(f"  Description: {description}")

if __name__ == "__main__":
    cfg1: BaseConfig = {"id": 1, "status": "pending"} # Fails status check.
    cfg2: DetailedConfig = {"id": 2, "status": "active", "description": "task A"} # Missing startDate, fails guard.
    cfg3: ActiveConfig = {"id": 3, "status": "active", "startDate": "2023-01-01"} # Valid ActiveConfig, but fails guard (missing description).
    cfg4: ActiveConfig = {"id": 4, "status": "active", "description": "task B", "startDate": "2023-02-01"} # Valid ActiveConfig, passes guard. (Lacks 'deadline')
    cfg5: ActiveConfig = {"id": 5, "status": "active", "description": "task C", "startDate": "2023-03-01", "deadline": 10} # Valid ActiveConfig, passes guard. (Has 'deadline')

    print("--- Processing cfg1 ---")
    process_config(cfg1)
    print("\n--- Processing cfg2 ---")
    process_config(cfg2)
    print("\n--- Processing cfg3 ---")
    process_config(cfg3)
    print("\n--- Processing cfg4 (Lacks 'deadline') ---")
    process_config(cfg4) # This one is expected to cause a KeyError at runtime for 'config["deadline"]'.
    print("\n--- Processing cfg5 (Has 'deadline') ---")
    process_config(cfg5)