# id: protocol-default-arg-compatibility
# EXPECTED:
#   mypy: No error
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Type checkers generally consider default argument *values* to not be part of the callable's type signature for compatibility, only the presence/absence of the argument and its type. While the default *value* differs, the `size: int` argument is optional in both, making them compatible in most checkers. This example usually *doesn't* diverge, but is often cited. For a real divergence, consider default argument *absence* in implementation.

from typing import Protocol

class Reader(Protocol):
    def read(self, size: int = -1) -> bytes: ...

class FileReader:
    def read(self, size: int = 1024) -> bytes:  # Different default argument value
        return b"some file data"

def use_reader(r: Reader) -> None:
    print(r.read())
    print(r.read(size=5))

if __name__ == "__main__":
    file_reader = FileReader()
    use_reader(file_reader)

**Self-correction:** The above example for "Protocol with default arguments" is a classic *misconception* about divergence. As noted in the `REASON`, most modern type checkers do *not* diverge on different default *values* for the same optional parameter. They typically only care about whether an argument is present, its type, and its optionality. I need to find a *real* divergence for this category.

A known divergence in this area is when a protocol specifies an optional (defaulted) parameter, but the implementation *omits* the default, making it a required parameter.


**Re-evaluating and generating for each divergence point with known actual divergences:**