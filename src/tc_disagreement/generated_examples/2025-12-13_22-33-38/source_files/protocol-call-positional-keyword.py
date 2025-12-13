# id: protocol-call-positional-keyword
# EXPECTED:
#   mypy: Error (Argument mismatch: Protocol expects keyword-only, function has positional-or-keyword)
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy can be strict about the exact call signature, especially when a protocol specifies keyword-only arguments for `__call__` (via `*`), but an implementing function uses positional-or-keyword arguments. It might consider the signatures incompatible. Pyright, Pyre, and Zuban are often more lenient, seeing a function that *can* accept keyword arguments as compatible with a protocol requiring them.

from typing import Protocol, Any

class DataSerializer(Protocol):
    """A protocol for functions that serialize data with specific keyword args."""
    def __call__(self, *, data: dict[str, Any], format: str = "json") -> bytes: ...

def serialize_to_bytes(data: dict[str, Any], format: str = "json") -> bytes:
    """A concrete serialization function with positional-or-keyword args."""
    if format == "json":
        import json
        return json.dumps(data).encode('utf-8')
    elif format == "yaml": # Simplified for example
        return str(data).encode('utf-8')
    else:
        raise ValueError("Unsupported format")

if __name__ == "__main__":
    # Divergence point: assigning a function with positional-or-keyword args to a Protocol requiring keyword-only
    serializer: DataSerializer = serialize_to_bytes # Checkers disagree here
    reveal_type(serializer)

    result = serializer(data={"name": "Alice"}, format="json") # This call itself would be valid at runtime
    reveal_type(result)

    result_direct = serialize_to_bytes(data={"id": 123}, format="yaml")
    reveal_type(result_direct)