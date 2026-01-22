# id: protocol-default-call-mismatch
# category: protocol-defaults
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import Protocol, runtime_checkable

@runtime_checkable
class HasDefaultMethod(Protocol):
    """
    Protocol with a method that has a default argument.
    """
    def greet(self, name: str = "World") -> str: ...

class ImplementsDefault:
    """
    Class implementing the protocol with a different default.
    PEP 544 allows this.
    """
    def greet(self, name: str = "User") -> str:
        return f"Hello, {name}!"

class RemovesDefault:
    """
    Class implementing the protocol by removing the default.
    PEP 544 allows an implementation to "supply a non-default parameter
    in place of one that has a default in the protocol."
    """
    def greet(self, name: str) -> str: # No default argument
        return f"Hi, {name}!"

def call_with_default(obj: HasDefaultMethod) -> str:
    """
    Function that expects a HasDefaultMethod and calls its `greet` method
    without providing the `name` argument, relying on the protocol's default.
    """
    # This call is statically valid based on HasDefaultMethod's signature.
    # The divergence arises because 'obj' at runtime could be 'RemovesDefault',
    # whose `greet` method does not support being called without arguments.
    return obj.greet() 

if __name__ == "__main__":
    impl_default = ImplementsDefault()
    removes_default = RemovesDefault()

    # This should be fine for all checkers and at runtime.
    print(f"Call with ImplementsDefault: {call_with_default(impl_default)}")

    # DIVERGENCE POINT:
    # `RemovesDefault` is considered a valid implementation of `HasDefaultMethod`
    # by some checkers (e.g., mypy) because PEP 544 allows implementations to
    # remove defaults. However, `call_with_default` then attempts to call
    # `obj.greet()` without arguments, which `RemovesDefault.greet` does not support.
    # Mypy tends to pass this check, leading to a runtime TypeError.
    # Other checkers (Pyre/Pyrefly, Zuban, Ty) are expected to catch this potential
    # runtime error statically, flagging `removes_default` as incompatible with `HasDefaultMethod`
    # for the purpose of the no-argument call.
    print(f"Call with RemovesDefault: {call_with_default(removes_default)}")