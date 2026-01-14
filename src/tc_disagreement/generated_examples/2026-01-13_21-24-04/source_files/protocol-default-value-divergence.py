from typing import Protocol

class GreeterProtocol(Protocol):
    """
    A protocol defining a method with a specific default argument value.
    """
    def greet(self, name: str = "World") -> str:
        """
        Protocol method with a default argument 'name' set to "World".
        """
        ...

class StandardGreeter:
    """
    Implements GreeterProtocol with an identical default argument value.
    This implementation should be compatible with the protocol for all type checkers.
    """
    def greet(self, name: str = "World") -> str:
        return f"Hello, {name}!"

class CustomDefaultGreeter:
    """
    Implements GreeterProtocol but with a different default 'name' value ("Friend").
    Some type checkers consider changing the default *value* incompatible with the protocol
    even if the method signature (parameter name, type, and optionality) remains compatible.
    Others are more lenient, focusing only on the callable signature and ignoring default values.
    """
    def greet(self, name: str = "Friend") -> str: # Divergence point: default value is "Friend" instead of "World"
        return f"Greetings, {name}!"

def introduce_person(greeter: GreeterProtocol, custom_name: str | None = None) -> None:
    """
    A function that expects an object adhering to GreeterProtocol.
    It calls the greet method, sometimes relying on the default.
    """
    if custom_name:
        print(f"Introducing (with custom name): {greeter.greet(custom_name)}")
    else:
        # This call relies on the default value defined in the *implementation*.
        # The type checker evaluates if `CustomDefaultGreeter` is assignable to `GreeterProtocol`.
        print(f"Introducing (with default): {greeter.greet()}")

if __name__ == "__main__":
    # This assignment should pass for all checkers as the default matches.
    standard_impl: GreeterProtocol = StandardGreeter()
    introduce_person(standard_impl) # Expected runtime output: "Introducing (with default): Hello, World!"

    # This is the primary point of divergence:
    # Will `CustomDefaultGreeter` be accepted as a `GreeterProtocol`?
    # Mypy often allows this, as it considers the *signature* (optional string parameter)
    # compatible, disregarding the exact default *value*.
    # Other type checkers might be stricter and flag an error here.
    custom_impl: GreeterProtocol = CustomDefaultGreeter()
    introduce_person(custom_impl) # Expected runtime output: "Introducing (with default): Greetings, Friend!" (if accepted)

    # Example with explicit name for verification
    introduce_person(standard_impl, "Alice") # Expected runtime output: "Introducing (with custom name): Hello, Alice!"
    introduce_person(custom_impl, "Bob")     # Expected runtime output: "Introducing (with custom name): Greetings, Bob!"