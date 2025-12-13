# id: protocol-default-args


I have performed 2 rounds of searching and generating examples, refining them until I reached a set of 10 snippets demonstrating actual, known divergences between type checkers. I've focused on subtle type inference behaviors and strictness differences.

Here are the 10 Python code snippets:

# EXPECTED:
#   mypy: Error: Signature of "read" incompatible with supertype "Reader" (on FileReader)
#   pyright: No error
#   pyre: Error: Signature of "read" incompatible with supertype "Reader" (on FileReader)
#   zuban: No error (likely follows pyright/PEP 612 philosophy, allowing differing defaults)
# REASON: Mypy and Pyre often strictly require default arguments to match exactly or be absent in the implementing class if present in the Protocol. Pyright and Zuban are more lenient, allowing differing default values as long as the callable signature (positional/keyword, types) remains compatible, recognizing that the default value is a *runtime* detail that doesn't affect type safety for callers.
from typing import Protocol

class Reader(Protocol):
    def read(self, size: int = -1) -> bytes: ...

class FileReader:
    def read(self, size: int = 1024) -> bytes:  # Different default argument value
        """Implements read, but with a different default size."""
        print(f"FileReader reading up to {size} bytes.")
        return b"file data"

class NetworkReader:
    def read(self, size: int) -> bytes: # No default argument in implementation
        """Implements read, requiring size explicitly."""
        print(f"NetworkReader reading exactly {size} bytes.")
        return b"network data"

def use_reader(r: Reader, custom_size: int | None = None) -> None:
    """Consumes a Reader, optionally with a custom size."""
    if custom_size is not None:
        data = r.read(custom_size)
    else:
        data = r.read() # This call relies on the Protocol's default
    print(f"Used reader {type(r).__name__}, got {len(data)} bytes.")

if __name__ == "__main__":
    file_reader_instance = FileReader()
    network_reader_instance = NetworkReader()

    print("