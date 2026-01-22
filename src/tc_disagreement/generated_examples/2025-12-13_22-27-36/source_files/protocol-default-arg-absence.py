# id: protocol-default-arg-absence
# EXPECTED:
#   mypy: No error. Mypy considers `path: str` compatible with `path: str = ...` in an implementation for a protocol.
#   pyright: No error. Pyright typically allows this as long as the implementation's argument types and positions are compatible with all possible calls allowed by the protocol.
#   pyre: Error. Pyre is often stricter, flagging an incompatibility because `FileConfigLoader.load` lacks a default argument, while `ConfigLoader.load` specifies one, which would make a call like `loader.load()` ambiguous for `FileConfigLoader`.
#   zuban: No error. Focuses on call signature compatibility (i.e., whether the implementation can satisfy all calls).
# REASON: Type checkers differ on whether the presence or absence of a default argument in an implementation, when the protocol specifies one, constitutes a signature mismatch. Some prioritize callable signature compatibility (parameters, types), allowing an implementation to omit a default if it can still satisfy calls where the argument is either provided or expected to be optional. Others view the default argument as part of the callable's contract that must be present.

from typing import Protocol

class ConfigLoader(Protocol):
    """Protocol requiring a load method with an optional path."""
    def load(self, path: str = "default.ini") -> dict[str, str]: ...

class FileConfigLoader:
    """Implementation that omits the default argument."""
    def load(self, path: str) -> dict[str, str]: # Protocol specifies default, implementation does not
        print(f"FileConfigLoader: Loading from {path}")
        return {"file_key": "file_value"}

class DefaultConfigLoader:
    """Implementation with a different default argument."""
    def load(self, path: str = "another.cfg") -> dict[str, str]: # Protocol specifies default, implementation has different default
        print(f"DefaultConfigLoader: Loading from {path} with different default")
        return {"default_key": "default_value"}

def process_config(loader: ConfigLoader) -> None:
    # This call relies on the protocol's default argument
    # Pyre is expected to flag an error here if `loader` is `FileConfigLoader` because `FileConfigLoader.load` has no default.
    config = loader.load()
    print(f"    Processed config (default): {config}")

    # This call explicitly provides an argument
    config = loader.load("custom.json")
    print(f"    Processed config (custom): {config}")

if __name__ == "__main__":
    print("--- Testing FileConfigLoader ---")
    file_loader: ConfigLoader = FileConfigLoader() # Potential divergence point
    process_config(file_loader)
    
    print("\n--- Testing DefaultConfigLoader ---")
    default_loader: ConfigLoader = DefaultConfigLoader() # All should typically allow
    process_config(default_loader)

---

### Snippet 2: TypeGuard with Generic Narrowing