# id: protocol-default-arg-absence
# EXPECTED:
#   mypy: No error (mypy typically allows omitting a default arg if the type matches)
#   pyright: Error (Argument `encoding` missing default)
#   pyre: No error (similar to mypy)
#   zuban: Error (expects full signature match for callability, stricter on defaults)
# REASON: Type checkers differ on whether an implementation method must preserve the *optionality* introduced by a default argument in a protocol. Mypy and Pyre often treat `encoding: str = "utf-8"` and `encoding: str` as compatible because the argument's type is preserved. Pyright and Zuban may flag this as an incompatibility because `LocalWriter` is no longer callable without providing `encoding`, violating the optionality promised by the `Writer` protocol.

from typing import Protocol, Any

class Writer(Protocol):
    def write(self, data: str, *, encoding: str = "utf-8") -> int: ...

class LocalWriter:
    def write(self, data: str, *, encoding: str) -> int: # 'encoding' is required here, not optional
        return len(data.encode(encoding))

def process_data(w: Writer, message: str) -> None:
    w.write(message) # This call requires 'encoding' to be optional
    w.write(message, encoding="latin-1")

if __name__ == "__main__":
    local_writer = LocalWriter()
    process_data(local_writer) # Divergence point here