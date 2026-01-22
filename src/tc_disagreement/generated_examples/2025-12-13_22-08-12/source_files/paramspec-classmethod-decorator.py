# id: paramspec-classmethod-decorator


")
    test_child_typeddict(td3)

    # Example of potential mypy/pyre errors if 'x' is not recognized as optional
    # type_checker_td = {'y': 'example'}
    # reveal_type(type_checker_td.get('x')) # This would be `None` at runtime,
                                          # but static analysis varies.

# EXPECTED:
#   mypy: Error: Argument "cls" of "create" has no corresponding argument in "wrapper" (or similar error indicating signature mismatch on 'create' after decoration)
#   pyright: No error
#   pyre: Error: Signature of "create" incompatible with decorator (or similar, indicating `cls` argument issue)
#   zuban: No error (likely handles ParamSpec correctly with classmethod)
# REASON: Mypy and Pyre have historically struggled to correctly infer and preserve the signature of classmethods when they are wrapped by a ParamSpec-aware decorator. The implicit `cls` argument can be lost or misrepresented in the `ParamSpec` context. Pyright and Zuban are generally more robust in preserving the full signature, including `cls`/`self` arguments and accurately mapping `ParamSpec`.
from typing import TypeVar, Callable, Any
from typing_extensions import ParamSpec # Python 3.10+, ParamSpec is in typing, but for broader compatibility often used from typing_extensions

P = ParamSpec('P')
T = TypeVar('T')

def log_calls(func: Callable[P, T]) -> Callable[P, T]:
    """A decorator that logs calls to the decorated function."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        print(f"